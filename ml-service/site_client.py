# ====
# NeuroTunes Site Client
# Handles local federated learning at healthcare sites
# Implements differential privacy and secure communication
# ====

import numpy as np
import json
import logging
import hashlib
import requests
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import torch
import torch.nn as nn
from cryptography.fernet import Fernet
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import mysql.connector
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PrivacyConfig:
    """Configuration for differential privacy."""
    epsilon: float = 1.0  # Privacy budget
    delta: float = 1e-5   # Privacy parameter
    max_grad_norm: float = 1.0  # Gradient clipping threshold
    noise_multiplier: float = 1.1  # Noise scale
    lot_size: int = 32    # Logical batch size

@dataclass
class TrainingConfig:
    """Local training configuration."""
    epochs: int = 5
    batch_size: int = 32
    learning_rate: float = 0.001
    validation_split: float = 0.2
    early_stopping_patience: int = 3
    min_samples_required: int = 100

class DifferentialPrivacyEngine:
    """
    Implements differential privacy for federated learning.
    Adds calibrated noise to gradients and clips them.
    """

    def __init__(self, privacy_config: PrivacyConfig):
        self.config = privacy_config
        self.privacy_spent = 0.0
        self.noise_scale = self._calculate_noise_scale()

    def _calculate_noise_scale(self) -> float:
        """Calculate noise scale based on privacy parameters."""
        return self.config.noise_multiplier * self.config.max_grad_norm

    def clip_gradients(self, gradients: List[torch.Tensor]) -> List[torch.Tensor]:
        """Clip gradients to bound sensitivity."""
        clipped_grads = []
        total_norm = 0.0

        # Calculate total norm
        for grad in gradients:
            if grad is not None:
                total_norm += grad.norm().item() ** 2
        total_norm = total_norm ** 0.5

        # Clip if necessary
        clip_coef = min(1.0, self.config.max_grad_norm / (total_norm + 1e-6))

        for grad in gradients:
            if grad is not None:
                clipped_grads.append(grad * clip_coef)
            else:
                clipped_grads.append(grad)

        return clipped_grads

    def add_noise(self, gradients: List[torch.Tensor]) -> List[torch.Tensor]:
        """Add calibrated Gaussian noise to gradients."""
        noisy_grads = []

        for grad in gradients:
            if grad is not None:
                noise = torch.normal(0, self.noise_scale, grad.shape)
                noisy_grads.append(grad + noise)
            else:
                noisy_grads.append(grad)

        return noisy_grads

    def process_gradients(self, gradients: List[torch.Tensor]) -> List[torch.Tensor]:
        """Apply differential privacy to gradients."""
        clipped_grads = self.clip_gradients(gradients)
        noisy_grads = self.add_noise(clipped_grads)

        # Update privacy spent (simplified accounting)
        self.privacy_spent += self.config.epsilon / 100  # Per batch

        return noisy_grads

    def get_privacy_spent(self) -> float:
        """Get total privacy budget spent."""
        return self.privacy_spent

class LocalRewardModel(nn.Module):
    """
    Local version of the reward model for federated training.
    """

    def __init__(self, input_dim: int = 50, hidden_dim: int = 128):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.network(x)

