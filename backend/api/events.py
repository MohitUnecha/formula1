"""
API Router: Events

Endpoints for Grand Prix events
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import date

from database import get_db
from models import Event, Session as DBSession

router = APIRouter()


class EventResponse(BaseModel):
    event_id: int
    season: int
    round: int
    event_name: str
    event_date: date
    event_format: str
    country: str
    location: str
    circuit_key: str
    session_count: int
    has_sprint: bool
    
    class Config:
        from_attributes = True


@router.get("/seasons/{season}/events", response_model=List[EventResponse])
async def get_events(season: int, db: Session = Depends(get_db)):
    """
    Get all events for a season
    
    Args:
        season: Season year
        
    Returns:
        List of Grand Prix events
    """
    events = db.query(Event).filter(Event.season == season).order_by(Event.round).all()
    
    if not events:
        raise HTTPException(status_code=404, detail=f"No events found for season {season}")
    
    result = []
    for event in events:
        session_count = db.query(DBSession).filter(DBSession.event_id == event.event_id).count()
        sprint_session_count = db.query(DBSession).filter(
            DBSession.event_id == event.event_id,
            DBSession.session_type.in_(["S", "SS", "SQ", "Sprint", "Sprint Shootout", "Sprint Qualifying"]),
        ).count()
        has_sprint = sprint_session_count > 0 or ("sprint" in (event.event_format or "").lower())
        
        result.append(EventResponse(
            event_id=event.event_id,
            season=event.season,
            round=event.round,
            event_name=event.event_name,
            event_date=event.event_date,
            event_format=event.event_format or "conventional",
            country=event.country or "",
            location=event.location or "",
            circuit_key=event.circuit_key or "",
            session_count=session_count,
            has_sprint=has_sprint,
        ))
    
    return result


@router.get("/events", response_model=List[EventResponse])
async def get_events_by_query(season: int = Query(..., ge=1950), db: Session = Depends(get_db)):
    """Compatibility endpoint for clients that pass season as a query param."""
    return await get_events(season=season, db=db)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get single event details"""
    event = db.query(Event).filter(Event.event_id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    session_count = db.query(DBSession).filter(DBSession.event_id == event_id).count()
    sprint_session_count = db.query(DBSession).filter(
        DBSession.event_id == event_id,
        DBSession.session_type.in_(["S", "SS", "SQ", "Sprint", "Sprint Shootout", "Sprint Qualifying"]),
    ).count()
    has_sprint = sprint_session_count > 0 or ("sprint" in (event.event_format or "").lower())
    
    return EventResponse(
        event_id=event.event_id,
        season=event.season,
        round=event.round,
        event_name=event.event_name,
        event_date=event.event_date,
        event_format=event.event_format or "conventional",
        country=event.country or "",
        location=event.location or "",
        circuit_key=event.circuit_key or "",
        session_count=session_count,
        has_sprint=has_sprint,
    )
