"""
ML Training Pipeline

Implements ensemble models for F1 race predictions.
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple, List
from pathlib import Path
import joblib
import json
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    brier_score_loss, log_loss, roc_auc_score,
    mean_absolute_error, mean_squared_error
)
from scipy.stats import spearmanr
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier, CatBoostRegressor
import shap

from config import settings


class EnsembleModel:
    """Ensemble of gradient boosting models for classification"""
    
    def __init__(self, model_type='classification'):
        self.model_type = model_type
        self.models = []
        self.weights = []
        self.feature_names = None
        
    def fit(self, X: pd.DataFrame, y: np.ndarray):
        """Train ensemble models"""
        self.feature_names = X.columns.tolist()
        
        # XGBoost
        if self.model_type == 'classification':
            xgb_model = xgb.XGBClassifier(
                max_depth=6,
                learning_rate=0.05,
                n_estimators=500,
                subsample=0.8,
                colsample_bytree=0.8,
                gamma=0.1,
                min_child_weight=3,
                objective='binary:logistic',
                eval_metric='logloss',
                early_stopping_rounds=50,
                tree_method='hist',
                random_state=42
            )
        else:
            xgb_model = xgb.XGBRegressor(
                max_depth=6,
                learning_rate=0.05,
                n_estimators=500,
                subsample=0.8,
                colsample_bytree=0.8,
                gamma=0.1,
                min_child_weight=3,
                objective='reg:squarederror',
                eval_metric='rmse',
                early_stopping_rounds=50,
                tree_method='hist',
                random_state=42
            )
        
        # LightGBM
        if self.model_type == 'classification':
            lgb_model = lgb.LGBMClassifier(
                num_leaves=31,
                learning_rate=0.05,
                n_estimators=500,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_samples=20,
                objective='binary',
                metric='binary_logloss',
                verbosity=-1,
                random_state=42
            )
        else:
            lgb_model = lgb.LGBMRegressor(
                num_leaves=31,
                learning_rate=0.05,
                n_estimators=500,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_samples=20,
                objective='regression',
                metric='rmse',
                verbosity=-1,
                random_state=42
            )
        
        # CatBoost
        if self.model_type == 'classification':
            cat_model = CatBoostClassifier(
                iterations=500,
                learning_rate=0.05,
                depth=6,
                l2_leaf_reg=3,
                verbose=False,
                random_state=42
            )
        else:
            cat_model = CatBoostRegressor(
                iterations=500,
                learning_rate=0.05,
                depth=6,
                l2_leaf_reg=3,
                verbose=False,
                random_state=42
            )
        
        # Train models
        print(f"Training {self.model_type} ensemble...")
        xgb_model.fit(X, y)
        lgb_model.fit(X, y)
        cat_model.fit(X, y)
        
        self.models = [xgb_model, lgb_model, cat_model]
        self.weights = [0.35, 0.35, 0.30]  # Can be optimized via validation
        
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions (regression)"""
        predictions = []
        for model, weight in zip(self.models, self.weights):
            pred = model.predict(X)
            predictions.append(pred * weight)
        return np.sum(predictions, axis=0)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Make probability predictions (classification)"""
        predictions = []
        for model, weight in zip(self.models, self.weights):
            if hasattr(model, 'predict_proba'):
                pred = model.predict_proba(X)[:, 1]
            else:
                pred = model.predict(X)
            predictions.append(pred * weight)
        return np.sum(predictions, axis=0)
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get aggregated feature importance"""
        importances = []
        
        for model in self.models:
            if hasattr(model, 'feature_importances_'):
                importances.append(model.feature_importances_)
        
        avg_importance = np.mean(importances, axis=0)
        
        return pd.DataFrame({
            'feature': self.feature_names,
            'importance': avg_importance
        }).sort_values('importance', ascending=False)


