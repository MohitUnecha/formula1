"""
API Router: Drivers

Endpoints for driver data, standings, and information
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import Driver, DriverSession, Session as DBSession, Event, Constructor
from team_mapping import get_team_for_driver, get_driver_name, get_season_drivers

router = APIRouter(prefix="/api", tags=["drivers"])


F1_MEDIA_BASE = "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers"

# Driver metadata with debut year to filter out incorrect data (some codes were reused by different drivers)
DRIVER_PROFILE_META: dict[str, dict[str, object]] = {
    "VER": {"first_name": "Max", "last_name": "Verstappen", "driver_number": 1, "nationality": "Dutch", "debut_year": 2015, "folder": "MAXVER01_Max_Verstappen", "file": "maxver01"},
    "LAW": {"first_name": "Liam", "last_name": "Lawson", "driver_number": 30, "nationality": "New Zealander", "debut_year": 2023, "folder": "LIALAW01_Liam_Lawson", "file": "lialaw01"},
    "LEC": {"first_name": "Charles", "last_name": "Leclerc", "driver_number": 16, "nationality": "Monegasque", "debut_year": 2018, "folder": "CHALEC01_Charles_Leclerc", "file": "chalec01"},
    "HAM": {"first_name": "Lewis", "last_name": "Hamilton", "driver_number": 44, "nationality": "British", "debut_year": 2007, "folder": "LEWHAM01_Lewis_Hamilton", "file": "lewham01"},
    "NOR": {"first_name": "Lando", "last_name": "Norris", "driver_number": 4, "nationality": "British", "debut_year": 2019, "folder": "LANNOR01_Lando_Norris", "file": "lannor01"},
    "PIA": {"first_name": "Oscar", "last_name": "Piastri", "driver_number": 81, "nationality": "Australian", "debut_year": 2023, "folder": "OSCPIA01_Oscar_Piastri", "file": "oscpia01"},
    "RUS": {"first_name": "George", "last_name": "Russell", "driver_number": 63, "nationality": "British", "debut_year": 2019, "folder": "GEORUS01_George_Russell", "file": "georus01"},
    "ANT": {"first_name": "Kimi", "last_name": "Antonelli", "driver_number": 12, "nationality": "Italian", "debut_year": 2025, "folder": "KIMAN01_Kimi_Antonelli", "file": "kiman01"},
    "ALO": {"first_name": "Fernando", "last_name": "Alonso", "driver_number": 14, "nationality": "Spanish", "debut_year": 2001, "folder": "FERALO01_Fernando_Alonso", "file": "feralo01"},
    "STR": {"first_name": "Lance", "last_name": "Stroll", "driver_number": 18, "nationality": "Canadian", "debut_year": 2017, "folder": "LANSTR01_Lance_Stroll", "file": "lanstr01"},
    "GAS": {"first_name": "Pierre", "last_name": "Gasly", "driver_number": 10, "nationality": "French", "debut_year": 2017, "folder": "PIEGAS01_Pierre_Gasly", "file": "piegas01"},
    "DOO": {"first_name": "Jack", "last_name": "Doohan", "driver_number": 7, "nationality": "Australian", "debut_year": 2025, "folder": "JACDOO01_Jack_Doohan", "file": "jacdoo01"},
    "ALB": {"first_name": "Alexander", "last_name": "Albon", "driver_number": 23, "nationality": "Thai", "debut_year": 2019, "folder": "ALEALB01_Alexander_Albon", "file": "alealb01"},
    "SAI": {"first_name": "Carlos", "last_name": "Sainz", "driver_number": 55, "nationality": "Spanish", "debut_year": 2015, "folder": "CARSAR01_Carlos_Sainz", "file": "carsar01"},
    "OCO": {"first_name": "Esteban", "last_name": "Ocon", "driver_number": 31, "nationality": "French", "debut_year": 2016, "folder": "ESTOCO01_Esteban_Ocon", "file": "estoco01"},
    "BEA": {"first_name": "Oliver", "last_name": "Bearman", "driver_number": 87, "nationality": "British", "debut_year": 2024, "folder": "OLIBEA01_Oliver_Bearman", "file": "olibea01"},
    "LIN": {"first_name": "Arvid", "last_name": "Lindblad", "driver_number": 45, "nationality": "British", "debut_year": 2026, "folder": "ARVLIN01_Arvid_Lindblad", "file": "arvlin01"},
    "HAD": {"first_name": "Isack", "last_name": "Hadjar", "driver_number": 6, "nationality": "French", "debut_year": 2025, "folder": "ISAHAD01_Isack_Hadjar", "file": "isahad01"},
    "PER": {"first_name": "Sergio", "last_name": "Perez", "driver_number": 11, "nationality": "Mexican", "debut_year": 2011, "folder": "SERPER01_Sergio_Perez", "file": "serper01"},
    "BOT": {"first_name": "Valtteri", "last_name": "Bottas", "driver_number": 77, "nationality": "Finnish", "debut_year": 2013, "folder": "VALBOT01_Valtteri_Bottas", "file": "valbot01"},
    "HUL": {"first_name": "Nico", "last_name": "Hulkenberg", "driver_number": 27, "nationality": "German", "debut_year": 2010, "folder": "NICHUL01_Nico_Hulkenberg", "file": "nichul01"},
    "BOR": {"first_name": "Gabriel", "last_name": "Bortoleto", "driver_number": 5, "nationality": "Brazilian", "debut_year": 2025, "folder": "GABORT01_Gabriel_Bortoleto", "file": "gabort01"},
    "TSU": {"first_name": "Yuki", "last_name": "Tsunoda", "driver_number": 22, "nationality": "Japanese", "debut_year": 2021, "folder": "YUKTSU01_Yuki_Tsunoda", "file": "yuktsu01"},
    "MAG": {"first_name": "Kevin", "last_name": "Magnussen", "driver_number": 20, "nationality": "Danish", "debut_year": 2014, "folder": "KEVMAG01_Kevin_Magnussen", "file": "kevmag01"},
    "ZHO": {"first_name": "Zhou", "last_name": "Guanyu", "driver_number": 24, "nationality": "Chinese", "debut_year": 2022, "folder": "ZHOGUA01_Zhou_Guanyu", "file": "zhogua01"},
    "RIC": {"first_name": "Daniel", "last_name": "Ricciardo", "driver_number": 3, "nationality": "Australian", "debut_year": 2011, "folder": "DANRIC01_Daniel_Ricciardo", "file": "danric01"},
    "MSC": {"first_name": "Mick", "last_name": "Schumacher", "driver_number": 47, "nationality": "German", "debut_year": 2021, "folder": "MICSCH01_Mick_Schumacher", "file": "micsch01"},
    "DEV": {"first_name": "Nyck", "last_name": "De Vries", "driver_number": 21, "nationality": "Dutch", "debut_year": 2023, "folder": "NYCDEV01_Nyck_De_Vries", "file": "nycdev01"},
    "SAR": {"first_name": "Logan", "last_name": "Sargeant", "driver_number": 2, "nationality": "American", "debut_year": 2023, "folder": "LOGSAR01_Logan_Sargeant", "file": "logsar01"},
    "LAT": {"first_name": "Nicholas", "last_name": "Latifi", "driver_number": 6, "nationality": "Canadian", "debut_year": 2020, "folder": "NICLAT01_Nicholas_Latifi", "file": "niclat01"},
    "VET": {"first_name": "Sebastian", "last_name": "Vettel", "driver_number": 5, "nationality": "German", "debut_year": 2007, "folder": "SEBVET01_Sebastian_Vettel", "file": "sebvet01"},
}


def _formula1_photo_url(driver_code: str) -> Optional[str]:
    meta = DRIVER_PROFILE_META.get(driver_code.upper())
    if not meta:
        return None
    folder = str(meta.get("folder", ""))
    file_name = str(meta.get("file", ""))
    if not folder or not file_name:
        return None
    first_char = folder[0].lower()
    return f"{F1_MEDIA_BASE}/{first_char}/{folder}/{file_name}.png"


def _fallback_season_drivers(season: int, db: Session) -> List[DriverResponse]:
    season_map = get_season_drivers(season)
    if not season_map:
        return []

    db_drivers = db.query(Driver).filter(Driver.driver_code.in_(list(season_map.keys()))).all()
    db_by_code = {d.driver_code.upper(): d for d in db_drivers}

    result: List[DriverResponse] = []
    for idx, (code, team_info) in enumerate(season_map.items()):
        code_up = code.upper()
        d = db_by_code.get(code_up)
        meta = DRIVER_PROFILE_META.get(code_up, {})
        name_override = get_driver_name(code_up, season)

        first = name_override[0] if name_override else str(meta.get("first_name") or (d.first_name if d else ""))
        last = name_override[1] if name_override else str(meta.get("last_name") or (d.last_name if d else ""))

        result.append(DriverResponse(
            driver_id=d.driver_id if d else 900000 + idx,
            driver_code=code_up,
            driver_number=(d.driver_number if d and d.driver_number is not None else meta.get("driver_number")),
            first_name=first,
            last_name=last,
            nationality=d.nationality if d and d.nationality else (str(meta.get("nationality")) if meta.get("nationality") else None),
            team_name=team_info[0],
            photo_url=(d.photo_url if d and d.photo_url else _formula1_photo_url(code_up)),
            biography=d.biography if d else None,
        ))

    result.sort(key=lambda r: (r.team_name or "", r.last_name or r.driver_code))
    return result


class DriverResponse(BaseModel):
    driver_id: int
    driver_code: str
    driver_number: Optional[int]
    first_name: str
    last_name: str
    nationality: Optional[str]
    team_name: Optional[str]
    photo_url: Optional[str]
    biography: Optional[str]
    
    class Config:
        from_attributes = True


class DriverStandingResponse(BaseModel):
    driver_code: str
    driver_name: str
    photo_url: Optional[str]
    team_name: Optional[str]
    total_points: float
    wins: int
    podiums: int
    dnfs: int
    
    class Config:
        from_attributes = True


class ConstructorStandingResponse(BaseModel):
    constructor_id: Optional[int] = None
    constructor_name: str
    total_points: float
    wins: int
    podiums: int
    drivers_count: int
    
    class Config:
        from_attributes = True


@router.get("/drivers", response_model=List[DriverResponse])
async def get_drivers(
    season: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all drivers, optionally filtered by season"""
    if season:
        # Get drivers that participated in a specific season
        drivers = db.query(Driver).join(
            DriverSession
        ).join(
            DBSession
        ).join(
            Event
        ).filter(
            Event.season == season
        ).distinct().all()
        
        # Apply season-correct team mappings and name overrides
        result = []
        for d in drivers:
            team_info = get_team_for_driver(d.driver_code, season)
            name_override = get_driver_name(d.driver_code, season)
            first = name_override[0] if name_override else (d.first_name or '')
            last = name_override[1] if name_override else (d.last_name or '')
            result.append(DriverResponse(
                driver_id=d.driver_id,
                driver_code=d.driver_code,
                driver_number=d.driver_number,
                first_name=first,
                last_name=last,
                nationality=d.nationality,
                team_name=team_info[0] if team_info else (d.team_name or ''),
                photo_url=d.photo_url,
                biography=d.biography,
            ))
        if result:
            return result

        # Fallback for seasons where events exist but session/driver rows are not ingested yet
        return _fallback_season_drivers(season, db)
    else:
        # Get all drivers
        drivers = db.query(Driver).order_by(Driver.last_name).all()
    
    return drivers


