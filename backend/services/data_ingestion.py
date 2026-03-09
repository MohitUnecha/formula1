"""
FastF1 Data Ingestion Service

Handles loading F1 data from FastF1 API and storing it in the database.
"""
import fastf1
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from database import SessionLocal
from models import (
    Event, Session as DBSession, Driver, DriverSession,
    Lap, PitStop, Weather, RaceControl
)


# Enable FastF1 caching
if settings.fastf1_cache_enabled:
    fastf1.Cache.enable_cache(str(settings.fastf1_cache_dir))


class DataIngestionService:
    """Service for ingesting F1 data using FastF1"""
    
    def __init__(self, db: Session):
        self.db = db
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def ingest_season(self, season: int) -> Dict[str, int]:
        """
        Ingest all events and sessions for a season
        
        Returns:
            Statistics about ingested data
        """
        print(f"Starting ingestion for season {season}")
        stats = {
            'events': 0,
            'sessions': 0,
            'drivers': 0,
            'laps': 0,
            'pit_stops': 0
        }
        
        # Get season schedule
        schedule = fastf1.get_event_schedule(season)
        
        for _, event_row in schedule.iterrows():
            try:
                event_stats = self.ingest_event(season, event_row)
                for key in stats:
                    stats[key] += event_stats.get(key, 0)
                self.db.commit()  # Commit after each event so progress survives restarts
            except Exception as e:
                print(f"Error ingesting event {event_row['EventName']}: {e}")
                self.db.rollback()
                continue
        
        print(f"Season {season} ingestion complete: {stats}")
        return stats
    
    def ingest_event(self, season: int, event_row) -> Dict[str, int]:
        """Ingest a single Grand Prix event"""
        stats = {'events': 0, 'sessions': 0, 'drivers': 0, 'laps': 0, 'pit_stops': 0}
        
        # Check if event already exists
        existing_event = self.db.query(Event).filter(
            Event.season == season,
            Event.round == event_row['RoundNumber']
        ).first()
        
        if existing_event:
            print(f"Event already exists: {event_row['EventName']}")
            event = existing_event
        else:
            # Create event - ensure date is Python date object
            event_date = event_row['EventDate']
            if hasattr(event_date, 'date'):
                event_date = event_date.date()
            elif isinstance(event_date, str):
                from datetime import datetime
                event_date = datetime.fromisoformat(event_date).date()
            
            event = Event(
                season=season,
                round=int(event_row['RoundNumber']),
                event_name=event_row['EventName'],
                event_date=event_date,
                event_format=event_row.get('EventFormat', 'conventional'),
                country=event_row.get('Country'),
                location=event_row.get('Location'),
                circuit_key=event_row.get('EventName', '').lower().replace(' ', '_')
            )
            self.db.add(event)
            self.db.flush()
            stats['events'] += 1
            print(f"Created event: {event.event_name}")
        
        # Ingest sessions (FP1, FP2, FP3, Qualifying, Sprint, Race)
        session_types = ['FP1', 'FP2', 'FP3', 'Q', 'S', 'R']
        
        for session_type in session_types:
            try:
                session_stats = self.ingest_session(season, event, session_type)
                for key in stats:
                    if key != 'events':
                        stats[key] += session_stats.get(key, 0)
            except Exception as e:
                print(f"Error ingesting session {session_type}: {e}")
                self.db.rollback()
                continue
        
        return stats
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    def ingest_session(self, season: int, event: Event, session_type: str) -> Dict[str, int]:
        """Ingest a single session (FP1, FP2, FP3, Q, S, R)"""
        stats = {'sessions': 0, 'drivers': 0, 'laps': 0, 'pit_stops': 0}
        
        print(f"  Loading {session_type} for {event.event_name}")
        
        # Load FastF1 session
        try:
            ff1_session = fastf1.get_session(season, event.round, session_type)
            ff1_session.load()
        except Exception as e:
            print(f"    Session {session_type} not available: {e}")
            return stats
        
        # Check if session already exists
        existing_session = self.db.query(DBSession).filter(
            DBSession.event_id == event.event_id,
            DBSession.session_type == session_type
        ).first()
        
        if existing_session:
            print(f"    Session already exists: {session_type}")
            return stats
        
        # Create session
        db_session = DBSession(
            event_id=event.event_id,
            session_type=session_type,
            session_date=ff1_session.date,
            total_laps=ff1_session.total_laps if hasattr(ff1_session, 'total_laps') else None,
            track_length_km=ff1_session.track_length / 1000 if hasattr(ff1_session, 'track_length') else None
        )
        self.db.add(db_session)
        self.db.flush()
        stats['sessions'] += 1
        
        # Ingest drivers and laps
        for driver_abbr in ff1_session.drivers:
            try:
                driver_stats = self.ingest_driver_session(ff1_session, db_session, driver_abbr)
                stats['drivers'] += driver_stats['drivers']
                stats['laps'] += driver_stats['laps']
                stats['pit_stops'] += driver_stats['pit_stops']
            except Exception as e:
                print(f"      Error ingesting driver {driver_abbr}: {e}")
                self.db.rollback()
                continue
        
        # Ingest weather
        self.ingest_weather(ff1_session, db_session)
        
        # Ingest race control messages
        if session_type == 'R':
            self.ingest_race_control(ff1_session, db_session)
        
        # Export telemetry to Parquet
        if session_type in ['Q', 'R']:
            self.export_telemetry_parquet(ff1_session, db_session)
        
        print(f"    Completed {session_type}: {stats['drivers']} drivers, {stats['laps']} laps")
        return stats
    
    def ingest_driver_session(self, ff1_session, db_session: DBSession, driver_abbr: str) -> Dict[str, int]:
        """Ingest driver participation in a session"""
        stats = {'drivers': 0, 'laps': 0, 'pit_stops': 0}
        
        # Get driver data
        driver_data = ff1_session.get_driver(driver_abbr)
        
        # Get or create driver
        driver = self.db.query(Driver).filter(Driver.driver_code == driver_abbr).first()
        if not driver:
            driver = Driver(
                driver_code=driver_abbr,
                driver_number=driver_data.get('DriverNumber'),
                first_name=driver_data.get('FirstName', ''),
                last_name=driver_data.get('LastName', ''),
                team_name=driver_data.get('TeamName', ''),
                team_color=f"#{driver_data.get('TeamColor', 'FFFFFF')}"
            )
            self.db.add(driver)
            self.db.flush()
            stats['drivers'] += 1
        
        # Create driver session
        driver_session = DriverSession(
            session_id=db_session.session_id,
            driver_id=driver.driver_id,
            grid_position=driver_data.get('GridPosition'),
            final_position=driver_data.get('Position'),
            points=driver_data.get('Points'),
            dnf=driver_data.get('Status', '') not in ['Finished', '+1 Lap', '+2 Laps'],
            dnf_reason=driver_data.get('Status') if driver_data.get('Status') not in ['Finished', '+1 Lap', '+2 Laps'] else None
        )
        self.db.add(driver_session)
        self.db.flush()
        
        # Ingest laps
        laps = ff1_session.laps.pick_driver(driver_abbr)
        for _, lap_data in laps.iterrows():
            lap = Lap(
                driver_session_id=driver_session.driver_session_id,
                lap_number=int(lap_data['LapNumber']),
                lap_time=self._time_to_seconds(lap_data.get('LapTime')),
                sector1_time=self._time_to_seconds(lap_data.get('Sector1Time')),
                sector2_time=self._time_to_seconds(lap_data.get('Sector2Time')),
                sector3_time=self._time_to_seconds(lap_data.get('Sector3Time')),
                position=lap_data.get('Position'),
                tyre_compound=lap_data.get('Compound'),
                tyre_age=lap_data.get('TyreLife'),
                is_personal_best=lap_data.get('IsPersonalBest', False),
                pit_out_lap=lap_data.get('PitOutTime') is not pd.NaT if pd.notna(lap_data.get('PitOutTime')) else False,
                pit_in_lap=lap_data.get('PitInTime') is not pd.NaT if pd.notna(lap_data.get('PitInTime')) else False,
                track_status=lap_data.get('TrackStatus'),
                is_accurate=lap_data.get('IsAccurate', True)
            )
            self.db.add(lap)
            stats['laps'] += 1
        
        # Store fastest lap
        if len(laps) > 0:
            fastest_lap = laps['LapTime'].min()
            if pd.notna(fastest_lap):
                driver_session.fastest_lap = self._time_to_seconds(fastest_lap)
        
        # Ingest pit stops
        if hasattr(ff1_session, 'laps'):
            pit_laps = laps[laps['PitInTime'].notna()]
            for _, pit_lap in pit_laps.iterrows():
                pit_stop = PitStop(
                    driver_session_id=driver_session.driver_session_id,
                    lap_number=int(pit_lap['LapNumber']),
                    pit_duration=self._time_to_seconds(pit_lap.get('PitInTime')) if pd.notna(pit_lap.get('PitInTime')) else None,
                    tyre_compound_old=pit_lap.get('Compound'),
                    time_of_day=self._time_to_seconds(pit_lap.get('Time')) if pd.notna(pit_lap.get('Time')) else None
                )
                self.db.add(pit_stop)
                stats['pit_stops'] += 1
        
        return stats
    
    def ingest_weather(self, ff1_session, db_session: DBSession):
        """Ingest weather data"""
        if not hasattr(ff1_session, 'weather_data') or ff1_session.weather_data.empty:
            return
        
        # Sample weather data (one entry per lap)
        weather_df = ff1_session.weather_data
        for lap_num in range(1, db_session.total_laps + 1 if db_session.total_laps else 1):
            weather_row = weather_df[weather_df['Time'].notna()].iloc[0] if len(weather_df) > 0 else None
            if weather_row is not None:
                weather = Weather(
                    session_id=db_session.session_id,
                    lap_number=lap_num,
                    air_temp=weather_row.get('AirTemp'),
                    track_temp=weather_row.get('TrackTemp'),
                    humidity=weather_row.get('Humidity'),
                    pressure=weather_row.get('Pressure'),
                    wind_speed=weather_row.get('WindSpeed'),
                    wind_direction=weather_row.get('WindDirection'),
                    rainfall=weather_row.get('Rainfall', False)
                )
                self.db.add(weather)
    
    def ingest_race_control(self, ff1_session, db_session: DBSession):
        """Ingest race control messages"""
        if not hasattr(ff1_session, 'race_control_messages'):
            return
        
        messages = ff1_session.race_control_messages
        if messages is None or len(messages) == 0:
            return
        
        for _, msg in messages.iterrows():
            race_control = RaceControl(
                session_id=db_session.session_id,
                lap_number=msg.get('Lap'),
                message_time=msg.get('Time'),
                category=msg.get('Category'),
                message=msg.get('Message'),
                flag_type=msg.get('Flag'),
                sector=msg.get('Sector'),
                driver_code=msg.get('RacingNumber')
            )
            self.db.add(race_control)
    
    def export_telemetry_parquet(self, ff1_session, db_session: DBSession):
        """Export telemetry data to Parquet files"""
        session_dir = (
            settings.parquet_dir 
            / f"season={ff1_session.event['EventDate'].year}"
            / f"event={ff1_session.event['EventName'].lower().replace(' ', '_')}"
            / f"session={db_session.session_type.lower()}"
        )
        session_dir.mkdir(parents=True, exist_ok=True)
        
        for driver_abbr in ff1_session.drivers:
            try:
                # Get driver telemetry
                driver_laps = ff1_session.laps.pick_driver(driver_abbr)
                if len(driver_laps) == 0:
                    continue
                
                # Get telemetry for all laps
                telemetry_list = []
                for lap_num in driver_laps['LapNumber'].unique():
                    lap = driver_laps[driver_laps['LapNumber'] == lap_num].iloc[0]
                    try:
                        telemetry = lap.get_telemetry()
                        if telemetry is not None and len(telemetry) > 0:
                            telemetry['lap_number'] = lap_num
                            telemetry['session_id'] = db_session.session_id
                            telemetry['driver_code'] = driver_abbr
                            telemetry_list.append(telemetry)
                    except:
                        continue
                
                if len(telemetry_list) == 0:
                    continue
                
                # Combine all laps
                all_telemetry = pd.concat(telemetry_list, ignore_index=True)
                
                # Select relevant columns
                columns = ['session_id', 'driver_code', 'lap_number', 'Distance', 'Time',
                          'Speed', 'Throttle', 'Brake', 'nGear', 'DRS', 'RPM', 'X', 'Y', 'Z']
                available_columns = [col for col in columns if col in all_telemetry.columns]
                telemetry_export = all_telemetry[available_columns]
                
                # Rename columns to lowercase
                telemetry_export.columns = [col.lower() for col in telemetry_export.columns]
                
                # Export to Parquet
                driver_file = session_dir / f"driver={driver_abbr}" / "telemetry.parquet"
                driver_file.parent.mkdir(parents=True, exist_ok=True)
                telemetry_export.to_parquet(driver_file, compression='snappy', index=False)
                
            except Exception as e:
                print(f"        Error exporting telemetry for {driver_abbr}: {e}")
                continue
    
    @staticmethod
    def _time_to_seconds(time_value) -> Optional[float]:
        """Convert pandas Timedelta to seconds"""
        if pd.isna(time_value):
            return None
        if isinstance(time_value, pd.Timedelta):
            return time_value.total_seconds()
        return float(time_value)


def ingest_season_cli(season: int):
    """CLI function to ingest a season"""
    db = SessionLocal()
    try:
        service = DataIngestionService(db)
        stats = service.ingest_season(season)
        print(f"\nIngestion complete for season {season}:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        season = int(sys.argv[1])
        ingest_season_cli(season)
    else:
        print("Usage: python data_ingestion.py <season>")
        print("Example: python data_ingestion.py 2024")
