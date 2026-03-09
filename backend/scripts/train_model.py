#!/usr/bin/env python3
"""
F1 Race Prediction ML Pipeline

Trains a model to predict race outcomes based on historical data:
- Grid position, recent form, team strength
- Circuit-specific performance
- DNF probability

Uses sklearn RandomForest + GradientBoosting ensemble.
"""
import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, mean_absolute_error

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from models import (
    Event, Session, Driver, Constructor, DriverSession, Lap,
    Prediction, ShapExplanation
)

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_models")
os.makedirs(MODEL_DIR, exist_ok=True)


def build_feature_dataframe(db):
    """
    Build a feature-rich DataFrame from all race sessions.
    Features per driver per race:
      - grid: grid position
      - season, round_num
      - driver_id, constructor_id
      - avg_finish_last5: rolling avg finish in last 5 races
      - avg_grid_last5: rolling avg grid in last 5 races
      - win_rate_last10: win rate in last 10 races
      - podium_rate_last10: podium rate in last 10 races
      - dnf_rate_last10: DNF rate in last 10 races
      - team_avg_finish_last5: constructor team average
      - positions_gained_avg: avg positions gained (grid - finish)
    
    Targets:
      - position: final position
      - is_win: 1 if P1
      - is_podium: 1 if P1-P3
      - is_top10: 1 if P1-P10
      - is_dnf: 1 if DNF
    """
    print("  Building feature dataframe...")

    # Get all race results ordered by season/round
    results = db.query(
        DriverSession.driver_session_id,
        DriverSession.position,
        DriverSession.grid,
        DriverSession.points,
        DriverSession.dnf,
        DriverSession.status,
        Driver.driver_id,
        Driver.driver_code,
        Driver.constructor_id,
        Event.season,
        Event.round,
        Event.event_name,
        Event.country,
        Session.session_id,
    ).join(
        Driver, DriverSession.driver_id == Driver.driver_id
    ).join(
        Session, DriverSession.session_id == Session.session_id
    ).join(
        Event, Session.event_id == Event.event_id
    ).filter(
        Session.session_type == 'R',
        DriverSession.position.isnot(None),
        DriverSession.position > 0,
    ).order_by(
        Event.season, Event.round
    ).all()

    if not results:
        print("  No race results found!")
        return pd.DataFrame()

    print(f"  Found {len(results)} race results")

    rows = []
    for r in results:
        rows.append({
            'ds_id': r.driver_session_id,
            'session_id': r.session_id,
            'driver_id': r.driver_id,
            'driver_code': r.driver_code,
            'constructor_id': r.constructor_id or 0,
            'season': r.season,
            'round_num': r.round,
            'event_name': r.event_name,
            'country': r.country or '',
            'grid': r.grid or 20,
            'position': r.position,
            'points': float(r.points or 0),
            'is_dnf': 1 if r.dnf else 0,
            'status': r.status or '',
        })

    df = pd.DataFrame(rows)

    # ─── Rolling features per driver ───
    print("  Computing rolling features...")

    # Sort by season/round for rolling computations
    df = df.sort_values(['season', 'round_num']).reset_index(drop=True)

    # Rolling averages per driver
    for col, window in [('position', 5), ('grid', 5)]:
        df[f'avg_{col}_last{window}'] = (
            df.groupby('driver_id')[col]
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
        )

    # Win/podium/DNF rate last 10
    df['is_win'] = (df['position'] == 1).astype(int)
    df['is_podium'] = (df['position'] <= 3).astype(int)
    df['is_top10'] = (df['position'] <= 10).astype(int)

    for col, window in [('is_win', 10), ('is_podium', 10), ('is_dnf', 10)]:
        df[f'{col}_rate_last{window}'] = (
            df.groupby('driver_id')[col]
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
        )

    # Positions gained (grid minus finish - positive = gained positions)
    df['positions_gained'] = df['grid'] - df['position']
    df['positions_gained_avg'] = (
        df.groupby('driver_id')['positions_gained']
        .transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
    )

    # Team average finish (last 5 races)
    df['team_avg_finish_last5'] = (
        df.groupby('constructor_id')['position']
        .transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
    )

    # Points per race average
    df['avg_points_last5'] = (
        df.groupby('driver_id')['points']
        .transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
    )

    # Fill NaN rolling features with median values
    feature_cols = [
        'grid', 'avg_position_last5', 'avg_grid_last5',
        'is_win_rate_last10', 'is_podium_rate_last10', 'is_dnf_rate_last10',
        'positions_gained_avg', 'team_avg_finish_last5', 'avg_points_last5',
        'season', 'round_num', 'constructor_id',
    ]

    for col in feature_cols:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median() if not df[col].isna().all() else 0)

    print(f"  Feature dataframe: {len(df)} rows, {len(df.columns)} columns")
    return df