class RacePredictionPipeline:
    """End-to-end prediction pipeline"""
    
    def __init__(self, model_dir: Path = None):
        self.model_dir = model_dir or settings.model_dir
        self.models = {
            'win_prob': EnsembleModel('classification'),
            'podium_prob': EnsembleModel('classification'),
            'top10_prob': EnsembleModel('classification'),
            'finish_position': EnsembleModel('regression'),
            'dnf_prob': EnsembleModel('classification'),
        }
        self.feature_columns = None
        self.scaler = None
        
    def prepare_training_data(self, features_df: pd.DataFrame, results_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Prepare training data with features and target variables
        
        Args:
            features_df: DataFrame with features for each driver-session
            results_df: DataFrame with actual race results
            
        Returns:
            X: Feature matrix
            y: Dictionary of target variables
        """
        # Merge features with results
        data = features_df.merge(results_df, on=['driver_session_id', 'driver_id'])
        
        # Remove metadata columns
        feature_cols = [col for col in data.columns if col not in [
            'driver_session_id', 'driver_id', 'session_id',
            'final_position', 'dnf', 'win', 'podium', 'top10'
        ]]
        
        X = data[feature_cols]
        self.feature_columns = feature_cols
        
        # Create target variables
        y = {
            'win': (data['final_position'] == 1).astype(int),
            'podium': (data['final_position'] <= 3).astype(int),
            'top10': (data['final_position'] <= 10).astype(int),
            'finish_position': data['final_position'].fillna(20),
            'dnf': data['dnf'].astype(int)
        }
        
        return X, y
    
    def train(self, X: pd.DataFrame, y: Dict[str, np.ndarray]):
        """Train all models"""
        print("Starting model training...")
        
        # Train each model
        self.models['win_prob'].fit(X, y['win'])
        print("✓ Win probability model trained")
        
        self.models['podium_prob'].fit(X, y['podium'])
        print("✓ Podium probability model trained")
        
        self.models['top10_prob'].fit(X, y['top10'])
        print("✓ Top-10 probability model trained")
        
        self.models['finish_position'].fit(X, y['finish_position'])
        print("✓ Finish position model trained")
        
        self.models['dnf_prob'].fit(X, y['dnf'])
        print("✓ DNF probability model trained")
        
        print("All models trained successfully!")
    
    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """Generate predictions for all drivers"""
        predictions = pd.DataFrame()
        
        predictions['win_probability'] = self.models['win_prob'].predict_proba(X)
        predictions['podium_probability'] = self.models['podium_prob'].predict_proba(X)
        predictions['top10_probability'] = self.models['top10_prob'].predict_proba(X)
        predictions['expected_position'] = self.models['finish_position'].predict(X)
        predictions['dnf_probability'] = self.models['dnf_prob'].predict_proba(X)
        
        # Clip probabilities
        for col in ['win_probability', 'podium_probability', 'top10_probability', 'dnf_probability']:
            predictions[col] = predictions[col].clip(0.001, 0.999)
        
        # Clip positions
        predictions['expected_position'] = predictions['expected_position'].clip(1, 20)
        
        # Compute confidence (based on model agreement)
        predictions['prediction_confidence'] = 0.75  # Placeholder
        
        return predictions
    
    def explain(self, X: pd.DataFrame, idx: int = 0) -> Dict:
        """Generate SHAP explanations for a single prediction"""
        explanations = {}
        
        for target, model in self.models.items():
            try:
                # Use TreeExplainer for gradient boosting models
                explainer = shap.TreeExplainer(model.models[0])  # Use first model (XGBoost)
                shap_values = explainer.shap_values(X.iloc[idx:idx+1])
                
                # Get top contributing features
                if isinstance(shap_values, list):
                    shap_values = shap_values[1]  # For binary classification
                
                feature_contributions = []
                for feature, shap_val, feature_val in zip(
                    X.columns, 
                    shap_values[0] if len(shap_values.shape) > 1 else shap_values,
                    X.iloc[idx]
                ):
                    feature_contributions.append({
                        'feature': feature,
                        'shap_value': float(shap_val),
                        'feature_value': float(feature_val),
                        'abs_contribution': abs(float(shap_val))
                    })
                
                # Sort by absolute contribution
                feature_contributions.sort(key=lambda x: x['abs_contribution'], reverse=True)
                
                explanations[target] = feature_contributions[:10]
                
            except Exception as e:
                print(f"Error explaining {target}: {e}")
                explanations[target] = []
        
        return explanations
    
    def evaluate(self, X: pd.DataFrame, y: Dict[str, np.ndarray]) -> Dict:
        """Evaluate model performance"""
        metrics = {}
        
        # Win prediction
        win_pred = self.models['win_prob'].predict_proba(X)
        metrics['win_brier'] = brier_score_loss(y['win'], win_pred)
        metrics['win_logloss'] = log_loss(y['win'], win_pred)
        if len(np.unique(y['win'])) > 1:
            metrics['win_auc'] = roc_auc_score(y['win'], win_pred)
        
        # Podium prediction
        podium_pred = self.models['podium_prob'].predict_proba(X)
        metrics['podium_brier'] = brier_score_loss(y['podium'], podium_pred)
        
        # Top-10 prediction
        top10_pred = self.models['top10_prob'].predict_proba(X)
        metrics['top10_brier'] = brier_score_loss(y['top10'], top10_pred)
        
        # Position prediction
        pos_pred = self.models['finish_position'].predict(X)
        metrics['position_mae'] = mean_absolute_error(y['finish_position'], pos_pred)
        metrics['position_rmse'] = np.sqrt(mean_squared_error(y['finish_position'], pos_pred))
        metrics['position_spearman'], _ = spearmanr(y['finish_position'], pos_pred)
        
        # Within 2 positions accuracy
        metrics['position_within_2'] = (np.abs(y['finish_position'] - pos_pred) <= 2).mean()
        
        # DNF prediction
        dnf_pred = self.models['dnf_prob'].predict_proba(X)
        metrics['dnf_brier'] = brier_score_loss(y['dnf'], dnf_pred)
        
        return metrics
    
    def save(self, version: str = "1.0.0"):
        """Save models to disk"""
        model_path = self.model_dir / f"model_{version}"
        model_path.mkdir(parents=True, exist_ok=True)
        
        # Save each model
        for name, model in self.models.items():
            joblib.dump(model, model_path / f"{name}.pkl")
        
        # Save metadata
        metadata = {
            'version': version,
            'feature_columns': self.feature_columns,
            'model_names': list(self.models.keys())
        }
        with open(model_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Models saved to {model_path}")
    
    def load(self, version: str = "1.0.0"):
        """Load models from disk"""
        model_path = self.model_dir / f"model_{version}"
        
        # Load metadata
        with open(model_path / "metadata.json", 'r') as f:
            metadata = json.load(f)
        
        self.feature_columns = metadata['feature_columns']
        
        # Load models
        for name in metadata['model_names']:
            self.models[name] = joblib.load(model_path / f"{name}.pkl")
        
        print(f"Models loaded from {model_path}")


class ModelEvaluator:
    """Evaluate model performance against baselines"""
    
    @staticmethod
    def evaluate_race(predictions: pd.DataFrame, actual: pd.DataFrame) -> Dict:
        """Evaluate predictions for a single race"""
        metrics = {}
        
        # Top-1 accuracy (winner prediction)
        predicted_winner = predictions['win_probability'].idxmax()
        actual_winner = actual[actual['final_position'] == 1].index[0]
        metrics['top1_accuracy'] = int(predicted_winner == actual_winner)
        
        # Podium hit rate
        predicted_podium = predictions.nlargest(3, 'podium_probability').index
        actual_podium = actual[actual['final_position'] <= 3].index
        metrics['podium_hit_rate'] = len(set(predicted_podium) & set(actual_podium)) / 3.0
        
        # Position correlation
        metrics['position_spearman'], _ = spearmanr(
            predictions['expected_position'],
            actual['final_position']
        )
        
        # MAE
        metrics['position_mae'] = np.abs(
            predictions['expected_position'] - actual['final_position']
        ).mean()
        
        return metrics
    
    @staticmethod
    def baseline_grid_order(actual: pd.DataFrame) -> pd.DataFrame:
        """Baseline: predict final position = grid position"""
        return actual[['grid_position']].rename(columns={'grid_position': 'expected_position'})
    
    @staticmethod
    def compare_to_baseline(model_metrics: Dict, baseline_metrics: Dict) -> Dict:
        """Compare model to baseline"""
        improvements = {}
        for key in model_metrics:
            if key in baseline_metrics:
                if baseline_metrics[key] != 0:
                    improvement_pct = (
                        (baseline_metrics[key] - model_metrics[key]) / abs(baseline_metrics[key])
                    ) * 100
                    improvements[f'{key}_improvement_pct'] = improvement_pct
        return improvements
