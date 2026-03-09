"""
API Router: Sessions

Endpoints for session data
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import Session as DBSession, DriverSession, Driver, Event
from team_mapping import get_team_for_driver

router = APIRouter()


class SessionResponse(BaseModel):
    session_id: int
    event_id: int
    event_name: str
    session_type: str
    session_date: datetime
    total_laps: int
    track_length_km: float
    driver_count: int
    
    class Config:
        from_attributes = True


class DriverSessionResponse(BaseModel):
    driver_code: str
    driver_name: str
    team_name: str
    grid: int | None = None
    position: int | None = None
    points: float | None = None
    dnf: bool
    fastest_lap: float | None = None
    status: str = ""
    
    class Config:
        from_attributes = True


@router.get("/events/{event_id}/sessions", response_model=List[SessionResponse])
async def get_sessions(event_id: int, db: Session = Depends(get_db)):
    """Get all sessions for an event"""
    sessions = db.query(DBSession).filter(
        DBSession.event_id == event_id
    ).order_by(DBSession.session_date).all()
    
    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found for this event")
    
    result = []
    for session in sessions:
        driver_count = db.query(DriverSession).filter(
            DriverSession.session_id == session.session_id
        ).count()
        
        result.append(SessionResponse(
            session_id=session.session_id,
            event_id=session.event_id,
            event_name=session.event.event_name,
            session_type=session.session_type,
            session_date=session.session_date,
            total_laps=session.total_laps or 0,
            track_length_km=float(session.track_length_km or 0),
            driver_count=driver_count
        ))
    
    return result


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get single session details"""
    session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    driver_count = db.query(DriverSession).filter(
        DriverSession.session_id == session_id
    ).count()
    
    return SessionResponse(
        session_id=session.session_id,
        event_id=session.event_id,
        event_name=session.event.event_name,
        session_type=session.session_type,
        session_date=session.session_date,
        total_laps=session.total_laps or 0,
        track_length_km=float(session.track_length_km or 0),
        driver_count=driver_count
    )


@router.get("/sessions/{session_id}/drivers", response_model=List[DriverSessionResponse])
async def get_session_drivers(session_id: int, db: Session = Depends(get_db)):
    """Get all drivers in a session with their results"""
    session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    event = db.query(Event).filter(Event.event_id == session.event_id).first() if session else None
    season = event.season if event else 0

    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id
    ).all()
    
    if not driver_sessions:
        raise HTTPException(status_code=404, detail="No drivers found for this session")
    
    result = []
    for ds in driver_sessions:
        team_info = get_team_for_driver(ds.driver.driver_code, season) if season else None
        team_name = team_info[0] if team_info else (ds.driver.team_name or "")
        result.append(DriverSessionResponse(
            driver_code=ds.driver.driver_code,
            driver_name=f"{ds.driver.first_name} {ds.driver.last_name}",
            team_name=team_name,
            grid=ds.grid,
            position=ds.position,
            points=float(ds.points) if ds.points is not None else None,
            dnf=ds.dnf or False,
            fastest_lap=float(ds.fastest_lap) if ds.fastest_lap is not None else None,
            status=ds.status or ""
        ))
    return result