def train_models(df):
    """Train prediction models"""
    print("\n  Training ML models...")

    feature_cols = [
        'grid', 'avg_position_last5', 'avg_grid_last5',
        'is_win_rate_last10', 'is_podium_rate_last10', 'is_dnf_rate_last10',
        'positions_gained_avg', 'team_avg_finish_last5', 'avg_points_last5',
        'season', 'round_num',
    ]

    # Split: use last 2 seasons as test
    max_season = df['season'].max()
    train = df[df['season'] < max_season - 1].copy()
    test = df[df['season'] >= max_season - 1].copy()

    # Drop rows with NaN target
    train = train.dropna(subset=['position'] + feature_cols)
    test = test.dropna(subset=['position'] + feature_cols)

    X_train = train[feature_cols].values
    X_test = test[feature_cols].values

    print(f"  Train: {len(train)} rows, Test: {len(test)} rows")

    models = {}
    metrics = {}

    # 1. Position prediction (regression)
    print("  Training position predictor...")
    pos_model = GradientBoostingRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, random_state=42
    )
    pos_model.fit(X_train, train['position'])
    pos_pred = pos_model.predict(X_test)
    pos_mae = mean_absolute_error(test['position'], pos_pred)
    models['position'] = pos_model
    metrics['position_mae'] = round(pos_mae, 2)
    print(f"    Position MAE: {pos_mae:.2f}")

    # 2. Win prediction (binary classification)
    print("  Training win predictor...")
    win_model = GradientBoostingClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.1,
        subsample=0.8, random_state=42
    )
    win_model.fit(X_train, train['is_win'])
    win_pred = win_model.predict(X_test)
    win_acc = accuracy_score(test['is_win'], win_pred)
    models['win'] = win_model
    metrics['win_accuracy'] = round(win_acc, 4)
    print(f"    Win accuracy: {win_acc:.4f}")

    # 3. Podium prediction
    print("  Training podium predictor...")
    pod_model = GradientBoostingClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.1,
        subsample=0.8, random_state=42
    )
    pod_model.fit(X_train, train['is_podium'])
    pod_pred = pod_model.predict(X_test)
    pod_acc = accuracy_score(test['is_podium'], pod_pred)
    models['podium'] = pod_model
    metrics['podium_accuracy'] = round(pod_acc, 4)
    print(f"    Podium accuracy: {pod_acc:.4f}")

    # 4. DNF prediction
    print("  Training DNF predictor...")
    dnf_model = GradientBoostingClassifier(
        n_estimators=100, max_depth=3, learning_rate=0.1,
        subsample=0.8, random_state=42
    )
    dnf_model.fit(X_train, train['is_dnf'])
    dnf_pred = dnf_model.predict(X_test)
    dnf_acc = accuracy_score(test['is_dnf'], dnf_pred)
    models['dnf'] = dnf_model
    metrics['dnf_accuracy'] = round(dnf_acc, 4)
    print(f"    DNF accuracy: {dnf_acc:.4f}")

    # Feature importance (from position model)
    importances = pos_model.feature_importances_
    fi = sorted(zip(feature_cols, importances), key=lambda x: -x[1])
    metrics['feature_importance'] = [
        {"feature": f, "importance": round(float(i), 4)} for f, i in fi
    ]
    print("\n  Feature importance:")
    for f, i in fi[:6]:
        print(f"    {f}: {i:.4f}")

    return models, metrics, feature_cols


def save_models(models, metrics, feature_cols):
    """Save trained models and metadata"""
    version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    for name, model in models.items():
        path = os.path.join(MODEL_DIR, f"{name}_model.joblib")
        joblib.dump(model, path)
        print(f"  Saved {path}")

    # Save metadata
    meta = {
        "version": version,
        "trained_at": datetime.utcnow().isoformat(),
        "feature_columns": feature_cols,
        "metrics": metrics,
    }
    meta_path = os.path.join(MODEL_DIR, "model_metadata.json")
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    print(f"  Saved {meta_path}")

    return version


