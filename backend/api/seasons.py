"""
API Router: Seasons

Endpoints for season metadata
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from pydantic import BaseModel

from database import get_db
from models import Event

router = APIRouter()


class SeasonResponse(BaseModel):
    season: int
    total_events: int
    
    class Config:
        from_attributes = True


@router.get("/seasons", response_model=List[int])
async def get_seasons(db: Session = Depends(get_db)):
    """
    Get list of all available seasons
    
    Returns:
        List of season years
    """
    seasons = db.query(Event.season).distinct().order_by(Event.season.desc()).all()
    return [s[0] for s in seasons]


@router.get("/seasons/{season}", response_model=SeasonResponse)
async def get_season_details(season: int, db: Session = Depends(get_db)):
    """
    Get details for a specific season
    
    Args:
        season: Season year (e.g., 2024)
        
    Returns:
        Season details with event count
    """
    event_count = db.query(func.count(Event.event_id)).filter(
        Event.season == season
    ).scalar()
    
    if event_count == 0:
        raise HTTPException(status_code=404, detail=f"Season {season} not found")
    
    return SeasonResponse(season=season, total_events=event_count)
