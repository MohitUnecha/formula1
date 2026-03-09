"""SQLAlchemy ORM models"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, Text,
    ForeignKey, UniqueConstraint, Index, DECIMAL
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Event(Base):
    """Grand Prix events"""
    __tablename__ = "events"
    
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False, index=True)
    round = Column(Integer, nullable=False)
    event_name = Column(String(255), nullable=False)
    event_date = Column(Date, nullable=False)
    event_format = Column(String(50))  # 'conventional', 'sprint'
    country = Column(String(100))
    location = Column(String(255))
    circuit_key = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    sessions = relationship("Session", back_populates="event", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('season', 'round', name='uq_event_season_round'),
        Index('idx_events_season', 'season'),
    )


class Session(Base):
    """Race sessions (FP1, FP2, FP3, Q, Sprint, Race)"""
    __tablename__ = "sessions"
    
    session_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey('events.event_id'), nullable=False)
    session_type = Column(String(50), nullable=False)  # 'FP1', 'FP2', 'FP3', 'Q', 'R', 'S'
    session_date = Column(DateTime, nullable=False)
    total_laps = Column(Integer)
    track_length_km = Column(DECIMAL(10, 3))
    track_status = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="sessions")
    driver_sessions = relationship("DriverSession", back_populates="session", cascade="all, delete-orphan")
    weather = relationship("Weather", back_populates="session", cascade="all, delete-orphan")
    race_control = relationship("RaceControl", back_populates="session", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('event_id', 'session_type', name='uq_session_event_type'),
        Index('idx_sessions_event', 'event_id'),
    )


class Constructor(Base):
    """F1 Constructors/Teams"""
    __tablename__ = "constructors"
    
    constructor_id = Column(Integer, primary_key=True, autoincrement=True)
    constructor_key = Column(String(100), unique=True, nullable=False)
    constructor_name = Column(String(255), nullable=False)
    nationality = Column(String(100))
    team_color = Column(String(7))  # Hex color for team
    logo_url = Column(String(500))  # Team/constructor logo
    description = Column(Text)  # Team info/history
    founded_year = Column(Integer)
    headquarters = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    drivers = relationship("Driver", back_populates="constructor")


class Driver(Base):
    """F1 Drivers"""
    __tablename__ = "drivers"
    
    driver_id = Column(Integer, primary_key=True, autoincrement=True)
    driver_code = Column(String(3), unique=True, nullable=False)
    driver_number = Column(Integer)
    first_name = Column(String(100))
    last_name = Column(String(100))
    nationality = Column(String(100))
    constructor_id = Column(Integer, ForeignKey('constructors.constructor_id'), nullable=True)
    team_name = Column(String(100))
    team_color = Column(String(7))  # Hex color
    photo_url = Column(String(500))  # Driver photo URL
    biography = Column(Text)  # Driver biography/facts
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    constructor = relationship("Constructor", back_populates="drivers")
    driver_sessions = relationship("DriverSession", back_populates="driver")
    predictions = relationship("Prediction", back_populates="driver")


class DriverSession(Base):
    """Driver participation in a session"""
    __tablename__ = "driver_sessions"
    
    driver_session_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('sessions.session_id'), nullable=False)
    driver_id = Column(Integer, ForeignKey('drivers.driver_id'), nullable=False)
    position = Column(Integer)  # Final position
    grid = Column(Integer)  # Grid position
    points = Column(DECIMAL(5, 2))
    status = Column(String(255))  # 'Finished', 'DNF', etc.
    dnf = Column(Boolean, default=False)
    dnf_reason = Column(String(255))
    fastest_lap = Column(DECIMAL(10, 3))
    
    # Relationships
    session = relationship("Session", back_populates="driver_sessions")
    driver = relationship("Driver", back_populates="driver_sessions")
    laps = relationship("Lap", back_populates="driver_session", cascade="all, delete-orphan")
    pit_stops = relationship("PitStop", back_populates="driver_session", cascade="all, delete-orphan")
    feature_store = relationship("FeatureStore", back_populates="driver_session", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('session_id', 'driver_id', name='uq_driver_session'),
        Index('idx_driver_sessions_session', 'session_id'),
        Index('idx_driver_sessions_driver', 'driver_id'),
    )


class Lap(Base):
    """Lap-level data"""
    __tablename__ = "laps"
    
    lap_id = Column(Integer, primary_key=True, autoincrement=True)
    driver_session_id = Column(Integer, ForeignKey('driver_sessions.driver_session_id'), nullable=False)
    lap_number = Column(Integer, nullable=False)
    lap_time = Column(DECIMAL(10, 3))
    sector1_time = Column(DECIMAL(10, 3))
    sector2_time = Column(DECIMAL(10, 3))
    sector3_time = Column(DECIMAL(10, 3))
    position = Column(Integer)
    tyre_compound = Column(String(20))
    tyre_age = Column(Integer)
    is_personal_best = Column(Boolean)
    pit_out_lap = Column(Boolean, default=False)
    pit_in_lap = Column(Boolean, default=False)
    track_status = Column(String(50))
    is_accurate = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    driver_session = relationship("DriverSession", back_populates="laps")
    
    __table_args__ = (
        UniqueConstraint('driver_session_id', 'lap_number', name='uq_lap'),
        Index('idx_laps_driver_session', 'driver_session_id'),
        Index('idx_laps_lap_number', 'lap_number'),
    )


class PitStop(Base):
    """Pit stop events"""
    __tablename__ = "pit_stops"
    
    pit_stop_id = Column(Integer, primary_key=True, autoincrement=True)
    driver_session_id = Column(Integer, ForeignKey('driver_sessions.driver_session_id'), nullable=False)
    lap_number = Column(Integer, nullable=False)
    pit_duration = Column(DECIMAL(10, 3))
    tyre_compound_old = Column(String(20))
    tyre_compound_new = Column(String(20))
    # Seconds from session start
    time_of_day = Column(DECIMAL(10, 3))
    
    # Relationships
    driver_session = relationship("DriverSession", back_populates="pit_stops")
    
    __table_args__ = (
        Index('idx_pit_stops_driver_session', 'driver_session_id'),
    )


class Weather(Base):
    """Weather conditions"""
    __tablename__ = "weather"
    
    weather_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('sessions.session_id'), nullable=False)
    lap_number = Column(Integer)
    air_temp = Column(DECIMAL(5, 2))
    track_temp = Column(DECIMAL(5, 2))
    humidity = Column(Integer)
    pressure = Column(DECIMAL(6, 2))
    wind_speed = Column(DECIMAL(5, 2))
    wind_direction = Column(Integer)
    rainfall = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    session = relationship("Session", back_populates="weather")
    
    __table_args__ = (
        Index('idx_weather_session', 'session_id'),
    )


class RaceControl(Base):
    """Race control messages and team radio (caddy)"""
    __tablename__ = "race_control"
    
    message_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('sessions.session_id'), nullable=False)
    lap_number = Column(Integer)
    message_time = Column(DateTime)
    category = Column(String(50))  # 'rcm', 'radio', 'warning', etc.
    message = Column(Text)
    flag_type = Column(String(20))
    sector = Column(Integer)
    driver_code = Column(String(3))
    
    # 2026 real-time fields for caddy/team radio data
    driver_id = Column(Integer, ForeignKey('drivers.driver_id'), nullable=True)
    is_caddy = Column(Boolean, default=False)  # True if team radio/caddy message
    receiver = Column(String(100))  # Who received the message
    sentiment = Column(String(20))  # Neutral, critical, positive
    timestamp_utc = Column(DateTime)  # Precise UTC timestamp
    source_radio_frequency = Column(String(50))  # Radio frequency used
    
    # Relationships
    session = relationship("Session", back_populates="race_control")
    driver = relationship("Driver", primaryjoin="RaceControl.driver_id==Driver.driver_id", foreign_keys="RaceControl.driver_id")
    
    __table_args__ = (
        Index('idx_race_control_session', 'session_id'),
    )


class Prediction(Base):
    """ML predictions"""
    __tablename__ = "predictions"
    
    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('sessions.session_id'), nullable=False)
    driver_id = Column(Integer, ForeignKey('drivers.driver_id'), nullable=False)
    prediction_time = Column(DateTime, server_default=func.now())
    model_version = Column(String(50))
    
    # Probability predictions
    win_probability = Column(DECIMAL(5, 4))
    podium_probability = Column(DECIMAL(5, 4))
    top10_probability = Column(DECIMAL(5, 4))
    dnf_probability = Column(DECIMAL(5, 4))
    
    # Point predictions
    expected_position = Column(DECIMAL(5, 2))
    expected_pit_stops = Column(DECIMAL(3, 1))
    
    # Strategy predictions
    strategy_1_stop_prob = Column(DECIMAL(5, 4))
    strategy_2_stop_prob = Column(DECIMAL(5, 4))
    strategy_3_stop_prob = Column(DECIMAL(5, 4))
    
    # Confidence
    prediction_confidence = Column(DECIMAL(5, 4))
    
    # Relationships
    session = relationship("Session", back_populates="predictions")
    driver = relationship("Driver", back_populates="predictions")
    shap_explanations = relationship("ShapExplanation", back_populates="prediction", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('session_id', 'driver_id', 'model_version', 'prediction_time', 
                        name='uq_prediction'),
        Index('idx_predictions_session', 'session_id'),
    )


class FeatureStore(Base):
    """Feature store for ML"""
    __tablename__ = "feature_store"
    
    feature_id = Column(Integer, primary_key=True, autoincrement=True)
    driver_session_id = Column(Integer, ForeignKey('driver_sessions.driver_session_id'), nullable=False)
    feature_name = Column(String(100), nullable=False)
    feature_value = Column(DECIMAL(12, 6))
    feature_category = Column(String(50))
    calculation_time = Column(DateTime, server_default=func.now())
    
    # Relationships
    driver_session = relationship("DriverSession", back_populates="feature_store")
    
    __table_args__ = (
        Index('idx_feature_store_driver_session', 'driver_session_id'),
        Index('idx_feature_store_name', 'feature_name'),
    )


class ShapExplanation(Base):
    """SHAP explanations for predictions"""
    __tablename__ = "shap_explanations"
    
    shap_id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, ForeignKey('predictions.prediction_id'), nullable=False)
    feature_name = Column(String(100), nullable=False)
    shap_value = Column(DECIMAL(10, 6))
    feature_value = Column(DECIMAL(12, 6))
    rank = Column(Integer)
    
    # Relationships
    prediction = relationship("Prediction", back_populates="shap_explanations")
    
    __table_args__ = (
        Index('idx_shap_prediction', 'prediction_id'),
    )


class IngestLog(Base):
    """Track data ingestion history and status"""
    __tablename__ = "ingest_logs"

    id = Column(Integer, primary_key=True)
    
    # Timing
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Status
    status = Column(String(50), default="running")  # running, completed, failed, cancelled
    error_message = Column(Text, nullable=True)
    
    # Data counts
    seasons_ingested = Column(Integer, default=0)
    events_ingested = Column(Integer, default=0)
    sessions_ingested = Column(Integer, default=0)
    drivers_ingested = Column(Integer, default=0)
    
    # Source info
    source = Column(String(100), default="fastf1")  # fastf1, manual, etc.
    
    # Extra info (stored as JSON string)
    extra_info = Column(Text, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "error_message": self.error_message,
            "seasons_ingested": self.seasons_ingested,
            "events_ingested": self.events_ingested,
            "sessions_ingested": self.sessions_ingested,
            "drivers_ingested": self.drivers_ingested,
            "source": self.source,
            "extra_info": self.extra_info,
        }


class PredictionRateLimit(Base):
    """Rate limiting for prediction API calls to conserve AI credits"""
    __tablename__ = "prediction_rate_limits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_ip = Column(String(45), nullable=False, index=True)  # IPv6 max length
    request_time = Column(DateTime, server_default=func.now(), nullable=False)
    season = Column(Integer)
    round = Column(Integer)
    
    __table_args__ = (
        Index('idx_rate_limit_ip_time', 'client_ip', 'request_time'),
    )


class NewsCache(Base):
    """Cache for Tavily/web search results to reduce API calls"""
    __tablename__ = "news_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(500), nullable=False, index=True)
    source = Column(String(50), default="tavily")  # tavily, scraper, manual
    
    # Search results stored as JSON
    results_json = Column(Text)  # JSON array of search results
    summary = Column(Text)  # AI-generated summary if available
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)  # Cache expiry time
    hit_count = Column(Integer, default=0)  # How many times this cache was used
    
    __table_args__ = (
        Index('idx_news_cache_query', 'query'),
        Index('idx_news_cache_expires', 'expires_at'),
    )