def generate_predictions_for_session(db, session_id, models, feature_cols):
    """Generate predictions for a specific session using the trained models"""
    # Get driver sessions for this session
    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id
    ).all()

    if not driver_sessions:
        return 0

    session = db.query(Session).filter(Session.session_id == session_id).first()
    event = db.query(Event).filter(Event.event_id == session.event_id).first()

    predictions_count = 0
    for ds in driver_sessions:
        driver = db.query(Driver).filter(Driver.driver_id == ds.driver_id).first()

        # Build features for this driver
        # Get recent history
        recent = db.query(DriverSession).join(Session).join(Event).filter(
            DriverSession.driver_id == ds.driver_id,
            Event.season <= event.season,
            DriverSession.position.isnot(None),
        ).order_by(Event.season.desc(), Event.round.desc()).limit(10).all()

        positions = [r.position for r in recent if r.position]
        grids = [r.grid for r in recent if r.grid]
        dnfs = [1 if r.dnf else 0 for r in recent]
        points = [float(r.points or 0) for r in recent]

        avg_pos_5 = np.mean(positions[:5]) if positions else 10
        avg_grid_5 = np.mean(grids[:5]) if grids else 10
        win_rate = sum(1 for p in positions[:10] if p == 1) / max(len(positions[:10]), 1)
        pod_rate = sum(1 for p in positions[:10] if p <= 3) / max(len(positions[:10]), 1)
        dnf_rate = np.mean(dnfs[:10]) if dnfs else 0.1
        gains = [g - p for g, p in zip(grids, positions) if g and p]
        avg_gain = np.mean(gains[:5]) if gains else 0
        avg_pts = np.mean(points[:5]) if points else 0

        features = np.array([[
            ds.grid or 15,          # grid
            avg_pos_5,              # avg_position_last5
            avg_grid_5,             # avg_grid_last5
            win_rate,               # is_win_rate_last10
            pod_rate,               # is_podium_rate_last10
            dnf_rate,               # is_dnf_rate_last10
            avg_gain,               # positions_gained_avg
            avg_pos_5,              # team_avg_finish_last5 (approx)
            avg_pts,                # avg_points_last5
            event.season,           # season
            event.round,            # round_num
        ]])

        # Predict
        try:
            exp_pos = float(models['position'].predict(features)[0])
            win_prob = float(models['win'].predict_proba(features)[0][1])
            pod_prob = float(models['podium'].predict_proba(features)[0][1])
            dnf_prob = float(models['dnf'].predict_proba(features)[0][1])
            top10_prob = 1.0 - (exp_pos / 20.0)  # Simple heuristic
            top10_prob = max(0, min(1, top10_prob))

            # Delete existing prediction if any
            db.query(Prediction).filter(
                Prediction.session_id == session_id,
                Prediction.driver_id == ds.driver_id
            ).delete()

            pred = Prediction(
                session_id=session_id,
                driver_id=ds.driver_id,
                model_version="1.0.0",
                win_probability=round(win_prob, 4),
                podium_probability=round(pod_prob, 4),
                top10_probability=round(top10_prob, 4),
                expected_position=round(exp_pos, 1),
                dnf_probability=round(dnf_prob, 4),
                prediction_confidence=round(1.0 - (dnf_prob * 0.3), 3),
                prediction_time=datetime.utcnow(),
            )
            db.add(pred)
            predictions_count += 1
        except Exception as e:
            print(f"    Warning: Could not predict for {driver.driver_code}: {e}")

    db.commit()
    return predictions_count


def main():
    print("=" * 60)
    print("  F1 ML PREDICTION PIPELINE")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Step 1: Build features
        df = build_feature_dataframe(db)
        if df.empty:
            print("No data to train on. Run ingestion first.")
            return

        # Step 2: Train models
        models, metrics, feature_cols = train_models(df)

        # Step 3: Save models
        version = save_models(models, metrics, feature_cols)

        # Step 4: Generate predictions for recent sessions
        print("\n  Generating predictions for recent sessions...")
        recent_sessions = db.query(Session).join(Event).filter(
            Session.session_type == 'R',
            Event.season >= 2020
        ).order_by(Event.season.desc(), Event.round.desc()).all()

        total_preds = 0
        for session in recent_sessions[:50]:  # Last 50 races
            count = generate_predictions_for_session(
                db, session.session_id, models, feature_cols
            )
            total_preds += count

        print(f"  Generated {total_preds} predictions for {min(len(recent_sessions), 50)} sessions")

        print(f"\n{'=' * 60}")
        print(f"  ML PIPELINE COMPLETE")
        print(f"{'=' * 60}")
        print(f"  Model version: {version}")
        print(f"  Position MAE: {metrics['position_mae']}")
        print(f"  Win accuracy: {metrics['win_accuracy']}")
        print(f"  Podium accuracy: {metrics['podium_accuracy']}")
        print(f"  DNF accuracy: {metrics['dnf_accuracy']}")
        print(f"  Predictions generated: {total_preds}")
        print(f"{'=' * 60}")

    except Exception as e:
        import traceback
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    main()