@router.get("/drivers/{driver_code}", response_model=DriverResponse)
async def get_driver(driver_code: str, db: Session = Depends(get_db)):
    """Get driver by code"""
    driver = db.query(Driver).filter(
        Driver.driver_code == driver_code.upper()
    ).first()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    return driver


@router.get("/standings/{season}", response_model=List[DriverStandingResponse])
async def get_standings(season: int, db: Session = Depends(get_db)):
    """Get championship standings for a season"""
    from sqlalchemy import case
    
    # Get all drivers who participated in the season
    drivers_data = db.query(
        Driver.driver_code,
        Driver.first_name,
        Driver.last_name,
        Driver.photo_url,
        Driver.team_name,
        func.sum(DriverSession.points).label('total_points'),
        func.count(
            case(
                (DriverSession.position == 1, 1),
                else_=None
            )
        ).label('wins'),
        func.count(
            case(
                (DriverSession.position.in_([1, 2, 3]), 1),
                else_=None
            )
        ).label('podiums'),
        func.count(
            case(
                (DriverSession.status == 'DNF', 1),
                else_=None
            )
        ).label('dnfs')
    ).join(
        DriverSession
    ).join(
        DBSession
    ).join(
        Event
    ).filter(
        Event.season == season
    ).group_by(
        Driver.driver_id
    ).order_by(
        func.sum(DriverSession.points).desc()
    ).all()
    
    if drivers_data:
        result = []
        for row in drivers_data:
            # Use season-correct team name and driver name
            team_info = get_team_for_driver(row.driver_code, season)
            team_name = team_info[0] if team_info else (row.team_name or '')
            name_override = get_driver_name(row.driver_code, season)
            if name_override:
                display_name = f"{name_override[0]} {name_override[1]}"
            else:
                display_name = f"{row.first_name} {row.last_name}"
            result.append(DriverStandingResponse(
                driver_code=row.driver_code,
                driver_name=display_name,
                photo_url=row.photo_url,
                team_name=team_name,
                total_points=float(row.total_points or 0),
                wins=row.wins or 0,
                podiums=row.podiums or 0,
                dnfs=row.dnfs or 0
            ))
        return result
    
    # Fallback: Generate standings from season driver mapping (for future seasons with no race data yet)
    season_drivers = get_season_drivers(season)
    if not season_drivers:
        raise HTTPException(status_code=404, detail="No standings found for this season")
    
    # Build response with 0 points for all drivers on the 2026 grid
    result = []
    for driver_code, (team_name, team_color) in season_drivers.items():
        name_override = get_driver_name(driver_code, season)
        if name_override:
            display_name = f"{name_override[0]} {name_override[1]}"
        else:
            # Try to get from DB
            driver = db.query(Driver).filter(Driver.driver_code == driver_code).first()
            if driver:
                display_name = f"{driver.first_name} {driver.last_name}"
            else:
                display_name = driver_code
        
        # Get photo URL from DB if available
        driver = db.query(Driver).filter(Driver.driver_code == driver_code).first()
        photo_url = driver.photo_url if driver else None
        
        result.append(DriverStandingResponse(
            driver_code=driver_code,
            driver_name=display_name,
            photo_url=photo_url,
            team_name=team_name,
            total_points=0.0,
            wins=0,
            podiums=0,
            dnfs=0
        ))
    
    return result


