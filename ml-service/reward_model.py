import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import r2_score, mean_squared_error
import numpy as np
import pandas as pd
import pickle
import json
import os
from data_logger import DataLogger
import logging
from scipy import sparse
import traceback

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RewardNet(nn.Module):
    def __init__(self, input_size):
        super(RewardNet, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 32)
        self.fc4 = nn.Linear(32, 1)
        self.dropout = nn.Dropout(0.3)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.relu(self.fc3(x))
        x = self.fc4(x)
        return x

class RewardModel:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = []
        # WEIGHTS_PATH lets an operator point the server at an externally-supplied
        # weights directory (e.g. restored from the private netrai/neurotunes-weights
        # repo). Defaults to /app/models for backward compatibility. See MODEL_CARD.md.
        _weights_dir = os.environ.get('WEIGHTS_PATH') or '/app/models'
        self.model_path = os.path.join(_weights_dir, 'reward_model.pth')
        self.scaler_path = os.path.join(_weights_dir, 'reward_scaler.pkl')
        self.encoders_path = os.path.join(_weights_dir, 'reward_encoders.pkl')
        self.columns_path = os.path.join(_weights_dir, 'reward_columns.pkl')
        self.metrics_path = os.path.join(_weights_dir, 'reward_metrics.json')

        # Most recent evaluation metrics, populated by train().
        #   test_metrics: R2/MSE on the held-out test split of the final model
        #   cv_metrics:   mean/std of R2/MSE across k-fold cross-validation
        # These let the retraining scheduler make champion/challenger decisions
        # and let the paper report generalization (R2) rather than raw loss.
        self.test_metrics = {}
        self.cv_metrics = {}

        # Ensure models directory exists
        os.makedirs('/app/models', exist_ok=True)
        logger.info("RewardModel initialized")

    @staticmethod
    def _evaluate(model, X_tensor, y_tensor):
        """Compute regression metrics (MSE, R2) for a model on given tensors."""
        model.eval()
        with torch.no_grad():
            preds = model(X_tensor).squeeze().cpu().numpy()
        y_true = y_tensor.cpu().numpy()
        return {
            "mse": float(mean_squared_error(y_true, preds)),
            "r2": float(r2_score(y_true, preds)),
        }

    def _train_fold(self, X_train, y_train, input_size, num_epochs=100, lr=0.001):
        """Train a fresh RewardNet on the given tensors and return it.

        Used both for k-fold cross-validation and as the shared training core.
        """
        model = RewardNet(input_size)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=lr)
        for _ in range(num_epochs):
            model.train()
            optimizer.zero_grad()
            outputs = model(X_train)
            loss = criterion(outputs.squeeze(), y_train)
            loss.backward()
            optimizer.step()
        return model

    def cross_validate(self, X_tensor, y_tensor, k=5, num_epochs=100):
        """Run k-fold cross-validation and return mean/std of R2 and MSE.

        Returns a dict with r2_mean/r2_std/mse_mean/mse_std/folds. If there is
        not enough data for k folds, k is reduced; if fewer than 2 folds are
        possible, cross-validation is skipped and an empty dict is returned.
        """
        n = X_tensor.shape[0]
        k = min(k, n // 2) if n >= 4 else 0
        if k < 2:
            logger.warning(f"Not enough samples ({n}) for cross-validation; skipping")
            return {}

        input_size = X_tensor.shape[1]
        kf = KFold(n_splits=k, shuffle=True, random_state=42)
        r2_scores, mse_scores = [], []

        X_np = X_tensor.cpu().numpy()
        for fold, (train_idx, val_idx) in enumerate(kf.split(X_np), start=1):
            X_tr = X_tensor[train_idx]
            y_tr = y_tensor[train_idx]
            X_val = X_tensor[val_idx]
            y_val = y_tensor[val_idx]

            fold_model = self._train_fold(X_tr, y_tr, input_size, num_epochs=num_epochs)
            m = self._evaluate(fold_model, X_val, y_val)
            r2_scores.append(m["r2"])
            mse_scores.append(m["mse"])
            logger.info(f"CV fold {fold}/{k}: R2={m['r2']:.4f}, MSE={m['mse']:.4f}")

        metrics = {
            "r2_mean": float(np.mean(r2_scores)),
            "r2_std": float(np.std(r2_scores)),
            "mse_mean": float(np.mean(mse_scores)),
            "mse_std": float(np.std(mse_scores)),
            "folds": k,
        }
        logger.info(
            f"Cross-validation ({k}-fold): R2={metrics['r2_mean']:.4f}"
            f"±{metrics['r2_std']:.4f}, MSE={metrics['mse_mean']:.4f}±{metrics['mse_std']:.4f}"
        )
        return metrics

    def safe_convert_types(self, df):
        """Safely convert data types and handle problematic columns"""
        logger.info(f"Converting data types for DataFrame with shape: {df.shape}")
        logger.debug(f"Original dtypes:\n{df.dtypes}")

        converted_df = df.copy()
        problematic_columns = []

        for col in converted_df.columns:
            try:
                logger.debug(f"Processing column: {col}")

                # Check for numpy object types
                if converted_df[col].dtype == 'object' or str(converted_df[col].dtype).startswith('object'):
                    logger.debug(f"Column {col} has object dtype, attempting conversion")

                    # Try to convert to numeric first
                    try:
                        converted_df[col] = pd.to_numeric(converted_df[col], errors='coerce')
                        logger.debug(f"Successfully converted {col} to numeric")
                    except:
                        # If numeric conversion fails, try string conversion
                        converted_df[col] = converted_df[col].astype(str)
                        logger.debug(f"Converted {col} to string")

                # Handle any remaining numpy types
                if hasattr(converted_df[col].iloc[0], 'item'):
                    converted_df[col] = converted_df[col].apply(lambda x: x.item() if hasattr(x, 'item') else x)
                    logger.debug(f"Applied .item() conversion to {col}")

            except Exception as e:
                logger.error(f"Error processing column {col}: {str(e)}")
                problematic_columns.append(col)
                # Drop problematic columns as last resort
                converted_df = converted_df.drop(columns=[col])

        if problematic_columns:
            logger.warning(f"Dropped problematic columns: {problematic_columns}")

        logger.info(f"Final converted dtypes:\n{converted_df.dtypes}")
        return converted_df

    def prepare_features(self, df):
        """Prepare features with comprehensive error handling"""
        logger.info(f"Preparing features for {len(df)} records")

        try:
            # Safe type conversion
            df = self.safe_convert_types(df)

            # Log data sample
            logger.debug(f"Data sample:\n{df.head()}")
            logger.debug(f"Data info:\n{df.info()}")

            # Separate numeric and categorical columns
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()

            logger.info(f"Numeric columns: {numeric_columns}")
            logger.info(f"Categorical columns: {categorical_columns}")

            # Process categorical columns
            processed_df = df.copy()
            for col in categorical_columns:
                try:
                    if col not in self.label_encoders:
                        self.label_encoders[col] = LabelEncoder()
                        processed_df[col] = self.label_encoders[col].fit_transform(processed_df[col].fillna('unknown'))
                        logger.debug(f"Fitted new encoder for {col}")
                    else:
                        # Handle unseen categories
                        unique_vals = processed_df[col].fillna('unknown').unique()
                        known_vals = self.label_encoders[col].classes_
                        new_vals = set(unique_vals) - set(known_vals)

                        if new_vals:
                            logger.warning(f"New categories in {col}: {new_vals}")
                            # Add new categories to encoder
                            all_vals = list(known_vals) + list(new_vals)
                            self.label_encoders[col].classes_ = np.array(all_vals)

                        processed_df[col] = self.label_encoders[col].transform(processed_df[col].fillna('unknown'))
                        logger.debug(f"Transformed existing column {col}")

                except Exception as e:
                    logger.error(f"Error encoding column {col}: {str(e)}")
                    # Drop problematic categorical column
                    processed_df = processed_df.drop(columns=[col])

            # Fill missing values in numeric columns
            for col in numeric_columns:
                if col in processed_df.columns:
                    processed_df[col] = processed_df[col].fillna(processed_df[col].mean())

            # Final type check
            logger.info(f"Final processed dtypes:\n{processed_df.dtypes}")

            return processed_df

        except Exception as e:
            logger.error(f"Error in prepare_features: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def safe_tensor_conversion(self, data, name="data"):
        """Safely convert data to tensor with comprehensive error handling"""
        logger.info(f"Converting {name} to tensor, shape: {data.shape if hasattr(data, 'shape') else 'unknown'}")

        try:
            # Handle sparse matrices
            if sparse.issparse(data):
                logger.debug(f"{name} is sparse, converting to dense")
                data = data.toarray()

            # Convert to numpy array if not already
            if not isinstance(data, np.ndarray):
                logger.debug(f"Converting {name} to numpy array")
                data = np.array(data)

            # Check for problematic data types
            logger.debug(f"{name} dtype: {data.dtype}")

            # Handle object arrays
            if data.dtype == 'object':
                logger.warning(f"{name} has object dtype, attempting conversion")
                try:
                    # Try to convert to float
                    data = data.astype(float)
                    logger.debug(f"Successfully converted {name} to float")
                except:
                    logger.error(f"Cannot convert {name} object array to numeric")
                    raise ValueError(f"Cannot convert {name} to numeric tensor")

            # Ensure data is numeric
            if not np.issubdtype(data.dtype, np.number):
                logger.error(f"{name} is not numeric: {data.dtype}")
                raise ValueError(f"{name} must be numeric for tensor conversion")

            # Check for NaN or infinite values
            if np.any(np.isnan(data)):
                logger.warning(f"{name} contains NaN values, filling with 0")
                data = np.nan_to_num(data, nan=0.0)

            if np.any(np.isinf(data)):
                logger.warning(f"{name} contains infinite values, clipping")
                data = np.clip(data, -1e6, 1e6)

            # Convert to tensor
            tensor = torch.FloatTensor(data)
            logger.info(f"Successfully converted {name} to tensor: {tensor.shape}")

            return tensor

        except Exception as e:
            logger.error(f"Error converting {name} to tensor: {str(e)}")
            logger.error(f"Data sample: {data[:5] if hasattr(data, '__getitem__') else 'Cannot display'}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def train(self):
        """Train the reward model with comprehensive error handling and logging"""
        logger.info("Starting reward model training")

        try:
            # Initialize data logger
            data_logger = DataLogger()
            logger.info("DataLogger initialized")

            # CORRECTED QUERY: Use the actual table names that exist
            logger.info("Fetching training data from database")
            query = """
            SELECT 
                g.tempo, g.music_key, g.mode, g.therapy_goal, g.duration,
                g.patient_data, g.music_params,
                f.overall_rating, f.effectiveness_rating, f.enjoyment_rating,
                f.reported_feeling, f.mood_change, f.energy_change, f.stress_change,
                f.listen_duration_seconds, f.replay_count, f.would_use_again
            FROM neurotunes_generation_log g
            JOIN neurotunes_feedback_log f ON g.log_id = f.generation_log_id
            WHERE f.overall_rating IS NOT NULL
            ORDER BY f.feedback_time DESC
            LIMIT 1000
            """

            cursor = data_logger.connection.cursor(dictionary=True)
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()

            # Close connection properly
            if hasattr(data_logger, 'connection') and data_logger.connection.is_connected():
                data_logger.connection.close()
                logger.info("Database connection closed")

            logger.info(f"Fetched {len(results)} training records")

            if len(results) < 10:
                logger.error(f"Insufficient training data: {len(results)} records")
                return False

            # Convert to DataFrame
            df = pd.DataFrame(results)
            logger.info(f"Created DataFrame with shape: {df.shape}")
            logger.debug(f"DataFrame columns: {df.columns.tolist()}")

            # Prepare features and target
            logger.info("Preparing features")
            target_col = 'overall_rating'
            feature_cols = [col for col in df.columns if col != target_col]

            X_df = df[feature_cols].copy()
            y = df[target_col].values

            logger.info(f"Target variable stats - Min: {y.min()}, Max: {y.max()}, Mean: {y.mean():.2f}")

            # Process features
            X_processed = self.prepare_features(X_df)
            self.feature_columns = X_processed.columns.tolist()

            logger.info(f"Processed features shape: {X_processed.shape}")
            logger.info(f"Feature columns: {self.feature_columns}")

            # Scale features
            logger.info("Scaling features")
            X_scaled = self.scaler.fit_transform(X_processed)
            logger.info(f"Scaled features shape: {X_scaled.shape}")

            # Convert to tensors with error handling
            logger.info("Converting to tensors")
            X_tensor = self.safe_tensor_conversion(X_scaled, "features")
            y_tensor = self.safe_tensor_conversion(y, "target")

            # k-fold cross-validation for a generalization estimate (R2/MSE)
            # BEFORE fitting the final model. This is reported in the paper and
            # used as a stability signal; it does not affect the final weights.
            logger.info("Running k-fold cross-validation")
            self.cv_metrics = self.cross_validate(X_tensor, y_tensor, k=5, num_epochs=100)

            # Split data
            logger.info("Splitting data")
            X_train, X_test, y_train, y_test = train_test_split(
                X_tensor, y_tensor, test_size=0.2, random_state=42
            )

            logger.info(f"Training set: {X_train.shape}, Test set: {X_test.shape}")

            # Initialize model
            input_size = X_train.shape[1]
            logger.info(f"Initializing model with input size: {input_size}")
            self.model = RewardNet(input_size)

            # Training setup
            criterion = nn.MSELoss()
            optimizer = optim.Adam(self.model.parameters(), lr=0.001)

            # Training loop with detailed logging
            logger.info("Starting training loop")
            num_epochs = 100
            best_loss = float('inf')

            for epoch in range(num_epochs):
                self.model.train()
                optimizer.zero_grad()

                outputs = self.model(X_train)
                loss = criterion(outputs.squeeze(), y_train)

                loss.backward()
                optimizer.step()

                # Validation
                if epoch % 10 == 0:
                    self.model.eval()
                    with torch.no_grad():
                        val_outputs = self.model(X_test)
                        val_loss = criterion(val_outputs.squeeze(), y_test)

                        logger.info(f"Epoch {epoch}: Train Loss: {loss.item():.4f}, Val Loss: {val_loss.item():.4f}")

                        if val_loss.item() < best_loss:
                            best_loss = val_loss.item()
                            logger.debug(f"New best validation loss: {best_loss:.4f}")

            # Final held-out test metrics (MSE + R2) for the fitted model.
            self.test_metrics = self._evaluate(self.model, X_test, y_test)
            logger.info(
                f"Final test metrics: R2={self.test_metrics['r2']:.4f}, "
                f"MSE={self.test_metrics['mse']:.4f}"
            )

            # Save model and preprocessors
            logger.info("Saving model and preprocessors")

            torch.save(self.model.state_dict(), self.model_path)
            logger.info(f"Model saved to {self.model_path}")

            with open(self.scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            logger.info(f"Scaler saved to {self.scaler_path}")

            with open(self.encoders_path, 'wb') as f:
                pickle.dump(self.label_encoders, f)
            logger.info(f"Encoders saved to {self.encoders_path}")

            with open(self.columns_path, 'wb') as f:
                pickle.dump(self.feature_columns, f)
            logger.info(f"Columns saved to {self.columns_path}")

            # Persist evaluation metrics next to the model so the retraining
            # scheduler can compare a future challenger against this champion.
            try:
                metrics_payload = {
                    "test_metrics": self.test_metrics,
                    "cv_metrics": self.cv_metrics,
                }
                with open(self.metrics_path, 'w') as f:
                    json.dump(metrics_payload, f, indent=2)
                logger.info(f"Metrics saved to {self.metrics_path}")
            except Exception as metrics_err:
                logger.warning(f"Could not persist metrics: {metrics_err}")

            logger.info(f"Training completed successfully! Final validation loss: {best_loss:.4f}")
            return True

        except Exception as e:
            logger.error(f"Training failed with error: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    def load_model(self):
        """Load trained model with error handling"""
        try:
            if not os.path.exists(self.model_path):
                logger.warning("No trained reward model found")
                return False

            # Load feature columns first to get input size
            with open(self.columns_path, 'rb') as f:
                self.feature_columns = pickle.load(f)

            input_size = len(self.feature_columns)
            self.model = RewardNet(input_size)
            self.model.load_state_dict(torch.load(self.model_path))
            self.model.eval()

            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)

            with open(self.encoders_path, 'rb') as f:
                self.label_encoders = pickle.load(f)

            logger.info("Reward model loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error loading reward model: {str(e)}")
            return False

    def predict_reward(self, music_params, patient_data):
        """Predict reward with error handling"""
        try:
            if self.model is None:
                if not self.load_model():
                    logger.warning("No trained model available, returning default reward")
                    return 0.5

            # Combine parameters
            combined_data = {**music_params, **patient_data}
            df = pd.DataFrame([combined_data])

            # Process features
            X_processed = self.prepare_features(df)

            # Ensure all expected columns are present
            for col in self.feature_columns:
                if col not in X_processed.columns:
                    X_processed[col] = 0

            X_processed = X_processed[self.feature_columns]
            X_scaled = self.scaler.transform(X_processed)
            X_tensor = self.safe_tensor_conversion(X_scaled, "prediction_features")

            with torch.no_grad():
                reward = self.model(X_tensor).item()

            logger.debug(f"Predicted reward: {reward}")
            return reward

        except Exception as e:
            logger.error(f"Error predicting reward: {str(e)}")
            return 0.5  # Default reward

# Global instance
reward_model = RewardModel()