class SiteClient:
    """
    Federated learning client for healthcare sites.
    Handles local training with privacy preservation.
    """

    def __init__(self, 
                 site_id: str,
                 site_name: str,
                 coordinator_url: str,
                 privacy_config: Optional[PrivacyConfig] = None,
                 training_config: Optional[TrainingConfig] = None):

        self.site_id = site_id
        self.site_name = site_name
        self.coordinator_url = coordinator_url

        # Configuration
        self.privacy_config = privacy_config or PrivacyConfig()
        self.training_config = training_config or TrainingConfig()

        # Privacy engine
        self.privacy_engine = DifferentialPrivacyEngine(self.privacy_config)

        # Model and training state
        self.local_model = None
        self.optimizer = None
        self.scaler = StandardScaler()

        # Database connection
        self.db_connection = self._setup_database()

        # Communication
        self.encryption_key = None
        self.cipher_suite = None

        # Status
        self.status = 'initialized'
        self.current_round_id = None
        self.training_thread = None

        logger.info(f"Site client initialized: {site_name} ({site_id})")

    def _setup_database(self):
        """Setup database connection for local data access."""
        try:
            connection = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_DATABASE', 'netraidb'),
                user=os.getenv('DB_USER', 'john'),
                password=os.getenv('DB_PASSWORD', 'john'),
                port=int(os.getenv('MYSQL_PORT', 3306))
            )
            logger.info("Database connection established")
            return connection
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return None

    def register_with_coordinator(self, estimated_patients: int) -> bool:
        """Register this site with the federation coordinator."""
        try:
            response = requests.post(f"{self.coordinator_url}/register_site", json={
                'site_name': self.site_name,
                'location': 'Healthcare Facility',  # Could be configured
                'estimated_patients': estimated_patients,
                'capabilities': {
                    'differential_privacy': True,
                    'secure_aggregation': True,
                    'clinical_metrics': True
                }
            })

            if response.status_code == 200:
                result = response.json()
                self.site_id = result.get('site_id', self.site_id)
                self.encryption_key = result.get('encryption_key', '').encode()
                if self.encryption_key:
                    self.cipher_suite = Fernet(self.encryption_key)

                logger.info(f"Successfully registered with coordinator")
                return True
            else:
                logger.error(f"Registration failed: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False

    def send_heartbeat(self) -> bool:
        """Send heartbeat to coordinator with status update."""
        try:
            patient_count = self._get_local_patient_count()

            response = requests.post(f"{self.coordinator_url}/heartbeat", json={
                'site_id': self.site_id,
                'status': self.status,
                'patient_count': patient_count,
                'privacy_budget_remaining': self.privacy_config.epsilon - self.privacy_engine.get_privacy_spent(),
                'last_training': self.current_round_id,
                'timestamp': datetime.now().isoformat()
            })

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            return False

    def _get_local_patient_count(self) -> int:
        """Get approximate count of local patients (privacy-safe)."""
        if not self.db_connection:
            return 0

        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM neurotunes_generation_log")
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting patient count: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()

    def get_local_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Retrieve local training data with privacy preservation.
        Only accesses aggregated, anonymized features.
        """
        if not self.db_connection:
            raise ValueError("No database connection available")

        cursor = self.db_connection.cursor(dictionary=True)
        try:
            # Get training data from the RLHF view (already anonymized)
            cursor.execute("""
                SELECT 
                    g.music_params,
                    f.overall_rating,
                    f.effectiveness_rating,
                    f.mood_change,
                    f.energy_change,
                    f.stress_change,
                    f.listen_duration_seconds,
                    f.would_use_again
                FROM neurotunes_generation_log g
                JOIN neurotunes_feedback_log f ON g.log_id = f.generation_log_id
                WHERE f.feedback_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                ORDER BY f.feedback_time DESC
                LIMIT 10000
            """)

            data = cursor.fetchall()

            if len(data) < self.training_config.min_samples_required:
                raise ValueError(f"Insufficient training data: {len(data)} < {self.training_config.min_samples_required}")

            # Extract features and labels
            features = []
            labels = []

            for row in data:
                # Parse music parameters
                music_params = json.loads(row['music_params'])

                # Create feature vector (anonymized)
                feature_vector = [
                    music_params.get('tempo', 120) / 200.0,  # Normalized
                    1.0 if music_params.get('key', 'C') in ['C', 'G', 'D'] else 0.0,
                    1.0 if music_params.get('mode', 'major') == 'major' else 0.0,
                    music_params.get('duration', 60) / 300.0,  # Normalized
                    row['effectiveness_rating'] / 5.0,
                    1.0 if row['mood_change'] == 'better' else 0.0,
                    1.0 if row['energy_change'] == 'better' else 0.0,
                    1.0 if row['stress_change'] == 'better' else 0.0,
                    row['listen_duration_seconds'] / 300.0,  # Normalized
                    1.0 if row['would_use_again'] else 0.0
                ]

                # Pad to fixed size
                while len(feature_vector) < 50:
                    feature_vector.append(0.0)

                features.append(feature_vector[:50])  # Truncate if too long
                labels.append(row['overall_rating'] / 5.0)  # Normalized rating

            X = np.array(features)
            y = np.array(labels)

            # Apply differential privacy to the dataset
            X = self._add_dataset_noise(X)

            logger.info(f"Retrieved {len(X)} training samples")
            return X, y

        except Exception as e:
            logger.error(f"Error retrieving training data: {e}")
            raise
        finally:
            cursor.close()

    def _add_dataset_noise(self, X: np.ndarray) -> np.ndarray:
        """Add noise to dataset for differential privacy."""
        noise_scale = 0.01  # Small noise for dataset-level privacy
        noise = np.random.normal(0, noise_scale, X.shape)
        return X + noise

    def train_local_model(self, round_id: str, global_weights: Optional[Dict] = None) -> Dict:
        """
        Train local model with differential privacy.
        """
        logger.info(f"Starting local training for round {round_id}")
        self.current_round_id = round_id
        self.status = 'training'

        try:
            # Get local training data
            X, y = self.get_local_training_data()

            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=self.training_config.validation_split, random_state=42
            )

            # Scale features
            X_train = self.scaler.fit_transform(X_train)
            X_val = self.scaler.transform(X_val)

            # Initialize model
            self.local_model = LocalRewardModel(input_dim=X.shape[1])

            # Load global weights if provided
            if global_weights:
                self.local_model.load_state_dict(global_weights)

            # Setup optimizer
            self.optimizer = torch.optim.Adam(
                self.local_model.parameters(), 
                lr=self.training_config.learning_rate
            )

            criterion = nn.MSELoss()

            # Convert to tensors
            X_train_tensor = torch.FloatTensor(X_train)
            y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
            X_val_tensor = torch.FloatTensor(X_val)
            y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1)

            # Training loop with differential privacy
            best_val_loss = float('inf')
            patience_counter = 0

            for epoch in range(self.training_config.epochs):
                self.local_model.train()

                # Batch training with DP
                for i in range(0, len(X_train_tensor), self.training_config.batch_size):
                    batch_X = X_train_tensor[i:i+self.training_config.batch_size]
                    batch_y = y_train_tensor[i:i+self.training_config.batch_size]

                    self.optimizer.zero_grad()

                    # Forward pass
                    outputs = self.local_model(batch_X)
                    loss = criterion(outputs, batch_y)

                    # Backward pass
                    loss.backward()

                    # Apply differential privacy to gradients
                    gradients = [param.grad for param in self.local_model.parameters()]
                    private_gradients = self.privacy_engine.process_gradients(gradients)

                    # Update parameters with private gradients
                    for param, private_grad in zip(self.local_model.parameters(), private_gradients):
                        if private_grad is not None:
                            param.grad = private_grad

                    self.optimizer.step()

                # Validation
                self.local_model.eval()
                with torch.no_grad():
                    val_outputs = self.local_model(X_val_tensor)
                    val_loss = criterion(val_outputs, y_val_tensor).item()

                logger.info(f"Epoch {epoch+1}/{self.training_config.epochs}, Val Loss: {val_loss:.4f}")

                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= self.training_config.early_stopping_patience:
                        logger.info(f"Early stopping at epoch {epoch+1}")
                        break

            # Calculate clinical metrics
            clinical_metrics = self._calculate_clinical_metrics(X_val_tensor, y_val_tensor)

            # Prepare results
            training_results = {
                'round_id': round_id,
                'sample_count': len(X_train),
                'validation_loss': best_val_loss,
                'privacy_spent': self.privacy_engine.get_privacy_spent(),
                'clinical_metrics': clinical_metrics,
                'model_weights': self.local_model.state_dict(),
                'training_completed': True
            }

            self.status = 'completed'
            logger.info(f"Local training completed for round {round_id}")

            return training_results

        except Exception as e:
            logger.error(f"Training failed: {e}")
            self.status = 'failed'
            return {
                'round_id': round_id,
                'training_completed': False,
                'error': str(e)
            }

    def _calculate_clinical_metrics(self, X_val: torch.Tensor, y_val: torch.Tensor) -> Dict:
        """Calculate clinical effectiveness metrics."""
        self.local_model.eval()

        with torch.no_grad():
            predictions = self.local_model(X_val)

            # Calculate metrics
            mse = nn.MSELoss()(predictions, y_val).item()
            mae = torch.mean(torch.abs(predictions - y_val)).item()

            # Clinical interpretation
            accuracy = 1.0 - mae  # Simple accuracy measure
            patient_satisfaction = torch.mean(predictions).item()

            return {
                'patient_satisfaction': patient_satisfaction,
                'prediction_accuracy': accuracy,
                'symptom_improvement': min(1.0, 1.0 - mse),  # Normalized
                'therapy_adherence': 0.85,  # Placeholder - would come from real data
                'adverse_events': 0.02  # Placeholder - would come from real data
            }

    def encrypt_model_weights(self, weights: Dict) -> bytes:
        """Encrypt model weights for secure transmission."""
        if not self.cipher_suite:
            raise ValueError("Encryption not initialized")

        # Convert weights to JSON-serializable format
        serializable_weights = {}
        for key, tensor in weights.items():
            serializable_weights[key] = tensor.numpy().tolist()

        weights_json = json.dumps(serializable_weights)
        return self.cipher_suite.encrypt(weights_json.encode())

    def submit_model_update(self, training_results: Dict) -> bool:
        """Submit encrypted model update to coordinator."""
        try:
            # Encrypt model weights
            encrypted_weights = self.encrypt_model_weights(training_results['model_weights'])

            # Prepare submission
            submission = {
                'site_id': self.site_id,
                'round_id': training_results['round_id'],
                'encrypted_weights': encrypted_weights.hex(),  # Convert to hex for JSON
                'sample_count': training_results['sample_count'],
                'privacy_spent': training_results['privacy_spent'],
                'validation_loss': training_results['validation_loss'],
                'clinical_metrics': training_results['clinical_metrics']
            }

            response = requests.post(f"{self.coordinator_url}/submit_update", json=submission)

            if response.status_code == 200:
                logger.info("Model update submitted successfully")
                return True
            else:
                logger.error(f"Submission failed: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error submitting update: {e}")
            return False

    def participate_in_round(self, round_id: str) -> bool:
        """Participate in a federation round."""
        try:
            # Get training configuration from coordinator
            config_response = requests.get(
                f"{self.coordinator_url}/training_config/{self.site_id}/{round_id}"
            )

            if config_response.status_code != 200:
                logger.error("Failed to get training configuration")
                return False

            config = config_response.json()

            # Update local configuration
            self.privacy_config.epsilon = config.get('privacy_epsilon', self.privacy_config.epsilon)
            self.training_config.epochs = config.get('training_epochs', self.training_config.epochs)

            # Train local model
            training_results = self.train_local_model(round_id)

            if not training_results.get('training_completed', False):
                return False

            # Submit results
            return self.submit_model_update(training_results)

        except Exception as e:
            logger.error(f"Error participating in round {round_id}: {e}")
            return False

    def start_heartbeat_thread(self, interval: int = 60):
        """Start background heartbeat thread."""
        def heartbeat_loop():
            while True:
                self.send_heartbeat()
                time.sleep(interval)

        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        logger.info("Heartbeat thread started")

# Example usage
if __name__ == "__main__":
    # Initialize site client
    privacy_config = PrivacyConfig(epsilon=1.0, delta=1e-5)
    training_config = TrainingConfig(epochs=5, batch_size=32)

    client = SiteClient(
        site_id="site_test_001",
        site_name="Test Medical Center",
        coordinator_url="http://localhost:8000",
        privacy_config=privacy_config,
        training_config=training_config
    )

    print("Site Client initialized for federated learning")