@router.get("/constructors/standings/{season}", response_model=List[ConstructorStandingResponse])
async def get_constructor_standings(season: int, db: Session = Depends(get_db)):
    """Get constructor championship standings for a season"""
    from sqlalchemy import case
    
    # Get all constructors who participated in the season
    constructors_data = db.query(
        Constructor.constructor_id,
        Constructor.constructor_name,
        func.sum(DriverSession.points).label('total_points'),
        func.count(
            case(
                (DriverSession.position == 1, 1),
                else_=None
            )
        ).label('wins'),
        func.count(
            case(
                (DriverSession.position.in_([1, 2, 3]), 1),
                else_=None
            )
        ).label('podiums'),
        func.count(func.distinct(Driver.driver_id)).label('drivers_count')
    ).join(
        Driver,
        Constructor.constructor_id == Driver.constructor_id
    ).join(
        DriverSession,
        Driver.driver_id == DriverSession.driver_id
    ).join(
        DBSession,
        DriverSession.session_id == DBSession.session_id
    ).join(
        Event,
        DBSession.event_id == Event.event_id
    ).filter(
        Event.season == season
    ).group_by(
        Constructor.constructor_id
    ).order_by(
        func.sum(DriverSession.points).desc()
    ).all()
    
    if constructors_data:
        result = []
        for row in constructors_data:
            result.append(ConstructorStandingResponse(
                constructor_id=row.constructor_id,
                constructor_name=row.constructor_name,
                total_points=float(row.total_points or 0),
                wins=row.wins or 0,
                podiums=row.podiums or 0,
                drivers_count=row.drivers_count or 0
            ))
        return result
    
    # Fallback: Generate standings from season driver mapping (for future seasons with no race data yet)
    season_drivers = get_season_drivers(season)
    if not season_drivers:
        raise HTTPException(status_code=404, detail="No constructor standings found for this season")
    
    # Extract unique teams from the season mapping
    teams_set: dict[str, list[str]] = {}
    for driver_code, (team_name, _) in season_drivers.items():
        if team_name not in teams_set:
            teams_set[team_name] = []
        teams_set[team_name].append(driver_code)
    
    # Build response with 0 points
    result = []
    for team_name, drivers in sorted(teams_set.items()):
        # Try to find constructor in DB for ID
        constructor = db.query(Constructor).filter(
            Constructor.constructor_name.ilike(f"%{team_name}%")
        ).first()
        
        result.append(ConstructorStandingResponse(
            constructor_id=constructor.constructor_id if constructor else None,
            constructor_name=team_name,
            total_points=0.0,
            wins=0,
            podiums=0,
            drivers_count=len(drivers)
        ))
    
    return result


@router.get("/constructors/{season}", response_model=List[dict])
async def get_constructors_by_season(season: int, db: Session = Depends(get_db)):
    """Get all constructors that participated in a season"""
    constructors = db.query(Constructor).join(
        Driver
    ).join(
        DriverSession
    ).join(
        DBSession
    ).join(
        Event
    ).filter(
        Event.season == season
    ).distinct().all()
    
    return [
        {
            'constructor_id': c.constructor_id,
            'constructor_name': c.constructor_name,
            'team_color': c.team_color,
            'nationality': c.nationality,
        }
        for c in constructors
    ]


# Team metadata (history, headquarters, etc.)
# Team logo URLs from official F1 media
TEAM_LOGO_BASE = "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos"

