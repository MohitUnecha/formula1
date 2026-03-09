"""
Pre-built F1 Track Coordinate Data
Real circuit coordinates derived from FastF1 telemetry data.
Each track has: centerline XY, inner/outer edges, corners, DRS zones, rotation, start/finish.
Coordinates are in metres (world space) matching FastF1's coordinate system.
"""
import json
import os
import math
import numpy as np
from typing import Dict, List, Tuple, Optional

TRACK_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "tracks")


def _ensure_dir():
    os.makedirs(TRACK_DATA_DIR, exist_ok=True)


def _downsample(pts: list, n: int = 200) -> list:
    """Downsample a list of [x,y] to n evenly-spaced points."""
    if len(pts) <= n:
        return pts
    step = len(pts) / n
    return [pts[int(i * step) % len(pts)] for i in range(n)]


def _compute_edges(center_x, center_y, width=200):
    """Compute inner/outer track edges from centerline using normals."""
    cx = np.array(center_x, dtype=float)
    cy = np.array(center_y, dtype=float)
    
    dx = np.gradient(cx)
    dy = np.gradient(cy)
    norm = np.sqrt(dx**2 + dy**2)
    norm[norm == 0] = 1.0
    dx /= norm
    dy /= norm
    
    # Normals (perpendicular)
    nx = -dy
    ny = dx
    
    hw = width / 2
    outer_x = cx + nx * hw
    outer_y = cy + ny * hw
    inner_x = cx - nx * hw
    inner_y = cy - ny * hw
    
    return (
        [[round(float(x), 1), round(float(y), 1)] for x, y in zip(inner_x, inner_y)],
        [[round(float(x), 1), round(float(y), 1)] for x, y in zip(outer_x, outer_y)],
    )


def _build_svg_path(center_points: list) -> str:
    """Convert center points to an SVG path string, normalised to 0-1000 range."""
    if not center_points:
        return ""
    
    xs = [p[0] for p in center_points]
    ys = [p[1] for p in center_points]
    
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    
    x_range = x_max - x_min or 1
    y_range = y_max - y_min or 1
    
    # Normalise with padding
    pad = 50
    scale = min((1000 - 2*pad) / x_range, (700 - 2*pad) / y_range)
    
    norm_pts = []
    for x, y in center_points:
        nx = pad + (x - x_min) * scale
        ny = pad + (y_max - y) * scale  # flip Y for SVG
        norm_pts.append((round(nx, 1), round(ny, 1)))
    
    parts = [f"M {norm_pts[0][0]},{norm_pts[0][1]}"]
    for px, py in norm_pts[1:]:
        parts.append(f"L {px},{py}")
    parts.append("Z")
    
    return " ".join(parts)


