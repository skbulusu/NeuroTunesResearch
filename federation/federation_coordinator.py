# ====
# NeuroTunes Federation Coordinator
# Orchestrates federated learning across multiple healthcare sites
# WITHOUT accessing any patient data - only model parameters
# ====

import asyncio
import json
import logging
import hashlib
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import uuid
from cryptography.fernet import Fernet
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SiteInfo:
    """Information about a participating healthcare site."""
    site_id: str
    site_name: str
    location: str
    last_seen: datetime
    patient_count: int  # Approximate, for weighting
    model_version: str
    privacy_budget: float  # Remaining differential privacy budget
    status: str  # 'active', 'inactive', 'training'

@dataclass
class FederationRound:
    """Information about a federation training round."""
    round_id: str
    start_time: datetime
    participating_sites: List[str]
    target_sites: int
    min_sites: int
    privacy_epsilon: float
    convergence_threshold: float
    status: str  # 'preparing', 'training', 'aggregating', 'completed', 'failed'

@dataclass
class ModelUpdate:
    """Encrypted model update from a site."""
    site_id: str
    round_id: str
    encrypted_weights: bytes
    sample_count: int
    privacy_spent: float
    validation_loss: float
    clinical_metrics: Dict
    timestamp: datetime

class FederationCoordinator:
    """
    Coordinates federated learning across multiple healthcare sites.
    Ensures privacy by never accessing raw patient data.
    """

    def __init__(self, 
                 min_sites: int = 3,
                 max_sites: int = 10,
                 privacy_epsilon: float = 1.0,
                 convergence_threshold: float = 0.01):

        self.min_sites = min_sites
        self.max_sites = max_sites
        self.privacy_epsilon = privacy_epsilon
        self.convergence_threshold = convergence_threshold

        # Site management
        self.registered_sites: Dict[str, SiteInfo] = {}
        self.active_sites: Dict[str, SiteInfo] = {}

        # Federation rounds
        self.current_round: Optional[FederationRound] = None
        self.round_history: List[FederationRound] = []
        self.model_updates: Dict[str, List[ModelUpdate]] = {}  # round_id -> updates

        # Global model state
        self.global_model_version = "1.0.0"
        self.global_model_hash = None
        self.aggregated_weights = None

        # Security
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)

        # Monitoring
        self.federation_metrics = {
            'total_rounds': 0,
            'successful_rounds': 0,
            'total_sites_trained': 0,
            'average_convergence_time': 0,
            'privacy_budget_used': 0,
            'clinical_improvement': 0
        }

        logger.info(f"Federation Coordinator initialized with {min_sites}-{max_sites} sites")

    def register_site(self, site_name: str, location: str, 
                     estimated_patients: int) -> str:
        """
        Register a new healthcare site for federated learning.
        Returns site_id for authentication.
        """
        site_id = f"site_{hashlib.md5(f'{site_name}_{location}'.encode()).hexdigest()[:8]}"

        site_info = SiteInfo(
            site_id=site_id,
            site_name=site_name,
            location=location,
            last_seen=datetime.now(),
            patient_count=estimated_patients,
            model_version=self.global_model_version,
            privacy_budget=self.privacy_epsilon,
            status='active'
        )

        self.registered_sites[site_id] = site_info
        self.active_sites[site_id] = site_info

        logger.info(f"Registered site: {site_name} ({location}) with ID: {site_id}")
        return site_id

    def site_heartbeat(self, site_id: str, status_update: Dict) -> bool:
        """
        Process heartbeat from a site with status updates.
        """
        if site_id not in self.registered_sites:
            logger.warning(f"Heartbeat from unregistered site: {site_id}")
            return False

        site = self.registered_sites[site_id]
        site.last_seen = datetime.now()
        site.patient_count = status_update.get('patient_count', site.patient_count)
        site.status = status_update.get('status', site.status)

        # Update active sites list
        if site.status == 'active':
            self.active_sites[site_id] = site
        elif site_id in self.active_sites:
            del self.active_sites[site_id]

        return True

    def can_start_federation_round(self) -> Tuple[bool, str]:
        """
        Check if conditions are met to start a new federation round.
        """
        if self.current_round and self.current_round.status in ['preparing', 'training', 'aggregating']:
            return False, "Federation round already in progress"

        active_count = len(self.active_sites)
        if active_count < self.min_sites:
            return False, f"Insufficient active sites: {active_count} < {self.min_sites}"

        # Check privacy budgets
        sites_with_budget = [s for s in self.active_sites.values() 
                           if s.privacy_budget > 0.1]
        if len(sites_with_budget) < self.min_sites:
            return False, "Insufficient privacy budget across sites"

        return True, "Ready for federation round"

    def start_federation_round(self, target_sites: Optional[int] = None) -> str:
        """
        Start a new federation training round.
        """
        can_start, reason = self.can_start_federation_round()
        if not can_start:
            raise ValueError(f"Cannot start federation round: {reason}")

        round_id = f"round_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Select participating sites
        available_sites = list(self.active_sites.keys())
        if target_sites:
            target_sites = min(target_sites, len(available_sites), self.max_sites)
        else:
            target_sites = min(len(available_sites), self.max_sites)

        # Prioritize sites with more patients and privacy budget
        site_scores = []
        for site_id in available_sites:
            site = self.active_sites[site_id]
            score = site.patient_count * site.privacy_budget
            site_scores.append((site_id, score))

        site_scores.sort(key=lambda x: x[1], reverse=True)
        participating_sites = [s[0] for s in site_scores[:target_sites]]

        self.current_round = FederationRound(
            round_id=round_id,
            start_time=datetime.now(),
            participating_sites=participating_sites,
            target_sites=target_sites,
            min_sites=self.min_sites,
            privacy_epsilon=self.privacy_epsilon / len(participating_sites),  # Split budget
            convergence_threshold=self.convergence_threshold,
            status='preparing'
        )

        self.model_updates[round_id] = []

        logger.info(f"Started federation round {round_id} with {len(participating_sites)} sites")
        return round_id

    def get_training_config(self, site_id: str, round_id: str) -> Dict:
        """
        Provide training configuration for a participating site.
        """
        if not self.current_round or self.current_round.round_id != round_id:
            raise ValueError("Invalid round ID or no active round")

        if site_id not in self.current_round.participating_sites:
            raise ValueError("Site not participating in current round")

        config = {
            'round_id': round_id,
            'global_model_version': self.global_model_version,
            'privacy_epsilon': self.current_round.privacy_epsilon,
            'training_epochs': 5,
            'batch_size': 32,
            'learning_rate': 0.001,
            'convergence_threshold': self.convergence_threshold,
            'clinical_metrics_required': [
                'patient_satisfaction',
                'symptom_improvement',
                'therapy_adherence',
                'adverse_events'
            ]
        }

        return config

    def submit_model_update(self, site_id: str, round_id: str, 
                          encrypted_weights: bytes, sample_count: int,
                          privacy_spent: float, validation_loss: float,
                          clinical_metrics: Dict) -> bool:
        """
        Receive encrypted model update from a site.
        """
        if not self.current_round or self.current_round.round_id != round_id:
            logger.error(f"Invalid round ID: {round_id}")
            return False

        if site_id not in self.current_round.participating_sites:
            logger.error(f"Site {site_id} not participating in round {round_id}")
            return False

        # Validate privacy budget
        site = self.registered_sites[site_id]
        if site.privacy_budget < privacy_spent:
            logger.error(f"Insufficient privacy budget for site {site_id}")
            return False

        # Store the update
        update = ModelUpdate(
            site_id=site_id,
            round_id=round_id,
            encrypted_weights=encrypted_weights,
            sample_count=sample_count,
            privacy_spent=privacy_spent,
            validation_loss=validation_loss,
            clinical_metrics=clinical_metrics,
            timestamp=datetime.now()
        )

        self.model_updates[round_id].append(update)

        # Update site's privacy budget
        site.privacy_budget -= privacy_spent

        logger.info(f"Received model update from site {site_id} for round {round_id}")

        # Check if we have enough updates to proceed
        if len(self.model_updates[round_id]) >= self.current_round.min_sites:
            self._try_aggregate_models(round_id)

        return True

    def _try_aggregate_models(self, round_id: str):
        """
        Attempt to aggregate model updates if conditions are met.
        """
        updates = self.model_updates[round_id]

        if len(updates) < self.current_round.min_sites:
            return

        # Wait a bit more for additional updates
        if len(updates) < self.current_round.target_sites:
            time_elapsed = datetime.now() - self.current_round.start_time
            if time_elapsed < timedelta(minutes=30):  # Wait up to 30 minutes
                return

        logger.info(f"Starting aggregation for round {round_id} with {len(updates)} updates")
        self.current_round.status = 'aggregating'

        try:
            # Perform secure aggregation
            aggregated_weights = self._secure_aggregate(updates)

            # Validate convergence
            convergence_achieved = self._check_convergence(updates)

            # Update global model
            self.aggregated_weights = aggregated_weights
            self.global_model_version = f"{float(self.global_model_version) + 0.1:.1f}"
            self.global_model_hash = hashlib.sha256(str(aggregated_weights).encode()).hexdigest()[:16]

            # Update metrics
            self._update_federation_metrics(updates, convergence_achieved)

            # Complete the round
            self.current_round.status = 'completed'
            self.round_history.append(self.current_round)

            logger.info(f"Federation round {round_id} completed successfully")

        except Exception as e:
            logger.error(f"Aggregation failed for round {round_id}: {e}")
            self.current_round.status = 'failed'
            self.round_history.append(self.current_round)

    def _secure_aggregate(self, updates: List[ModelUpdate]) -> np.ndarray:
        """
        Perform secure aggregation of model updates.
        Uses weighted averaging based on sample counts.
        """
        # Decrypt weights (in real implementation, use homomorphic encryption)
        decrypted_weights = []
        sample_counts = []

        for update in updates:
            # Simulate decryption (replace with actual secure aggregation)
            weights_json = self.cipher_suite.decrypt(update.encrypted_weights).decode()
            weights = np.array(json.loads(weights_json))
            decrypted_weights.append(weights)
            sample_counts.append(update.sample_count)

        # Weighted average
        total_samples = sum(sample_counts)
        aggregated = np.zeros_like(decrypted_weights[0])

        for weights, count in zip(decrypted_weights, sample_counts):
            weight = count / total_samples
            aggregated += weight * weights

        return aggregated

    def _check_convergence(self, updates: List[ModelUpdate]) -> bool:
        """
        Check if the federation round has achieved convergence.
        """
        if len(updates) < 2:
            return False

        # Check validation loss convergence
        losses = [update.validation_loss for update in updates]
        loss_std = np.std(losses)

        return loss_std < self.convergence_threshold

    def _update_federation_metrics(self, updates: List[ModelUpdate], converged: bool):
        """
        Update federation performance metrics.
        """
        self.federation_metrics['total_rounds'] += 1
        if converged:
            self.federation_metrics['successful_rounds'] += 1

        self.federation_metrics['total_sites_trained'] += len(updates)

        # Calculate clinical improvement
        clinical_scores = []
        for update in updates:
            if 'patient_satisfaction' in update.clinical_metrics:
                clinical_scores.append(update.clinical_metrics['patient_satisfaction'])

        if clinical_scores:
            avg_clinical = np.mean(clinical_scores)
            self.federation_metrics['clinical_improvement'] = avg_clinical

    def get_global_model_info(self) -> Dict:
        """
        Get information about the current global model.
        """
        return {
            'version': self.global_model_version,
            'hash': self.global_model_hash,
            'last_updated': self.current_round.start_time if self.current_round else None,
            'participating_sites': len(self.active_sites),
            'total_rounds': self.federation_metrics['total_rounds'],
            'success_rate': (self.federation_metrics['successful_rounds'] / 
                           max(1, self.federation_metrics['total_rounds'])),
            'clinical_improvement': self.federation_metrics['clinical_improvement']
        }

    def get_federation_status(self) -> Dict:
        """
        Get current federation status and metrics.
        """
        return {
            'coordinator_status': 'active',
            'registered_sites': len(self.registered_sites),
            'active_sites': len(self.active_sites),
            'current_round': asdict(self.current_round) if self.current_round else None,
            'global_model': self.get_global_model_info(),
            'metrics': self.federation_metrics,
            'privacy_budget_remaining': sum(s.privacy_budget for s in self.active_sites.values())
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize coordinator
    coordinator = FederationCoordinator(min_sites=2, max_sites=5)

    # Register some test sites
    site1 = coordinator.register_site("Mayo Clinic", "Rochester, MN", 1000)
    site2 = coordinator.register_site("Johns Hopkins", "Baltimore, MD", 800)
    site3 = coordinator.register_site("UCSF Medical", "San Francisco, CA", 600)

    print("Federation Coordinator initialized with test sites")
    print(f"Status: {coordinator.get_federation_status()}")