TEAM_METADATA: dict[str, dict] = {
    "Red Bull": {
        "full_name": "Oracle Red Bull Racing",
        "founded": 2005,
        "headquarters": "Milton Keynes, United Kingdom",
        "team_principal": "Laurent Mekies",
        "power_unit": "Ford-RBPT",
        "team_color": "#3671C6",
        "logo_url": "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos/red%20bull",
        "history": "Originally formed from the Jaguar Racing team purchased by Red Bull in 2004. Became one of the most dominant teams in F1 history with 6 consecutive Constructors' Championships (2010-2013, 2022-2024) and produced 4-time World Champions Sebastian Vettel and Max Verstappen.",
        "name_variants": ["Red Bull Racing", "Red Bull", "RBR"]
    },
    "Ferrari": {
        "full_name": "Scuderia Ferrari HP",
        "founded": 1950,
        "headquarters": "Maranello, Italy",
        "team_principal": "Frédéric Vasseur",
        "power_unit": "Ferrari",
        "team_color": "#E8002D",
        "logo_url": "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos/ferrari",
        "history": "The oldest and most successful team in F1 history. Founded by Enzo Ferrari, Ferrari has won 16 Constructors' Championships and produced legendary drivers including Michael Schumacher, Niki Lauda, and Lewis Hamilton.",
        "name_variants": ["Ferrari", "Scuderia Ferrari"]
    },
    "Mercedes": {
        "full_name": "Mercedes-AMG Petronas F1 Team",
        "founded": 2010,
        "headquarters": "Brackley, United Kingdom",
        "team_principal": "Toto Wolff",
        "power_unit": "Mercedes",
        "team_color": "#27F4D2",
        "logo_url": "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos/mercedes",
        "history": "Entered as a works team in 2010 after purchasing Brawn GP. Dominated the turbo-hybrid era with 8 consecutive Constructors' Championships (2014-2021), with Lewis Hamilton winning 6 titles with the team.",
        "name_variants": ["Mercedes", "Mercedes-AMG"]
    },
    "McLaren": {
        "full_name": "McLaren F1 Team",
        "founded": 1963,
        "headquarters": "Woking, United Kingdom",
        "team_principal": "Andrea Stella",
        "power_unit": "Mercedes",
        "team_color": "#FF8000",
        "logo_url": "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos/mclaren",
        "history": "One of the most successful teams in F1 with 8 Constructors' Championships. Produced legends like Ayrton Senna, Alain Prost, and Mika Häkkinen. Recently returned to competitiveness after years of rebuilding.",
        "name_variants": ["McLaren", "McLaren F1 Team"]
    },
    "Aston Martin": {
        "full_name": "Aston Martin Aramco F1 Team",
        "founded": 2021,
        "headquarters": "Silverstone, United Kingdom",
        "team_principal": "Mike Krack",
        "power_unit": "Honda",
        "team_color": "#229971",
        "logo_url": "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos/aston%20martin",
        "history": "Rebranded from Racing Point in 2021, with roots going back to Jordan Grand Prix (1991). Signed Fernando Alonso in 2023 and invested heavily in new facilities to challenge for championships.",
        "name_variants": ["Aston Martin", "Aston Martin Aramco"]
    },
    "Alpine": {
        "full_name": "BWT Alpine F1 Team",
        "founded": 2021,
        "headquarters": "Enstone, United Kingdom & Viry-Châtillon, France",
        "team_principal": "Oliver Oakes",
        "power_unit": "Renault",
        "team_color": "#0093CC",
        "logo_url": "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos/alpine",
        "history": "Renault's works team rebranded as Alpine in 2021. The Enstone factory has a rich history as Benetton (1986-2001), Renault (2002-2011), Lotus (2012-2015), and Renault again (2016-2020).",
        "name_variants": ["Alpine", "Alpine F1 Team"]
    },
    "Williams": {
        "full_name": "Williams Racing",
        "founded": 1977,
        "headquarters": "Grove, United Kingdom",
        "team_principal": "James Vowles",
        "power_unit": "Mercedes",
        "team_color": "#64C4FF",
        "logo_url": "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos/williams",
        "history": "Founded by Sir Frank Williams, the team won 9 Constructors' Championships in the 1980s and 1990s. Drivers like Nigel Mansell, Alain Prost, and Damon Hill achieved legendary status with the team.",
        "name_variants": ["Williams", "Williams Racing"]
    },
    "Haas": {
        "full_name": "MoneyGram Haas F1 Team",
        "founded": 2016,
        "headquarters": "Kannapolis, USA",
        "team_principal": "Ayao Komatsu",
        "power_unit": "Ferrari",
        "team_color": "#B6BABD",
        "logo_url": "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos/haas",
        "history": "America's first F1 team since 1986, founded by NASCAR team owner Gene Haas. Partnered closely with Ferrari for technical support and has been developing steadily since their debut.",
        "name_variants": ["Haas", "Haas F1 Team", "MoneyGram Haas"]
    },
    "Kick Sauber": {
        "full_name": "Stake F1 Team Kick Sauber",
        "founded": 1993,
        "headquarters": "Hinwil, Switzerland",
        "team_principal": "Alessandro Alunni Bravi",
        "power_unit": "Ferrari",
        "team_color": "#52E252",
        "logo_url": "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos/kick%20sauber",
        "history": "Originally Sauber Motorsport, the Swiss team has a long F1 history. Operated as BMW Sauber (2006-2009) and Alfa Romeo (2019-2023). Set to become Audi's works team from 2026.",
        "name_variants": ["Sauber", "Kick Sauber", "Alfa Romeo"]
    },
    "Racing Bulls": {
        "full_name": "Visa Cash App RB F1 Team",
        "founded": 2006,
        "headquarters": "Faenza, Italy",
        "team_principal": "Alan Permane",
        "power_unit": "Ford-RBPT",
        "team_color": "#6692FF",
        "logo_url": "https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_1320/content/dam/fom-website/2018-redesign-assets/team%20logos/rb",
        "history": "Red Bull's junior team, originally Scuderia Toro Rosso (2006-2019), then AlphaTauri (2020-2023), now Racing Bulls. Has been a proving ground for future champions including Sebastian Vettel and Max Verstappen.",
        "name_variants": ["Racing Bulls", "RB", "AlphaTauri", "Toro Rosso", "Visa Cash App RB"]
    },
    "Cadillac": {
        "full_name": "Cadillac Formula 1 Team",
        "founded": 2026,
        "headquarters": "Fishers, Indiana, USA",
        "team_principal": "Graeme Lowdon",
        "power_unit": "Ferrari",
        "team_color": "#C4A747",
        "logo_url": "/images/teams/cadillac.svg",
        "history": "General Motors' entry into F1 under the Cadillac brand, joining the grid in 2026 as the 11th team. First new independent constructor since Haas in 2016. Using Ferrari power units until GM develops their own engines for 2029. Headquartered in Fishers, Indiana with facilities in Concord NC, Warren MI, and Silverstone UK.",
        "name_variants": ["Cadillac", "GM", "General Motors", "TWG Cadillac"]
    },
    "Audi": {
        "full_name": "Audi Revolut F1 Team",
        "founded": 2026,
        "headquarters": "Hinwil, Switzerland",
        "team_principal": "Jonathan Wheatley",
        "power_unit": "Audi",
        "team_color": "#990000",
        "logo_url": "/images/teams/audi.svg",
        "history": "VW Group's return to F1 through Audi, formed through the acquisition of Sauber Motorsport. Jonathan Wheatley serves as team principal with Mattia Binotto as head of the Audi F1 project. Operates from Hinwil (Switzerland), Neuburg (Germany), and Bicester (UK). Revolut is the title sponsor.",
        "name_variants": ["Audi", "Audi F1 Team", "Audi Revolut"]
    },
}


