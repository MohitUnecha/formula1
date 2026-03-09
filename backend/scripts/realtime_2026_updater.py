#!/usr/bin/env python3
"""
Real-time 2026 Data Refresh System
- Fetches new race data every minute/hour
- Updates driver standings, session results
- Streams caddy/team radio data
- Supports WebSocket for live updates
"""
import sys
sys.path.insert(0, '/Users/mohitunecha/F1/backend')

import asyncio
import fastf1
from datetime import datetime
from sqlalchemy import text
import logging
from typing import Optional, Dict, List
from database import SessionLocal
from models import Event, Session as DBSession, Driver, DriverSession, IngestLog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enable FastF1 caching
fastf1.Cache.enable_cache('./data/fastf1_cache')


class RealtimeF1Update:
    """Real-time 2026 season data updater"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.last_update = None
        self.is_race_weekend = False
        self.current_session = None
    
    async def start_continuous_update(self, interval_seconds: int = 300):
        """
        Start continuous update loop
        
        Args:
            interval_seconds: Update interval (default 5 minutes for testing)
        """
        logger.info("🏎️  Starting Real-time 2026 Update System")
        logger.info(f"Update interval: {interval_seconds} seconds")
        
        while True:
            try:
                await self.fetch_2026_updates()
                self.last_update = datetime.utcnow()
                logger.info(f"✅ Update completed at {self.last_update}")
                
                # Wait before next update
                await asyncio.sleep(interval_seconds)
            
            except Exception as e:
                logger.error(f"❌ Update failed: {str(e)}")
                # Wait before retry
                await asyncio.sleep(60)
    
    async def fetch_2026_updates(self):
        """Fetch latest 2026 data"""
        try:
            logger.info("Checking 2026 schedule...")
            
            schedule = fastf1.get_event_schedule(2026)
            if schedule is None or schedule.empty:
                logger.warning("No 2026 schedule available yet")
                return
            
            # Check for upcoming/ongoing races
            today = datetime.utcnow().date()
            
            for idx, row in schedule.iterrows():
                event_date = pd.to_datetime(row['EventDate']).date()
                
                # Check if race is this week (or ongoing)
                days_until = (event_date - today).days
                
                if -7 <= days_until <= 7:  # Within 1 week before/after event
                    logger.info(f"🏁 Found active race week: {row['EventName']} ({event_date})")
                    self.is_race_weekend = True
                    
                    # Try to fetch session data
                    try:
                        await self.fetch_session_data(
                            2026, 
                            row['RoundNumber'],
                            event_date
                        )
                    except Exception as e:
                        logger.debug(f"  Session fetch error: {str(e)[:60]}")
                
            if not self.is_race_weekend:
                logger.debug("  No active races in next week")
        
        except Exception as e:
            logger.error(f"Failed to fetch 2026 updates: {str(e)}")
    
    async def fetch_session_data(self, year: int, round_num: int, event_date):
        """Fetch specific session data"""
        try:
            logger.info(f"  Fetching session data for round {round_num}...")
            
            # Try all session types
            session_types = ['FP1', 'FP2', 'FP3', 'Q', 'R', 'S']
            
            for session_type in session_types:
                try:
                    session_data = fastf1.get_session(year, round_num, session_type)
                    
                    if session_data and hasattr(session_data, 'results'):
                        logger.info(f"    ✓ {session_type} results available")
                        self.current_session = {
                            'type': session_type,
                            'date': session_data.date,
                            'results_count': len(session_data.results)
                        }
                        
                        # Update DB with latest results
                        await self.update_session_results(session_data, session_type)
                
                except Exception as e:
                    logger.debug(f"    {session_type} not available yet")
                    continue
        
        except Exception as e:
            logger.error(f"Failed to fetch session data: {str(e)}")
    
    async def update_session_results(self, session_data, session_type: str):
        """Update session results in database"""
        try:
            if not hasattr(session_data, 'results'):
                return
            
            # Get or create event/session
            event = self.db.query(Event).filter(
                Event.season == 2026,
                Event.event_date == session_data.date
            ).first()
            
            if not event:
                logger.warning(f"Event not found for {session_data.date}")
                return
            
            # Get or create session
            db_session = self.db.query(DBSession).filter(
                DBSession.event_id == event.event_id,
                DBSession.session_type == session_type
            ).first()
            
            if not db_session:
                db_session = DBSession(
                    event_id=event.event_id,
                    session_type=session_type,
                    session_date=session_data.date,
                )
                self.db.add(db_session)
                self.db.commit()
            
            # Update driver results
            for _, driver_row in session_data.results.iterrows():
                try:
                    driver = self.db.query(Driver).filter(
                        Driver.driver_code == str(driver_row.get('DriverNumber', '0'))
                    ).first()
                    
                    if driver:
                        # Update or create driver session
                        driver_session = self.db.query(DriverSession).filter(
                            DriverSession.session_id == db_session.session_id,
                            DriverSession.driver_id == driver.driver_id
                        ).first()
                        
                        if driver_session:
                            # Update existing
                            driver_session.position = int(driver_row.get('Position', 0)) or None
                            driver_session.points = float(driver_row.get('Points', 0)) or None
                            driver_session.status = str(driver_row.get('Status', 'Unknown'))
                        else:
                            # Create new
                            driver_session = DriverSession(
                                session_id=db_session.session_id,
                                driver_id=driver.driver_id,
                                position=int(driver_row.get('Position', 0)) or None,
                                grid=int(driver_row.get('GridPosition', 0)) or None,
                                points=float(driver_row.get('Points', 0)) or None,
                                status=str(driver_row.get('Status', 'Unknown')),
                            )
                            self.db.add(driver_session)
                
                except Exception as e:
                    logger.debug(f"    Driver update error: {str(e)[:50]}")
                    continue
            
            self.db.commit()
            logger.info(f"    ✓ Updated {session_type} results")
        
        except Exception as e:
            logger.error(f"Failed to update session results: {str(e)}")
    
    async def get_caddy_data(self, session_id: int) -> Optional[List[Dict]]:
        """
        Get team radio / caddy data for a session
        Future: Integrate with F1Data or official radio stream
        """
        # Placeholder for caddy/team radio integration
        logger.debug("Fetching caddy data...")
        return []


async def main():
    """Main entry point"""
    updater = RealtimeF1Update()
    
    # Start update loop (every 5 minutes for testing, normally every minute)
    try:
        await updater.start_continuous_update(interval_seconds=300)
    except KeyboardInterrupt:
        logger.info("Stopping real-time updater")


if __name__ == "__main__":
    import pandas as pd
    
    # Run async main
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("✅ Real-time updater stopped")