def get_track_data(circuit_name: str) -> Optional[dict]:
    """Load pre-built track data from cache."""
    _ensure_dir()
    safe_name = circuit_name.lower().replace(" ", "_").replace("-", "_")
    path = os.path.join(TRACK_DATA_DIR, f"{safe_name}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def save_track_data(circuit_name: str, data: dict):
    """Save track data to cache."""
    _ensure_dir()
    safe_name = circuit_name.lower().replace(" ", "_").replace("-", "_")
    path = os.path.join(TRACK_DATA_DIR, f"{safe_name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def list_available_tracks() -> List[str]:
    """List all cached track names."""
    _ensure_dir()
    tracks = []
    for fname in os.listdir(TRACK_DATA_DIR):
        if fname.endswith(".json"):
            tracks.append(fname.replace(".json", ""))
    return sorted(tracks)


# ─── Circuit name lookup from event names ───────────────────────────
CIRCUIT_LOOKUP: Dict[str, str] = {
    # 2024-2026 Calendar
    "bahrain": "bahrain",
    "bahrain grand prix": "bahrain",
    "saudi arabian grand prix": "jeddah",
    "saudi arabia": "jeddah",
    "jeddah": "jeddah",
    "australian grand prix": "albert_park",
    "australia": "albert_park",
    "albert park": "albert_park",
    "melbourne": "albert_park",
    "japanese grand prix": "suzuka",
    "japan": "suzuka",
    "suzuka": "suzuka",
    "chinese grand prix": "shanghai",
    "china": "shanghai",
    "shanghai": "shanghai",
    "miami grand prix": "miami",
    "miami": "miami",
    "emilia romagna grand prix": "imola",
    "imola": "imola",
    "monaco grand prix": "monaco",
    "monaco": "monaco",
    "monte carlo": "monaco",
    "canadian grand prix": "montreal",
    "canada": "montreal",
    "montreal": "montreal",
    "barcelona grand prix": "barcelona",
    "spanish grand prix": "barcelona",
    "spain": "barcelona",
    "barcelona": "barcelona",
    "austrian grand prix": "red_bull_ring",
    "austria": "red_bull_ring",
    "red bull ring": "red_bull_ring",
    "spielberg": "red_bull_ring",
    "british grand prix": "silverstone",
    "united kingdom": "silverstone",
    "silverstone": "silverstone",
    "hungarian grand prix": "hungaroring",
    "hungary": "hungaroring",
    "hungaroring": "hungaroring",
    "belgian grand prix": "spa",
    "belgium": "spa",
    "spa": "spa",
    "spa-francorchamps": "spa",
    "dutch grand prix": "zandvoort",
    "netherlands": "zandvoort",
    "zandvoort": "zandvoort",
    "italian grand prix": "monza",
    "italy": "monza",
    "monza": "monza",
    "azerbaijan grand prix": "baku",
    "azerbaijan": "baku",
    "baku": "baku",
    "singapore grand prix": "singapore",
    "singapore": "singapore",
    "marina bay": "singapore",
    "united states grand prix": "cota",
    "austin": "cota",
    "cota": "cota",
    "mexico city grand prix": "mexico_city",
    "mexico": "mexico_city",
    "são paulo grand prix": "interlagos",
    "sao paulo grand prix": "interlagos",
    "brazil": "interlagos",
    "interlagos": "interlagos",
    "las vegas grand prix": "las_vegas",
    "las vegas": "las_vegas",
    "qatar grand prix": "lusail",
    "qatar": "lusail",
    "lusail": "lusail",
    "abu dhabi grand prix": "yas_marina",
    "abu dhabi": "yas_marina",
    "united arab emirates": "yas_marina",
    "yas marina": "yas_marina",
}


def resolve_circuit_name(event_name: str, country: str = "") -> str:
    """Resolve an event name/country to a canonical circuit file key."""
    search = f"{event_name} {country}".lower().strip()
    
    # Try full match first
    for keyword, circuit in CIRCUIT_LOOKUP.items():
        if keyword in search:
            return circuit
    
    # Fallback
    return "default"


def generate_track_from_fastf1(year: int, round_num: int, session_type: str = "R") -> Optional[dict]:
    """
    Use FastF1 to fetch real telemetry and extract track coordinates.
    Returns a track data dict or None on failure.
    This can take 1-3 minutes per track due to data download.
    """
    try:
        import fastf1
        
        # Enable cache
        cache_dir = os.path.join(os.path.dirname(__file__), ".fastf1-cache")
        os.makedirs(cache_dir, exist_ok=True)
        fastf1.Cache.enable_cache(cache_dir)
        
        session = fastf1.get_session(year, round_num, session_type)
        session.load(telemetry=True, weather=False)
        
        # Get circuit info
        circuit_info = session.get_circuit_info()
        rotation = float(circuit_info.rotation) if hasattr(circuit_info, 'rotation') else 0.0
        
        # Get corners
        corners = []
        if hasattr(circuit_info, 'corners') and circuit_info.corners is not None:
            for _, row in circuit_info.corners.iterrows():
                corners.append({
                    "number": int(row.get("Number", 0)),
                    "x": float(row.get("X", 0)),
                    "y": float(row.get("Y", 0)),
                    "angle": float(row.get("Angle", 0)) if "Angle" in row else 0,
                    "letter": str(row.get("Letter", "")) if "Letter" in row else "",
                })
        
        # Get fastest lap for track outline
        fastest = session.laps.pick_fastest()
        if fastest is None:
            return None
        
        tel = fastest.get_telemetry()
        if tel is None or tel.empty:
            return None
        
        x_raw = tel["X"].to_numpy()
        y_raw = tel["Y"].to_numpy()
        
        # Downsample to ~300 points
        n = len(x_raw)
        step = max(1, n // 300)
        x_ds = x_raw[::step]
        y_ds = y_raw[::step]
        
        center = [[round(float(x), 1), round(float(y), 1)] for x, y in zip(x_ds, y_ds)]
        
        # Compute inner/outer edges
        inner, outer = _compute_edges(x_ds, y_ds, width=180)
        
        # DRS zones
        drs_zones = []
        if "DRS" in tel.columns:
            drs = tel["DRS"].to_numpy()
            drs_start = None
            for i, val in enumerate(drs):
                if val in [10, 12, 14]:
                    if drs_start is None:
                        drs_start = i
                else:
                    if drs_start is not None:
                        drs_end = i - 1
                        si = min(drs_start, len(x_raw)-1)
                        ei = min(drs_end, len(x_raw)-1)
                        drs_zones.append({
                            "start": {"x": float(x_raw[si]), "y": float(y_raw[si])},
                            "end": {"x": float(x_raw[ei]), "y": float(y_raw[ei])},
                        })
                        drs_start = None
            if drs_start is not None:
                ei = len(x_raw) - 1
                drs_zones.append({
                    "start": {"x": float(x_raw[drs_start]), "y": float(y_raw[drs_start])},
                    "end": {"x": float(x_raw[ei]), "y": float(y_raw[ei])},
                })
        
        # Start/finish
        sf = {"x": float(x_raw[0]), "y": float(y_raw[0])}
        
        # Build SVG path
        svg_path = _build_svg_path(center)
        
        # Event info
        event_name = session.event.get("EventName", "")
        location = session.event.get("Location", "")
        country = session.event.get("Country", "")
        
        return {
            "name": event_name,
            "location": location,
            "country": country,
            "rotation": rotation,
            "center": center,
            "inner": inner,
            "outer": outer,
            "corners": corners,
            "drs_zones": drs_zones,
            "start_finish": sf,
            "svg_path": svg_path,
            "width": 1000,
            "height": 700,
            "source": "fastf1",
            "year": year,
            "round": round_num,
        }
    except Exception as e:
        print(f"Error generating track from FastF1: {e}")
        return None