@router.get("/constructors/{constructor_id}/profile")
async def get_constructor_profile(
    constructor_id: str,
    db: Session = Depends(get_db)
):
    """
    Comprehensive constructor profile with team history, stats, 
    current drivers, and season-by-season performance.
    """
    from sqlalchemy import case, desc, asc
    
    # Constructor lineage — maps current teams to their predecessor constructor_ids
    # so season history includes the full team history across rebrandings.
    CONSTRUCTOR_LINEAGE: dict[str, list[str]] = {
        "racing_bulls": ["rb", "alphatauri", "toro_rosso"],
        "rb": ["alphatauri", "toro_rosso"],
        "alpine": ["renault"],
        "aston_martin": ["racing_point", "force_india"],
        "kick_sauber": ["alfa_romeo_racing", "alfa_romeo", "sauber"],
        "red_bull_racing": ["red_bull"],
    }
    
    # Get constructor - support both ID number and name-based lookup
    constructor = None
    
    # Try by ID first
    if constructor_id.isdigit():
        constructor = db.query(Constructor).filter(Constructor.constructor_id == int(constructor_id)).first()
    
    # Try by constructor_key or name
    if not constructor:
        # Normalize the input for matching
        normalized_id = constructor_id.lower().replace('-', ' ').replace('_', ' ')
        
        constructors = db.query(Constructor).all()
        for c in constructors:
            if c.constructor_key and c.constructor_key.lower() == normalized_id:
                constructor = c
                break
            if c.constructor_name and c.constructor_name.lower() == normalized_id:
                constructor = c
                break
            # Partial match
            if c.constructor_name and normalized_id in c.constructor_name.lower():
                constructor = c
                break
    
    if not constructor:
        raise HTTPException(status_code=404, detail="Constructor not found")
    
    team_name = constructor.constructor_name
    
    # Get team metadata
    meta = {}
    for key, data in TEAM_METADATA.items():
        if key.lower() in team_name.lower() or team_name.lower() in key.lower():
            meta = data
            break
    
    # Build list of all constructor IDs for this team's lineage (including predecessors)
    lineage_keys = CONSTRUCTOR_LINEAGE.get(constructor.constructor_key or "", [])
    lineage_ids = [constructor.constructor_id]
    if lineage_keys:
        pred_constructors = db.query(Constructor).filter(
            Constructor.constructor_key.in_(lineage_keys)
        ).all()
        lineage_ids.extend([c.constructor_id for c in pred_constructors])
    
    # For teams founded recently (e.g. 2026) with NO lineage, only show stats from debut season.
    # Teams with lineage (like Racing Bulls inheriting Toro Rosso) use the full lineage IDs instead.
    founded_year = meta.get('founded') or constructor.founded_year or 1950
    has_lineage = len(lineage_ids) > 1
    
    # Which IDs to query: lineage for established teams, just self for brand-new teams
    stat_constructor_ids = lineage_ids if has_lineage else [constructor.constructor_id]
    
    # ── Career Statistics ──
    career_query = db.query(
        func.count(DriverSession.driver_session_id).label('total_races'),
        func.sum(DriverSession.points).label('total_points'),
        func.sum(case((DriverSession.position == 1, 1), else_=0)).label('wins'),
        func.sum(case((DriverSession.position.in_([1, 2, 3]), 1), else_=0)).label('podiums'),
        func.sum(case((DriverSession.grid == 1, 1), else_=0)).label('poles'),
        func.count(func.distinct(Event.season)).label('seasons'),
    ).select_from(DriverSession).join(
        Driver, DriverSession.driver_id == Driver.driver_id
    ).join(
        DBSession, DriverSession.session_id == DBSession.session_id
    ).join(
        Event, DBSession.event_id == Event.event_id
    ).filter(
        Driver.constructor_id.in_(stat_constructor_ids),
        DBSession.session_type == 'R',
    )
    # For brand-new teams (no lineage), restrict to founded year onward
    if not has_lineage and founded_year >= 2025:
        career_query = career_query.filter(Event.season >= founded_year)
    career_stats = career_query.first()
    
    # ── Season by Season Stats ──
    season_stats = []
    season_query = db.query(
        Event.season,
        func.sum(DriverSession.points).label('points'),
        func.sum(case((DriverSession.position == 1, 1), else_=0)).label('wins'),
        func.sum(case((DriverSession.position.in_([1, 2, 3]), 1), else_=0)).label('podiums'),
        func.sum(case((DriverSession.grid == 1, 1), else_=0)).label('poles'),
        func.count(func.distinct(Event.event_id)).label('races'),
    ).select_from(DriverSession).join(
        Driver, DriverSession.driver_id == Driver.driver_id
    ).join(
        DBSession, DriverSession.session_id == DBSession.session_id
    ).join(
        Event, DBSession.event_id == Event.event_id
    ).filter(
        Driver.constructor_id.in_(stat_constructor_ids),
        DBSession.session_type == 'R',
    )
    if not has_lineage and founded_year >= 2025:
        season_query = season_query.filter(Event.season >= founded_year)
    seasons_data = season_query.group_by(Event.season).order_by(desc(Event.season)).all()
    
    for row in seasons_data:
        season_stats.append({
            'season': row.season,
            'points': float(row.points or 0),
            'wins': row.wins or 0,
            'podiums': row.podiums or 0,
            'poles': row.poles or 0,
            'races': row.races or 0,
        })
    
    # ── Current Drivers (2026 or latest from season mapping) ──
    current_drivers = []
    season_drivers_2026 = get_season_drivers(2026)
    season_drivers_2025 = get_season_drivers(2025)
    
    # Match team names from season mapping to this constructor
    def team_matches(season_team_name: str) -> bool:
        """Check if the season team name matches this constructor"""
        st = season_team_name.lower()
        tn = team_name.lower()
        # Check name variants from metadata
        variants = meta.get('name_variants', [])
        for v in variants:
            if v.lower() in st or st in v.lower():
                return True
        return tn in st or st in tn
    
    # Find current drivers from 2026 season mapping
    current_driver_codes = [
        code for code, (season_team, _) in season_drivers_2026.items()
        if team_matches(season_team)
    ]
    
    for driver_code in current_driver_codes:
        d = db.query(Driver).filter(Driver.driver_code == driver_code).first()
        if not d:
            # Use metadata fallback
            driver_meta = DRIVER_PROFILE_META.get(driver_code, {})
            if driver_meta:
                current_drivers.append({
                    'driver_id': None,
                    'driver_code': driver_code,
                    'first_name': str(driver_meta.get('first_name', '')),
                    'last_name': str(driver_meta.get('last_name', '')),
                    'full_name': f"{driver_meta.get('first_name', '')} {driver_meta.get('last_name', '')}",
                    'nationality': str(driver_meta.get('nationality', '')),
                    'driver_number': driver_meta.get('driver_number'),
                    'points': 0,
                    'wins': 0,
                    'podiums': 0,
                })
            continue
        
        # Get driver stats (career stats)
        driver_stats = db.query(
            func.sum(DriverSession.points).label('points'),
            func.sum(case((DriverSession.position == 1, 1), else_=0)).label('wins'),
            func.sum(case((DriverSession.position.in_([1, 2, 3]), 1), else_=0)).label('podiums'),
        ).select_from(DriverSession).join(
            DBSession, DriverSession.session_id == DBSession.session_id
        ).filter(
            DriverSession.driver_id == d.driver_id,
            DBSession.session_type == 'R'
        ).first()
        
        current_drivers.append({
            'driver_id': d.driver_id,
            'driver_code': d.driver_code,
            'first_name': d.first_name,
            'last_name': d.last_name,
            'full_name': f"{d.first_name} {d.last_name}",
            'nationality': d.nationality,
            'driver_number': d.driver_number,
            'points': float(driver_stats.points or 0) if driver_stats else 0,
            'wins': driver_stats.wins if driver_stats else 0,
            'podiums': driver_stats.podiums if driver_stats else 0,
        })
    
    # Sort drivers by points
    current_drivers.sort(key=lambda x: x['points'], reverse=True)
    current_driver_codes_set = set(current_driver_codes)
    
    # ── Notable Drivers (historical - all drivers who drove for this team's lineage) ──
    # Scan all seasons to find drivers who drove for this team
    from team_mapping import SEASON_TEAMS
    historical_driver_codes = set()
    for season, drivers_map in SEASON_TEAMS.items():
        for code, (season_team, _) in drivers_map.items():
            if team_matches(season_team):
                historical_driver_codes.add(code)
    
    # Exclude current drivers — they already appear in the current_drivers section
    historical_driver_codes -= current_driver_codes_set
    
    notable_drivers = []
    for code in historical_driver_codes:
        d = db.query(Driver).filter(Driver.driver_code == code).first()
        if not d:
            continue
        
        # Get career stats for this driver
        driver_meta = DRIVER_PROFILE_META.get(code, {})
        debut_year = driver_meta.get('debut_year')
        
        stats_query = db.query(
            func.sum(DriverSession.points).label('points'),
            func.sum(case((DriverSession.position == 1, 1), else_=0)).label('wins'),
        ).select_from(DriverSession).join(
            DBSession, DriverSession.session_id == DBSession.session_id
        ).join(
            Event, DBSession.event_id == Event.event_id
        ).filter(
            DriverSession.driver_id == d.driver_id,
            DBSession.session_type == 'R'
        )
        
        # Filter by debut year if available
        if debut_year:
            stats_query = stats_query.filter(Event.season >= debut_year)
        
        stats = stats_query.first()
        
        # Get proper name (handle code reuse)
        first_name = d.first_name
        last_name = d.last_name
        if driver_meta:
            first_name = str(driver_meta.get('first_name', first_name))
            last_name = str(driver_meta.get('last_name', last_name))
        
        notable_drivers.append({
            'driver_code': code,
            'name': f"{first_name} {last_name}",
            'points': float(stats.points or 0) if stats else 0,
            'wins': stats.wins if stats else 0,
        })
    
    # Sort by points and take top 10
    notable_drivers.sort(key=lambda x: x['points'], reverse=True)
    notable_drivers = notable_drivers[:10]
    
    # Team colors from DB or metadata
    team_color = meta.get('team_color') or constructor.team_color or "#888888"
    
    # Logo URL from metadata or DB
    logo_url = meta.get('logo_url') or constructor.logo_url
    
    return {
        'constructor_id': constructor.constructor_id,
        'constructor_key': constructor.constructor_key,
        'constructor_name': team_name,
        'full_name': meta.get('full_name', team_name),
        'team_color': team_color,
        'nationality': constructor.nationality,
        'founded': meta.get('founded') or constructor.founded_year,
        'headquarters': meta.get('headquarters') or constructor.headquarters,
        'team_principal': meta.get('team_principal'),
        'power_unit': meta.get('power_unit'),
        'history': meta.get('history') or constructor.description,
        'logo_url': logo_url,
        'career_stats': {
            'total_races': career_stats.total_races if career_stats else 0,
            'total_points': float(career_stats.total_points or 0) if career_stats else 0,
            'wins': (career_stats.wins or 0) if career_stats else 0,
            'podiums': (career_stats.podiums or 0) if career_stats else 0,
            'poles': (career_stats.poles or 0) if career_stats else 0,
            'seasons': career_stats.seasons if career_stats else 0,
        },
        'season_history': season_stats,
        'current_drivers': current_drivers,
        'notable_drivers': notable_drivers,
    }


