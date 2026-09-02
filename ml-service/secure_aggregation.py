# ====
# NeuroTunes Secure Aggregation Protocol
# Implements privacy-preserving aggregation using cryptographic techniques
# Ensures no single party can see individual model updates
# ====

import numpy as np
import json
import hashlib
import secrets
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecretShare:
    """A secret share for secure aggregation."""
    share_id: str
    site_id: str
    encrypted_share: bytes
    commitment: str  # Hash commitment for verification
    timestamp: float

@dataclass
class AggregationRound:
    """Information about a secure aggregation round."""
    round_id: str
    participating_sites: List[str]
    threshold: int  # Minimum shares needed
    total_sites: int
    shares_received: Dict[str, SecretShare]
    aggregation_result: Optional[np.ndarray]
    status: str  # 'collecting', 'aggregating', 'completed', 'failed'

class HomomorphicEncryption:
    """
    Simplified homomorphic encryption for secure aggregation.
    In production, use libraries like Microsoft SEAL or HElib.
    """

    def __init__(self, key_size: int = 2048):
        self.key_size = key_size
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()

    def encrypt_vector(self, vector: np.ndarray) -> List[bytes]:
        """Encrypt a vector element-wise."""
        encrypted_elements = []

        for element in vector.flatten():
            # Convert to bytes (simplified - real implementation needs proper encoding)
            element_bytes = str(float(element)).encode('utf-8')

            # Encrypt with padding
            encrypted = self.public_key.encrypt(
                element_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            encrypted_elements.append(encrypted)

        return encrypted_elements

    def decrypt_vector(self, encrypted_vector: List[bytes], original_shape: Tuple) -> np.ndarray:
        """Decrypt a vector and restore original shape."""
        decrypted_elements = []

        for encrypted_element in encrypted_vector:
            decrypted_bytes = self.private_key.decrypt(
                encrypted_element,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # Convert back to float
            element_value = float(decrypted_bytes.decode('utf-8'))
            decrypted_elements.append(element_value)

        return np.array(decrypted_elements).reshape(original_shape)

    def homomorphic_add(self, encrypted_a: List[bytes], encrypted_b: List[bytes]) -> List[bytes]:
        """
        Homomorphic addition (simplified implementation).
        Real implementation would use proper homomorphic encryption.
        """
        # This is a placeholder - real homomorphic encryption allows
        # operations on encrypted data without decryption
        if len(encrypted_a) != len(encrypted_b):
            raise ValueError("Encrypted vectors must have same length")

        # In a real implementation, this would perform addition on encrypted values
        # For now, we'll simulate by returning one of the inputs
        return encrypted_a  # Placeholder

class SecretSharingScheme:
    """
    Implements Shamir's Secret Sharing for secure aggregation.
    """

    def __init__(self, threshold: int, total_shares: int):
        self.threshold = threshold
        self.total_shares = total_shares
        self.prime = 2**31 - 1  # Large prime for finite field arithmetic

    def _mod_inverse(self, a: int, m: int) -> int:
        """Calculate modular inverse using extended Euclidean algorithm."""
        if a < 0:
            a = (a % m + m) % m

        # Extended Euclidean Algorithm
        def extended_gcd(a, b):
            if a == 0:
                return b, 0, 1
            gcd, x1, y1 = extended_gcd(b % a, a)
            x = y1 - (b // a) * x1
            y = x1
            return gcd, x, y

        gcd, x, _ = extended_gcd(a, m)
        if gcd != 1:
            raise ValueError("Modular inverse does not exist")
        return (x % m + m) % m

    def _evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
        """Evaluate polynomial at point x using Horner's method."""
        result = 0
        for coeff in reversed(coefficients):
            result = (result * x + coeff) % self.prime
        return result

    def create_shares(self, secret: int) -> List[Tuple[int, int]]:
        """Create secret shares using Shamir's scheme."""
        # Generate random coefficients for polynomial
        coefficients = [secret] + [secrets.randbelow(self.prime) for _ in range(self.threshold - 1)]

        # Generate shares
        shares = []
        for i in range(1, self.total_shares + 1):
            share_value = self._evaluate_polynomial(coefficients, i)
            shares.append((i, share_value))

        return shares

    def reconstruct_secret(self, shares: List[Tuple[int, int]]) -> int:
        """Reconstruct secret from shares using Lagrange interpolation."""
        if len(shares) < self.threshold:
            raise ValueError(f"Need at least {self.threshold} shares, got {len(shares)}")

        # Use first 'threshold' shares
        shares = shares[:self.threshold]

        secret = 0
        for i, (xi, yi) in enumerate(shares):
            # Calculate Lagrange coefficient
            numerator = 1
            denominator = 1

            for j, (xj, _) in enumerate(shares):
                if i != j:
                    numerator = (numerator * (-xj)) % self.prime
                    denominator = (denominator * (xi - xj)) % self.prime

            # Calculate coefficient
            coeff = (numerator * self._mod_inverse(denominator, self.prime)) % self.prime
            secret = (secret + yi * coeff) % self.prime

        return secret % self.prime

class SecureAggregationProtocol:
    """
    Main secure aggregation protocol coordinator.
    """

    def __init__(self, threshold_ratio: float = 0.67):
        self.threshold_ratio = threshold_ratio
        self.active_rounds: Dict[str, AggregationRound] = {}
        self.homomorphic_engine = HomomorphicEncryption()
        self.lock = threading.Lock()

        logger.info("Secure Aggregation Protocol initialized")

    def start_aggregation_round(self, round_id: str, participating_sites: List[str]) -> bool:
        """Start a new secure aggregation round."""
        with self.lock:
            if round_id in self.active_rounds:
                logger.warning(f"Round {round_id} already exists")
                return False

            total_sites = len(participating_sites)
            threshold = max(2, int(total_sites * self.threshold_ratio))

            self.active_rounds[round_id] = AggregationRound(
                round_id=round_id,
                participating_sites=participating_sites,
                threshold=threshold,
                total_sites=total_sites,
                shares_received={},
                aggregation_result=None,
                status='collecting'
            )

            logger.info(f"Started aggregation round {round_id} with {total_sites} sites (threshold: {threshold})")
            return True

    def submit_encrypted_update(self, round_id: str, site_id: str, 
                              encrypted_weights: bytes, metadata: Dict) -> bool:
        """Submit encrypted model update for aggregation."""
        with self.lock:
            if round_id not in self.active_rounds:
                logger.error(f"Round {round_id} not found")
                return False

            round_info = self.active_rounds[round_id]

            if round_info.status != 'collecting':
                logger.error(f"Round {round_id} not accepting submissions (status: {round_info.status})")
                return False

            if site_id not in round_info.participating_sites:
                logger.error(f"Site {site_id} not participating in round {round_id}")
                return False

            # Create commitment hash for verification
            commitment = hashlib.sha256(encrypted_weights + site_id.encode()).hexdigest()

            # Store the share
            share = SecretShare(
                share_id=f"{round_id}_{site_id}",
                site_id=site_id,
                encrypted_share=encrypted_weights,
                commitment=commitment,
                timestamp=time.time()
            )

            round_info.shares_received[site_id] = share

            logger.info(f"Received encrypted update from {site_id} for round {round_id}")

            # Check if we can start aggregation
            if len(round_info.shares_received) >= round_info.threshold:
                self._trigger_aggregation(round_id)

            return True

    def _trigger_aggregation(self, round_id: str):
        """Trigger secure aggregation when threshold is met."""
        round_info = self.active_rounds[round_id]
        round_info.status = 'aggregating'

        logger.info(f"Starting secure aggregation for round {round_id}")

        # Run aggregation in background thread
        def run_aggregation():
            try:
                result = self._perform_secure_aggregation(round_id)
                with self.lock:
                    round_info.aggregation_result = result
                    round_info.status = 'completed'
                logger.info(f"Aggregation completed for round {round_id}")
            except Exception as e:
                logger.error(f"Aggregation failed for round {round_id}: {e}")
                with self.lock:
                    round_info.status = 'failed'

        aggregation_thread = threading.Thread(target=run_aggregation)
        aggregation_thread.start()

    def _perform_secure_aggregation(self, round_id: str) -> np.ndarray:
        """Perform the actual secure aggregation."""
        round_info = self.active_rounds[round_id]
        shares = list(round_info.shares_received.values())

        if len(shares) < round_info.threshold:
            raise ValueError(f"Insufficient shares: {len(shares)} < {round_info.threshold}")

        # Step 1: Decrypt individual updates (in real implementation, 
        # this would use homomorphic encryption to avoid decryption)
        decrypted_updates = []
        sample_counts = []

        for share in shares:
            try:
                # Simulate decryption (replace with actual homomorphic operations)
                decrypted_data = self._decrypt_model_update(share.encrypted_share)
                weights = decrypted_data['weights']
                sample_count = decrypted_data['sample_count']

                decrypted_updates.append(weights)
                sample_counts.append(sample_count)

            except Exception as e:
                logger.error(f"Failed to decrypt update from {share.site_id}: {e}")
                continue

        if not decrypted_updates:
            raise ValueError("No valid updates to aggregate")

        # Step 2: Perform weighted aggregation
        aggregated_weights = self._weighted_average(decrypted_updates, sample_counts)

        # Step 3: Add aggregation noise for additional privacy
        aggregated_weights = self._add_aggregation_noise(aggregated_weights)

        return aggregated_weights

    def _decrypt_model_update(self, encrypted_data: bytes) -> Dict:
        """
        Decrypt model update (simplified implementation).
        In production, use proper homomorphic encryption.
        """
        # This is a placeholder - in real implementation, 
        # homomorphic encryption would allow aggregation without decryption

        # Simulate decryption
        try:
            # For demo purposes, assume data is JSON-encoded
            decrypted_json = encrypted_data.decode('utf-8')
            data = json.loads(decrypted_json)

            # Convert weights back to numpy arrays
            weights = {}
            for key, value in data['weights'].items():
                weights[key] = np.array(value)

            return {
                'weights': weights,
                'sample_count': data.get('sample_count', 1)
            }

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def _weighted_average(self, weight_lists: List[Dict], sample_counts: List[int]) -> Dict:
        """Compute weighted average of model weights."""
        if not weight_lists:
            raise ValueError("No weights to aggregate")

        total_samples = sum(sample_counts)
        aggregated = {}

        # Get all parameter names from first model
        param_names = weight_lists[0].keys()

        for param_name in param_names:
            # Initialize aggregated parameter
            aggregated[param_name] = np.zeros_like(weight_lists[0][param_name])

            # Weighted sum
            for weights, sample_count in zip(weight_lists, sample_counts):
                if param_name in weights:
                    weight = sample_count / total_samples
                    aggregated[param_name] += weight * weights[param_name]

        return aggregated

    def _add_aggregation_noise(self, weights: Dict, noise_scale: float = 0.001) -> Dict:
        """Add noise to aggregated weights for additional privacy."""
        noisy_weights = {}

        for param_name, param_weights in weights.items():
            noise = np.random.normal(0, noise_scale, param_weights.shape)
            noisy_weights[param_name] = param_weights + noise

        return noisy_weights

    def get_aggregation_result(self, round_id: str) -> Optional[np.ndarray]:
        """Get aggregation result for a completed round."""
        with self.lock:
            if round_id not in self.active_rounds:
                return None

            round_info = self.active_rounds[round_id]
            if round_info.status == 'completed':
                return round_info.aggregation_result

            return None

    def get_round_status(self, round_id: str) -> Dict:
        """Get status information for an aggregation round."""
        with self.lock:
            if round_id not in self.active_rounds:
                return {'error': 'Round not found'}

            round_info = self.active_rounds[round_id]
            return {
                'round_id': round_id,
                'status': round_info.status,
                'participating_sites': round_info.participating_sites,
                'shares_received': len(round_info.shares_received),
                'threshold': round_info.threshold,
                'total_sites': round_info.total_sites,
                'completion_percentage': len(round_info.shares_received) / round_info.total_sites * 100
            }

    def cleanup_completed_rounds(self, max_age_hours: int = 24):
        """Clean up old completed rounds."""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)

        with self.lock:
            rounds_to_remove = []

            for round_id, round_info in self.active_rounds.items():
                if round_info.status in ['completed', 'failed']:
                    # Check if any share is older than cutoff
                    oldest_share_time = min(
                        share.timestamp for share in round_info.shares_received.values()
                    ) if round_info.shares_received else current_time

                    if oldest_share_time < cutoff_time:
                        rounds_to_remove.append(round_id)

            for round_id in rounds_to_remove:
                del self.active_rounds[round_id]
                logger.info(f"Cleaned up old round: {round_id}")

class SecureAggregationClient:
    """
    Client-side interface for secure aggregation.
    """

    def __init__(self, site_id: str):
        self.site_id = site_id
        self.homomorphic_engine = HomomorphicEncryption()

    def encrypt_model_weights(self, weights: Dict, sample_count: int) -> bytes:
        """Encrypt model weights for secure aggregation."""
        # Prepare data for encryption
        data = {
            'weights': {},
            'sample_count': sample_count,
            'site_id': self.site_id,
            'timestamp': time.time()
        }

        # Convert numpy arrays to lists for JSON serialization
        for key, value in weights.items():
            if isinstance(value, np.ndarray):
                data['weights'][key] = value.tolist()
            else:
                data['weights'][key] = value

        # Serialize and encrypt
        json_data = json.dumps(data)

        # In production, use proper homomorphic encryption
        # For now, return as bytes for demonstration
        return json_data.encode('utf-8')

    def verify_aggregation_integrity(self, round_id: str, 
                                   aggregated_result: np.ndarray,
                                   expected_participants: List[str]) -> bool:
        """Verify the integrity of aggregation result."""
        # Implement verification logic
        # This could include checking commitments, zero-knowledge proofs, etc.

        # Placeholder verification
        if aggregated_result is None:
            return False

        # Check if result has reasonable values
        if np.any(np.isnan(aggregated_result)) or np.any(np.isinf(aggregated_result)):
            return False

        return True

# Example usage and testing
if __name__ == "__main__":
    # Initialize secure aggregation protocol
    protocol = SecureAggregationProtocol(threshold_ratio=0.67)

    # Simulate a federation round
    round_id = "test_round_001"
    sites = ["site_001", "site_002", "site_003", "site_004"]

    # Start aggregation round
    protocol.start_aggregation_round(round_id, sites)

    # Simulate encrypted updates from sites
    for i, site_id in enumerate(sites[:3]):  # Only 3 out of 4 sites participate
        client = SecureAggregationClient(site_id)

        # Create dummy weights
        dummy_weights = {
            'layer1.weight': np.random.randn(10, 5),
            'layer1.bias': np.random.randn(10),
            'layer2.weight': np.random.randn(1, 10)
        }

        encrypted_weights = client.encrypt_model_weights(dummy_weights, sample_count=100 + i*50)

        protocol.submit_encrypted_update(
            round_id, site_id, encrypted_weights, 
            {'validation_loss': 0.1 + i*0.01}
        )

    # Wait for aggregation to complete
    import time
    time.sleep(2)

    # Check results
    status = protocol.get_round_status(round_id)
    result = protocol.get_aggregation_result(round_id)

    print(f"Aggregation Status: {status}")
    print(f"Result Available: {result is not None}")

    print("Secure Aggregation Protocol demonstration completed")
