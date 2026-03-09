"""
Feature Engineering Service

Computes ML features from raw F1 data.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta

from models import (
    Event, Session as DBSession, Driver, DriverSession,
    Lap, PitStop, Weather, FeatureStore
)


class FeatureEngineer:
    """Feature engineering for F1 race predictions"""
    
    def __init__(self, db: Session, lookback_races: int = 10):
        self.db = db
        self.lookback = lookback_races
    
    def compute_features_for_session(self, session_id: int) -> pd.DataFrame:
        """
        Compute all features for all drivers in a session
        
        Returns:
            DataFrame with features for each driver
        """
        session = self.db.query(DBSession).filter(DBSession.session_id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        driver_sessions = self.db.query(DriverSession).filter(
            DriverSession.session_id == session_id
        ).all()
        
        features_list = []
        for ds in driver_sessions:
            features = self.engineer_features(session_id, ds.driver_id)
            features['driver_session_id'] = ds.driver_session_id
            features['driver_id'] = ds.driver_id
            features_list.append(features)
        
        return pd.DataFrame(features_list)
    
    def engineer_features(self, session_id: int, driver_id: int) -> Dict:
        """Compute all features for a single driver in a session"""
        features = {}
        
        # Get session info
        session = self.db.query(DBSession).filter(DBSession.session_id == session_id).first()
        event = self.db.query(Event).filter(Event.event_id == session.event_id).first()
        driver = self.db.query(Driver).filter(Driver.driver_id == driver_id).first()
        
        # Driver form features
        features.update(self._driver_form_features(driver_id, event.season, event.round))
        
        # Team features
        features.update(self._team_features(driver.team_name, event.season, event.round))
        
        # Track-specific features
        features.update(self._track_features(event.circuit_key, driver_id))
        
        # Practice session features
        features.update(self._practice_features(session_id, driver_id))
        
        # Qualifying features
        features.update(self._qualifying_features(session_id, driver_id))
        
        # Strategy features
        features.update(self._strategy_features(session_id, driver_id))
        
        # Weather features
        features.update(self._weather_features(session_id))
        
        # Context features
        features.update(self._context_features(event.season, event.round, driver_id))
        
        return features
    
    def _driver_form_features(self, driver_id: int, season: int, current_round: int) -> Dict:
        """Compute driver form features based on recent races"""
        features = {}
        
        # Get recent races (lookback)
        recent_races = self.db.query(DriverSession).join(DBSession).join(Event).filter(
            DriverSession.driver_id == driver_id,
            Event.season <= season,
            DBSession.session_type == 'R',
            Event.round < current_round if Event.season == season else True
        ).order_by(Event.season.desc(), Event.round.desc()).limit(self.lookback).all()
        
        if len(recent_races) == 0:
            return self._default_form_features()
        
        # Extract metrics
        positions = [r.final_position for r in recent_races if r.final_position]
        quali_positions = [r.grid_position for r in recent_races if r.grid_position]
        dnfs = [r.dnf for r in recent_races]
        
        # Avg finish position (L3, L5, L10)
        features['avg_finish_position_l3'] = np.mean(positions[:3]) if len(positions) >= 3 else np.mean(positions) if positions else 10.0
        features['avg_finish_position_l5'] = np.mean(positions[:5]) if len(positions) >= 5 else np.mean(positions) if positions else 10.0
        features['avg_finish_position_l10'] = np.mean(positions) if positions else 10.0
        
        # Avg qualifying position
        features['avg_qualifying_position_l3'] = np.mean(quali_positions[:3]) if len(quali_positions) >= 3 else 10.0
        features['avg_qualifying_position_l5'] = np.mean(quali_positions[:5]) if len(quali_positions) >= 5 else 10.0
        
        # Consistency
        features['finish_position_std_l5'] = np.std(positions[:5]) if len(positions) >= 5 else 0.0
        
        # DNF rate
        features['dnf_rate_l10'] = sum(dnfs) / len(dnfs) if dnfs else 0.0
        
        # Points per race (approximate)
        points_map = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
        points = [points_map.get(p, 0) for p in positions[:5] if p is not None]
        features['points_per_race_l5'] = np.mean(points) if points else 0.0
        
        # Position gain trend (linear regression slope)
        if len(positions) >= 3:
            x = np.arange(len(positions[:5]))
            y = np.array(positions[:5])
            if len(x) > 1 and len(y) > 1:
                slope = np.polyfit(x, y, 1)[0]
                features['position_gain_trend_l5'] = -slope  # Negative slope = improving
            else:
                features['position_gain_trend_l5'] = 0.0
        else:
            features['position_gain_trend_l5'] = 0.0
        
        # Podium rate
        podiums = [1 for p in positions[:5] if p and p <= 3]
        features['podium_rate_l5'] = len(podiums) / min(5, len(positions)) if positions else 0.0
        
        # Top 10 rate
        top10 = [1 for p in positions if p and p <= 10]
        features['top10_rate_l10'] = len(top10) / len(positions) if positions else 0.0
        
        # Race vs quali delta
        deltas = []
        for race in recent_races[:5]:
            if race.final_position and race.grid_position:
                deltas.append(race.grid_position - race.final_position)
        features['avg_race_vs_quali_delta_l5'] = np.mean(deltas) if deltas else 0.0
        
        return features
    
    def _default_form_features(self) -> Dict:
        """Default features for drivers with no history"""
        return {
            'avg_finish_position_l3': 15.0,
            'avg_finish_position_l5': 15.0,
            'avg_finish_position_l10': 15.0,
            'avg_qualifying_position_l3': 15.0,
            'avg_qualifying_position_l5': 15.0,
            'finish_position_std_l5': 5.0,
            'dnf_rate_l10': 0.1,
            'points_per_race_l5': 0.0,
            'position_gain_trend_l5': 0.0,
            'podium_rate_l5': 0.0,
            'top10_rate_l10': 0.0,
            'avg_race_vs_quali_delta_l5': 0.0
        }
    
    def _team_features(self, team_name: str, season: int, current_round: int) -> Dict:
        """Compute team performance features"""
        features = {}
        
        # Get recent races for this team
        team_races = self.db.query(DriverSession).join(Driver).join(DBSession).join(Event).filter(
            Driver.team_name == team_name,
            Event.season == season,
            Event.round < current_round,
            DBSession.session_type == 'R'
        ).all()
        
        if len(team_races) == 0:
            return {
                'team_avg_finish_l5': 10.0,
                'team_avg_quali_l5': 10.0,
                'team_reliability_rate_l10': 0.9
            }
        
        positions = [r.final_position for r in team_races if r.final_position]
        quali_positions = [r.grid_position for r in team_races if r.grid_position]
        dnfs = [r.dnf for r in team_races]
        
        features['team_avg_finish_l5'] = np.mean(positions[:10]) if positions else 10.0
        features['team_avg_quali_l5'] = np.mean(quali_positions[:10]) if quali_positions else 10.0
        features['team_reliability_rate_l10'] = 1.0 - (sum(dnfs) / len(dnfs)) if dnfs else 0.9
        
        return features
    
    def _track_features(self, circuit_key: str, driver_id: int) -> Dict:
        """Compute track-specific features"""
        features = {}
        
        # Get driver's historical performance at this track
        track_races = self.db.query(DriverSession).join(DBSession).join(Event).filter(
            DriverSession.driver_id == driver_id,
            Event.circuit_key == circuit_key,
            DBSession.session_type == 'R'
        ).all()
        
        if len(track_races) > 0:
            positions = [r.final_position for r in track_races if r.final_position]
            quali_positions = [r.grid_position for r in track_races if r.grid_position]
            
            features['driver_avg_finish_at_track'] = np.mean(positions) if positions else 10.0
            features['driver_best_finish_at_track'] = min(positions) if positions else 20
            features['driver_avg_quali_at_track'] = np.mean(quali_positions) if quali_positions else 10.0
        else:
            features['driver_avg_finish_at_track'] = 10.0
            features['driver_best_finish_at_track'] = 20
            features['driver_avg_quali_at_track'] = 10.0
        
        # Track characteristics (computed from historical data)
        features['track_overtaking_difficulty'] = self._compute_overtaking_difficulty(circuit_key)
        features['track_safety_car_likelihood'] = self._compute_safety_car_likelihood(circuit_key)
        
        return features
    
    def _compute_overtaking_difficulty(self, circuit_key: str) -> float:
        """Compute overtaking difficulty (higher = harder to overtake)"""
        # Based on average position changes in recent races
        races = self.db.query(DriverSession).join(DBSession).join(Event).filter(
            Event.circuit_key == circuit_key,
            DBSession.session_type == 'R'
        ).limit(10).all()
        
        if len(races) == 0:
            return 0.5  # Default
        
        position_changes = []
        for race in races:
            if race.grid_position and race.final_position:
                position_changes.append(abs(race.grid_position - race.final_position))
        
        avg_change = np.mean(position_changes) if position_changes else 2.0
        # Normalize: low change = high difficulty
        return 1.0 - min(avg_change / 10.0, 1.0)
    
    def _compute_safety_car_likelihood(self, circuit_key: str) -> float:
        """Compute safety car likelihood"""
        # Count safety car events at this track
        sc_count = self.db.query(func.count()).select_from(RaceControl).join(DBSession).join(Event).filter(
            Event.circuit_key == circuit_key,
            RaceControl.flag_type.in_(['SC', 'VSC'])
        ).scalar()
        
        total_races = self.db.query(func.count()).select_from(DBSession).join(Event).filter(
            Event.circuit_key == circuit_key,
            DBSession.session_type == 'R'
        ).scalar()
        
        return (sc_count / total_races) if total_races > 0 else 0.2
    
    def _practice_features(self, session_id: int, driver_id: int) -> Dict:
        """Extract features from practice sessions"""
        features = {}
        
        # Get event_id from session
        session = self.db.query(DBSession).filter(DBSession.session_id == session_id).first()
        event_id = session.event_id
        
        # Get FP2 or FP3 sessions (for long run data)
        fp_sessions = self.db.query(DBSession).filter(
            DBSession.event_id == event_id,
            DBSession.session_type.in_(['FP2', 'FP3'])
        ).all()
        
        if len(fp_sessions) == 0:
            return self._default_practice_features()
        
        # Get driver's practice laps
        for fp_session in fp_sessions:
            driver_session = self.db.query(DriverSession).filter(
                DriverSession.session_id == fp_session.session_id,
                DriverSession.driver_id == driver_id
            ).first()
            
            if driver_session:
                laps = self.db.query(Lap).filter(
                    Lap.driver_session_id == driver_session.driver_session_id,
                    Lap.is_accurate == True
                ).order_by(Lap.lap_number).all()
                
                if len(laps) > 5:
                    # Long run analysis (consecutive laps on same tyre)
                    lap_times = [l.lap_time for l in laps[2:] if l.lap_time and not l.pit_out_lap]
                    
                    if len(lap_times) >= 5:
                        features['fp_long_run_avg_lap'] = np.mean(lap_times)
                        features['fp_long_run_consistency'] = np.std(lap_times)
                        
                        # Degradation: lap time trend
                        x = np.arange(len(lap_times[:10]))
                        y = np.array(lap_times[:10])
                        if len(x) > 3:
                            slope = np.polyfit(x, y, 1)[0]
                            features['fp_long_run_degradation'] = slope
                    
                # Best lap
                best_lap = min([l.lap_time for l in laps if l.lap_time], default=None)
                if best_lap:
                    features['fp_best_lap_time'] = best_lap
                    
                    # Rank among drivers
                    all_best_laps = self.db.query(
                        func.min(Lap.lap_time)
                    ).join(DriverSession).filter(
                        DriverSession.session_id == fp_session.session_id,
                        Lap.lap_time.isnot(None)
                    ).group_by(DriverSession.driver_id).all()
                    
                    best_laps = [l[0] for l in all_best_laps if l[0]]
                    best_laps.sort()
                    features['fp_best_lap_rank'] = best_laps.index(best_lap) + 1 if best_lap in best_laps else 20
        
        # Fill defaults if not computed
        if 'fp_long_run_avg_lap' not in features:
            features.update(self._default_practice_features())
        
        return features
    
    def _default_practice_features(self) -> Dict:
        return {
            'fp_long_run_avg_lap': 90.0,
            'fp_long_run_degradation': 0.05,
            'fp_long_run_consistency': 0.5,
            'fp_best_lap_time': 90.0,
            'fp_best_lap_rank': 10
        }
    
    def _qualifying_features(self, session_id: int, driver_id: int) -> Dict:
        """Extract qualifying features"""
        features = {}
        
        # Get qualifying session for this event
        session = self.db.query(DBSession).filter(DBSession.session_id == session_id).first()
        quali_session = self.db.query(DBSession).filter(
            DBSession.event_id == session.event_id,
            DBSession.session_type == 'Q'
        ).first()
        
        if not quali_session:
            return {'grid_position': 20, 'quali_gap_to_pole': 2.0}
        
        driver_session = self.db.query(DriverSession).filter(
            DriverSession.session_id == quali_session.session_id,
            DriverSession.driver_id == driver_id
        ).first()
        
        if driver_session and driver_session.grid_position:
            features['grid_position'] = driver_session.grid_position
            
            # Get pole time
            pole_lap = self.db.query(Lap).join(DriverSession).filter(
                DriverSession.session_id == quali_session.session_id,
                Lap.lap_time.isnot(None)
            ).order_by(Lap.lap_time).first()
            
            driver_best = self.db.query(func.min(Lap.lap_time)).join(DriverSession).filter(
                DriverSession.driver_session_id == driver_session.driver_session_id
            ).scalar()
            
            if pole_lap and driver_best:
                features['quali_gap_to_pole'] = driver_best - pole_lap.lap_time
            else:
                features['quali_gap_to_pole'] = 1.0
        else:
            features['grid_position'] = 20
            features['quali_gap_to_pole'] = 2.0
        
        return features
    
    def _strategy_features(self, session_id: int, driver_id: int) -> Dict:
        """Compute strategy-related features"""
        # Placeholder for tyre allocation data (would need additional data source)
        return {
            'expected_pit_stops': 1.5,
            'track_pit_loss_time': 22.0
        }
    
    def _weather_features(self, session_id: int) -> Dict:
        """Extract weather features"""
        weather = self.db.query(Weather).filter(
            Weather.session_id == session_id
        ).first()
        
        if weather:
            return {
                'race_air_temp': float(weather.air_temp) if weather.air_temp else 25.0,
                'race_track_temp': float(weather.track_temp) if weather.track_temp else 35.0,
                'race_humidity': weather.humidity if weather.humidity else 50,
                'race_wind_speed': float(weather.wind_speed) if weather.wind_speed else 5.0,
                'race_rainfall_expected': weather.rainfall
            }
        return {
            'race_air_temp': 25.0,
            'race_track_temp': 35.0,
            'race_humidity': 50,
            'race_wind_speed': 5.0,
            'race_rainfall_expected': False
        }
    
    def _context_features(self, season: int, round_num: int, driver_id: int) -> Dict:
        """Compute contextual features"""
        # Total races in season (approximate)
        total_races = 22
        
        return {
            'season_race_number': round_num,
            'races_remaining': max(0, total_races - round_num),
            'championship_position': 10  # Would need standings data
        }
    
    def save_features_to_db(self, features_df: pd.DataFrame):
        """Save computed features to feature store"""
        for _, row in features_df.iterrows():
            driver_session_id = row['driver_session_id']
            
            # Remove metadata columns
            feature_cols = [col for col in row.index if col not in ['driver_session_id', 'driver_id']]
            
            for feature_name in feature_cols:
                feature = FeatureStore(
                    driver_session_id=driver_session_id,
                    feature_name=feature_name,
                    feature_value=float(row[feature_name]) if pd.notna(row[feature_name]) else None,
                    feature_category=self._categorize_feature(feature_name)
                )
                self.db.add(feature)
        
        self.db.commit()
    
    def _categorize_feature(self, feature_name: str) -> str:
        """Categorize feature by prefix"""
        if feature_name.startswith('avg_finish') or feature_name.startswith('dnf_rate'):
            return 'driver_form'
        elif feature_name.startswith('team_'):
            return 'team_performance'
        elif feature_name.startswith('driver_') and 'track' in feature_name:
            return 'track_specific'
        elif feature_name.startswith('fp_'):
            return 'practice'
        elif feature_name.startswith('grid') or feature_name.startswith('quali'):
            return 'qualifying'
        elif feature_name.startswith('race_'):
            return 'weather'
        else:
            return 'context'