@router.get("/drivers/{driver_code}/stats/{season}")
async def get_driver_season_stats(
    driver_code: str,
    season: int,
    db: Session = Depends(get_db)
):
    """Get driver statistics for a specific season"""
    
    driver = db.query(Driver).filter(
        Driver.driver_code == driver_code.upper()
    ).first()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Get season stats  (SQLAlchemy 2.x case() syntax)
    from sqlalchemy import case
    stats = db.query(
        func.count(DriverSession.driver_session_id).label('races'),
        func.sum(DriverSession.points).label('points'),
        func.sum(
            case((DriverSession.position == 1, 1), else_=0)
        ).label('wins'),
        func.sum(
            case((DriverSession.position.in_([1, 2, 3]), 1), else_=0)
        ).label('podiums'),
        func.avg(DriverSession.grid).label('avg_grid'),
        func.avg(DriverSession.position).label('avg_finish')
    ).join(
        DBSession
    ).join(
        Event
    ).filter(
        DriverSession.driver_id == driver.driver_id,
        Event.season == season
    ).first()
    
    return {
        'driver_code': driver_code,
        'driver_name': f"{driver.first_name} {driver.last_name}",
        'season': season,
        'races': stats.races or 0,
        'points': float(stats.points or 0),
        'wins': stats.wins or 0,
        'podiums': stats.podiums or 0,
        'avg_grid_position': float(stats.avg_grid or 0),
        'avg_finish_position': float(stats.avg_finish or 0)
    }


@router.get("/drivers/{driver_code}/profile")
async def get_driver_profile(
    driver_code: str,
    db: Session = Depends(get_db)
):
    """
    Comprehensive driver profile with career stats, season history, 
    recent results, and ELO rating.
    """
    from sqlalchemy import case, desc
    
    driver_code = driver_code.upper()
    
    # Get driver from DB or fallback to profile meta
    driver = db.query(Driver).filter(Driver.driver_code == driver_code).first()
    meta = DRIVER_PROFILE_META.get(driver_code, {})
    
    if not driver and not meta:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Basic driver info
    first_name = driver.first_name if driver else str(meta.get("first_name", ""))
    last_name = driver.last_name if driver else str(meta.get("last_name", ""))
    nationality = driver.nationality if driver else str(meta.get("nationality", ""))
    driver_number = driver.driver_number if driver else meta.get("driver_number")
    photo_url = driver.photo_url if driver and driver.photo_url else _formula1_photo_url(driver_code)
    biography = driver.biography if driver else None
    
    # Get current team (for 2026 or latest season)
    current_team_info = get_team_for_driver(driver_code, 2026)
    if not current_team_info:
        current_team_info = get_team_for_driver(driver_code, 2025)
    team_name = current_team_info[0] if current_team_info else (driver.team_name if driver else None)
    team_color = current_team_info[1] if current_team_info else (driver.team_color if driver else "#333333")
    
    # Get debut year from meta to filter out data from code-collision drivers
    debut_year = meta.get('debut_year')
    
    # ── Career Statistics ──
    career_stats = None
    if driver:
        career_query = db.query(
            func.count(DriverSession.driver_session_id).label('total_races'),
            func.sum(DriverSession.points).label('total_points'),
            func.sum(case((DriverSession.position == 1, 1), else_=0)).label('wins'),
            func.sum(case((DriverSession.position.in_([1, 2, 3]), 1), else_=0)).label('podiums'),
            func.sum(case((DriverSession.grid == 1, 1), else_=0)).label('poles'),
            func.sum(case((DriverSession.dnf == True, 1), else_=0)).label('dnfs'),
            func.min(DriverSession.position).label('best_finish'),
            func.avg(DriverSession.position).label('avg_finish'),
            func.avg(DriverSession.grid).label('avg_grid'),
        ).select_from(DriverSession).join(
            DBSession, DriverSession.session_id == DBSession.session_id
        ).join(
            Event, DBSession.event_id == Event.event_id
        ).filter(
            DriverSession.driver_id == driver.driver_id,
            DBSession.session_type == 'R'  # Only count race sessions
        )
        # Filter by debut year to exclude data from different drivers with same code
        if debut_year:
            career_query = career_query.filter(Event.season >= debut_year)
        career_stats = career_query.first()
    
    # Count fastest laps (check if driver had the fastest lap in a race)
    fastest_laps = 0
    if driver:
        fl_query = db.query(func.count()).select_from(DriverSession).join(
            DBSession, DriverSession.session_id == DBSession.session_id
        ).join(
            Event, DBSession.event_id == Event.event_id
        ).filter(
            DriverSession.driver_id == driver.driver_id,
            DBSession.session_type == 'R',
            DriverSession.fastest_lap.isnot(None)
        )
        if debut_year:
            fl_query = fl_query.filter(Event.season >= debut_year)
        fastest_laps = fl_query.scalar() or 0
    
    # ── Season by Season Stats ──
    season_stats = []
    if driver:
        seasons_query = db.query(
            Event.season,
            func.count(DriverSession.driver_session_id).label('races'),
            func.sum(DriverSession.points).label('points'),
            func.sum(case((DriverSession.position == 1, 1), else_=0)).label('wins'),
            func.sum(case((DriverSession.position.in_([1, 2, 3]), 1), else_=0)).label('podiums'),
            func.min(DriverSession.position).label('best_finish'),
            func.avg(DriverSession.position).label('avg_finish'),
        ).select_from(DriverSession).join(
            DBSession, DriverSession.session_id == DBSession.session_id
        ).join(
            Event, DBSession.event_id == Event.event_id
        ).filter(
            DriverSession.driver_id == driver.driver_id,
            DBSession.session_type == 'R'
        )
        if debut_year:
            seasons_query = seasons_query.filter(Event.season >= debut_year)
        seasons_data = seasons_query.group_by(Event.season).order_by(desc(Event.season)).all()
        
        for row in seasons_data:
            # Get team for that season
            season_team = get_team_for_driver(driver_code, row.season)
            season_stats.append({
                'season': row.season,
                'team': season_team[0] if season_team else None,
                'team_color': season_team[1] if season_team else "#333333",
                'races': row.races or 0,
                'points': float(row.points or 0),
                'wins': row.wins or 0,
                'podiums': row.podiums or 0,
                'best_finish': row.best_finish,
                'avg_finish': round(float(row.avg_finish), 1) if row.avg_finish else None,
                'position': None,  # Championship position - calculate separately
            })
    
    # ── Recent Race Results (last 10 races) ──
    recent_results = []
    if driver:
        recent_query = db.query(
            Event.event_name,
            Event.season,
            Event.round,
            Event.country,
            DriverSession.position,
            DriverSession.grid,
            DriverSession.points,
            DriverSession.status,
            DriverSession.dnf,
        ).join(DBSession, DriverSession.session_id == DBSession.session_id).join(
            Event, DBSession.event_id == Event.event_id
        ).filter(
            DriverSession.driver_id == driver.driver_id,
            DBSession.session_type == 'R'
        )
        if debut_year:
            recent_query = recent_query.filter(Event.season >= debut_year)
        recent = recent_query.order_by(desc(Event.season), desc(Event.round)).limit(10).all()
        
        for r in recent:
            positions_gained = (r.grid - r.position) if r.grid and r.position else 0
            recent_results.append({
                'event_name': r.event_name,
                'season': r.season,
                'round': r.round,
                'country': r.country,
                'position': r.position,
                'grid': r.grid,
                'points': float(r.points or 0),
                'status': r.status,
                'dnf': r.dnf or False,
                'positions_gained': positions_gained,
            })
    
    # ── ELO Rating ──
    elo_data = None
    try:
        from services.elo_rating import get_elo_system
        elo = get_elo_system(db)
        driver_elo = elo.get_driver_elo(driver_code)
        if driver_elo:
            elo_data = {
                'rating': round(driver_elo.rating, 1),
                'peak_rating': round(driver_elo.peak_rating, 1),
                'tier': driver_elo.tier,
                'races_completed': driver_elo.races_completed,
            }
    except Exception:
        pass
    
    # ── Head-to-Head vs Teammate ──
    teammate_comparison = None
    # Find current teammate
    if driver and team_name:
        season_drivers = get_season_drivers(2026) or get_season_drivers(2025) or {}
        teammates = [code for code, info in season_drivers.items() 
                     if info[0] == team_name and code != driver_code]
        if teammates:
            teammate_code = teammates[0]
            # Compare recent results
            teammate_driver = db.query(Driver).filter(Driver.driver_code == teammate_code).first()
            if teammate_driver:
                # Get last 10 races where both competed
                my_results = {(r.season, r.round): r.position for r in recent}
                
                teammate_recent = db.query(
                    Event.season, Event.round, DriverSession.position
                ).join(DBSession, DriverSession.session_id == DBSession.session_id).join(
                    Event, DBSession.event_id == Event.event_id
                ).filter(
                    DriverSession.driver_id == teammate_driver.driver_id,
                    DBSession.session_type == 'R'
                ).order_by(desc(Event.season), desc(Event.round)).limit(20).all()
                
                tm_results = {(r.season, r.round): r.position for r in teammate_recent}
                
                common_races = set(my_results.keys()) & set(tm_results.keys())
                wins_h2h = sum(1 for key in common_races if my_results.get(key) and tm_results.get(key) and my_results[key] < tm_results[key])
                losses_h2h = sum(1 for key in common_races if my_results.get(key) and tm_results.get(key) and my_results[key] > tm_results[key])
                
                teammate_comparison = {
                    'teammate_code': teammate_code,
                    'teammate_name': f"{teammate_driver.first_name} {teammate_driver.last_name}",
                    'races_compared': len(common_races),
                    'wins': wins_h2h,
                    'losses': losses_h2h,
                }
    
    return {
        'driver_code': driver_code,
        'driver_number': driver_number,
        'first_name': first_name,
        'last_name': last_name,
        'full_name': f"{first_name} {last_name}",
        'nationality': nationality,
        'team_name': team_name,
        'team_color': team_color,
        'photo_url': photo_url,
        'biography': biography,
        'career_stats': {
            'total_races': career_stats.total_races if career_stats else 0,
            'total_points': float(career_stats.total_points or 0) if career_stats else 0,
            'wins': career_stats.wins if career_stats else 0,
            'podiums': career_stats.podiums if career_stats else 0,
            'poles': career_stats.poles if career_stats else 0,
            'fastest_laps': fastest_laps,
            'dnfs': career_stats.dnfs if career_stats else 0,
            'best_finish': career_stats.best_finish if career_stats else None,
            'avg_finish': round(float(career_stats.avg_finish), 2) if career_stats and career_stats.avg_finish else None,
            'avg_grid': round(float(career_stats.avg_grid), 2) if career_stats and career_stats.avg_grid else None,
            'win_rate': round((career_stats.wins / career_stats.total_races) * 100, 1) if career_stats and career_stats.total_races else 0,
            'podium_rate': round((career_stats.podiums / career_stats.total_races) * 100, 1) if career_stats and career_stats.total_races else 0,
        },
        'season_history': season_stats,
        'recent_results': recent_results,
        'elo': elo_data,
        'teammate_comparison': teammate_comparison,
    }
