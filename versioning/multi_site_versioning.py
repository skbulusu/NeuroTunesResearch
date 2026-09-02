# ====
# NeuroTunes Multi-Site Model Versioning System (CORRECTED VERSION)
# Handles version control across healthcare sites with distributed rollback
# ====

import json
import logging
import hashlib
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import uuid
import mysql.connector
from mysql.connector import pooling
import os
import pickle
import threading
from pathlib import Path
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ModelVersion:
    """Represents a model version with metadata."""
    version_id: str
    site_id: str
    version_number: str  # e.g., "1.2.3"
    parent_version: Optional[str]
    model_hash: str
    model_weights_path: str
    performance_metrics: Dict
    clinical_metrics: Dict
    created_at: datetime
    created_by: str
    status: str  # 'active', 'deprecated', 'rollback_candidate'
    compatibility_info: Dict
    deployment_sites: List[str]

@dataclass
class VersionCompatibility:
    """Compatibility information between model versions."""
    version_a: str
    version_b: str
    compatibility_score: float  # 0.0 to 1.0
    breaking_changes: List[str]
    migration_required: bool
    tested_combinations: List[str]

@dataclass
class RollbackPlan:
    """Plan for rolling back across multiple sites."""
    rollback_id: str
    target_version: str
    affected_sites: List[str]
    rollback_reason: str
    estimated_duration: int  # minutes
    risk_assessment: str
    approval_required: bool
    created_at: datetime
    status: str  # 'planned', 'approved', 'executing', 'completed', 'failed'

class MultiSiteVersionManager:
    """
    Manages model versions across multiple healthcare sites.
    Provides distributed version control with rollback capabilities.
    """

    def __init__(self, base_model_path: str = "models/versions"):
        # Input validation
        if not base_model_path:
            raise ValueError("base_model_path cannot be empty")

        self.base_model_path = Path(base_model_path)
        self.base_model_path.mkdir(parents=True, exist_ok=True)

        # Thread safety
        self._lock = threading.RLock()

        # Database connection pool
        self.db_pool = self._setup_database_pool()

        # Version tracking (thread-safe)
        self.site_versions: Dict[str, str] = {}  # site_id -> current_version
        self.version_registry: Dict[str, ModelVersion] = {}
        self.compatibility_matrix: Dict[Tuple[str, str], VersionCompatibility] = {}

        # Rollback management
        self.active_rollbacks: Dict[str, RollbackPlan] = {}

        # Initialize database tables and load existing versions
        self._create_versioning_tables()
        self._load_existing_versions()

        logger.info("Multi-Site Version Manager initialized with connection pooling")

    def _setup_database_pool(self):
        """Setup database connection pool for better reliability."""
        try:
            config = {
                'host': os.getenv('dbHost', 'localhost'),
                'database': os.getenv('dbName', 'netraidb'),
                'user': os.getenv('dbUsername', 'root'),
                'password': os.getenv('dbPWD', ''),
                'port': int(os.getenv('MYSQL_PORT', 3306)),
                'pool_name': 'versioning_pool',
                'pool_size': 5,
                'pool_reset_session': True,
                'autocommit': False
            }

            pool = pooling.MySQLConnectionPool(**config)
            logger.info("Database connection pool established")
            return pool
        except Exception as e:
            logger.error(f"Database connection pool setup failed: {e}")
            return None

    def _get_db_connection(self):
        """Get a database connection from the pool with retry logic."""
        if not self.db_pool:
            return None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                connection = self.db_pool.get_connection()
                if connection.is_connected():
                    return connection
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    logger.error("All database connection attempts failed")
                    return None

    def _create_versioning_tables(self):
        """Create database tables for version management."""
        connection = self._get_db_connection()
        if not connection:
            logger.error("Cannot create tables - no database connection")
            return

        cursor = connection.cursor()
        try:
            # Model versions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS neurotunes_model_versions (
                    version_id VARCHAR(128) PRIMARY KEY,
                    site_id VARCHAR(64) NOT NULL,
                    version_number VARCHAR(32) NOT NULL,
                    parent_version VARCHAR(128),
                    model_hash VARCHAR(64) NOT NULL,
                    model_weights_path TEXT NOT NULL,
                    performance_metrics JSON,
                    clinical_metrics JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(128),
                    status ENUM('active', 'deprecated', 'rollback_candidate') DEFAULT 'active',
                    compatibility_info JSON,
                    deployment_sites JSON,
                    INDEX idx_site_version (site_id, version_number),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at),
                    INDEX idx_site_id (site_id)
                )
            """)

            # Version compatibility table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS neurotunes_version_compatibility (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version_a VARCHAR(128) NOT NULL,
                    version_b VARCHAR(128) NOT NULL,
                    compatibility_score DECIMAL(3,2) NOT NULL,
                    breaking_changes JSON,
                    migration_required BOOLEAN DEFAULT FALSE,
                    tested_combinations JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_compatibility (version_a, version_b),
                    INDEX idx_version_a (version_a),
                    INDEX idx_version_b (version_b),
                    INDEX idx_compatibility_score (compatibility_score)
                )
            """)

            # Rollback plans table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS neurotunes_rollback_plans (
                    rollback_id VARCHAR(128) PRIMARY KEY,
                    target_version VARCHAR(128) NOT NULL,
                    affected_sites JSON NOT NULL,
                    rollback_reason TEXT,
                    estimated_duration INT,
                    risk_assessment TEXT,
                    approval_required BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('planned', 'approved', 'executing', 'completed', 'failed') DEFAULT 'planned',
                    INDEX idx_target_version (target_version),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at)
                )
            """)

            # Site version tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS neurotunes_site_versions (
                    site_id VARCHAR(64) PRIMARY KEY,
                    current_version VARCHAR(128) NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    update_method VARCHAR(32),
                    INDEX idx_current_version (current_version),
                    INDEX idx_last_updated (last_updated)
                )
            """)

            connection.commit()
            logger.info("Version management tables created successfully")

        except Exception as e:
            logger.error(f"Error creating versioning tables: {e}")
            connection.rollback()
        finally:
            cursor.close()
            connection.close()

    def _load_existing_versions(self):
        """Load existing versions from database."""
        connection = self._get_db_connection()
        if not connection:
            return

        cursor = connection.cursor(dictionary=True)
        try:
            with self._lock:
                # Load model versions
                cursor.execute("SELECT * FROM neurotunes_model_versions ORDER BY created_at DESC")
                versions = cursor.fetchall()

                for version_data in versions:
                    try:
                        version = ModelVersion(
                            version_id=version_data['version_id'],
                            site_id=version_data['site_id'],
                            version_number=version_data['version_number'],
                            parent_version=version_data['parent_version'],
                            model_hash=version_data['model_hash'],
                            model_weights_path=version_data['model_weights_path'],
                            performance_metrics=json.loads(version_data['performance_metrics'] or '{}'),
                            clinical_metrics=json.loads(version_data['clinical_metrics'] or '{}'),
                            created_at=version_data['created_at'],
                            created_by=version_data['created_by'],
                            status=version_data['status'],
                            compatibility_info=json.loads(version_data['compatibility_info'] or '{}'),
                            deployment_sites=json.loads(version_data['deployment_sites'] or '[]')
                        )
                        self.version_registry[version.version_id] = version
                    except Exception as e:
                        logger.warning(f"Error loading version {version_data.get('version_id', 'unknown')}: {e}")

                # Load site current versions
                cursor.execute("SELECT * FROM neurotunes_site_versions")
                site_versions = cursor.fetchall()

                for site_version in site_versions:
                    self.site_versions[site_version['site_id']] = site_version['current_version']

                logger.info(f"Loaded {len(self.version_registry)} versions for {len(self.site_versions)} sites")

        except Exception as e:
            logger.error(f"Error loading existing versions: {e}")
        finally:
            cursor.close()
            connection.close()

    def create_new_version(self, 
                          site_id: str, 
                          model_weights: Any, 
                          performance_metrics: Dict,
                          clinical_metrics: Dict,
                          created_by: str,
                          parent_version: Optional[str] = None) -> str:
        """
        Create a new model version for a site with comprehensive validation.
        """
        # Input validation
        if not site_id or not site_id.strip():
            raise ValueError("site_id cannot be empty")
        if not created_by or not created_by.strip():
            raise ValueError("created_by cannot be empty")
        if not isinstance(performance_metrics, dict):
            raise ValueError("performance_metrics must be a dictionary")
        if not isinstance(clinical_metrics, dict):
            raise ValueError("clinical_metrics must be a dictionary")

        with self._lock:
            # Generate version number
            current_version = self.site_versions.get(site_id, "0.0.0")
            new_version_number = self._increment_version(current_version)

            # Generate unique version ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            version_id = f"{site_id}_{new_version_number}_{timestamp}_{uuid.uuid4().hex[:8]}"

            # Calculate model hash
            model_hash = self._calculate_model_hash(model_weights)

            # Save model weights
            model_weights_path = self.base_model_path / f"{version_id}.pkl"
            try:
                with open(model_weights_path, 'wb') as f:
                    pickle.dump(model_weights, f)
            except Exception as e:
                raise RuntimeError(f"Failed to save model weights: {e}")

            # Create version object
            version = ModelVersion(
                version_id=version_id,
                site_id=site_id,
                version_number=new_version_number,
                parent_version=parent_version or self.site_versions.get(site_id),
                model_hash=model_hash,
                model_weights_path=str(model_weights_path),
                performance_metrics=performance_metrics,
                clinical_metrics=clinical_metrics,
                created_at=datetime.now(),
                created_by=created_by,
                status='active',
                compatibility_info={},
                deployment_sites=[site_id]
            )

            # Save to database
            if not self._save_version_to_db(version):
                # Cleanup on failure
                if model_weights_path.exists():
                    model_weights_path.unlink()
                raise RuntimeError("Failed to save version to database")

            # Update registry and site tracking
            self.version_registry[version_id] = version
            self.site_versions[site_id] = version_id
            self._update_site_version(site_id, version_id, 'new_version')

            # Check compatibility with other versions (async to avoid blocking)
            threading.Thread(
                target=self._check_compatibility_with_existing_versions,
                args=(version,),
                daemon=True
            ).start()

            logger.info(f"Created new version {new_version_number} for site {site_id}: {version_id}")
            return version_id

    def _increment_version(self, current_version: str) -> str:
        """Increment version number (semantic versioning)."""
        try:
            parts = current_version.split('.')
            if len(parts) != 3:
                return "1.0.1"
            major, minor, patch = map(int, parts)
            return f"{major}.{minor}.{patch + 1}"
        except (ValueError, AttributeError):
            return "1.0.1"

    def _calculate_model_hash(self, model_weights: Any) -> str:
        """Calculate hash of model weights for integrity checking."""
        try:
            if hasattr(model_weights, 'state_dict'):
                # PyTorch model
                weights_str = str(sorted(model_weights.state_dict().items()))
            elif isinstance(model_weights, dict):
                weights_str = str(sorted(model_weights.items()))
            elif hasattr(model_weights, '__dict__'):
                weights_str = str(sorted(model_weights.__dict__.items()))
            else:
                weights_str = str(model_weights)

            return hashlib.sha256(weights_str.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.warning(f"Error calculating model hash: {e}")
            return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()

    def _save_version_to_db(self, version: ModelVersion) -> bool:
        """Save version to database with error handling."""
        connection = self._get_db_connection()
        if not connection:
            return False

        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO neurotunes_model_versions 
                (version_id, site_id, version_number, parent_version, model_hash, 
                 model_weights_path, performance_metrics, clinical_metrics, 
                 created_by, status, compatibility_info, deployment_sites)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                version.version_id,
                version.site_id,
                version.version_number,
                version.parent_version,
                version.model_hash,
                version.model_weights_path,
                json.dumps(version.performance_metrics),
                json.dumps(version.clinical_metrics),
                version.created_by,
                version.status,
                json.dumps(version.compatibility_info),
                json.dumps(version.deployment_sites)
            ))
            connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving version to database: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()

    def _update_site_version(self, site_id: str, version_id: str, update_method: str) -> bool:
        """Update site's current version."""
        connection = self._get_db_connection()
        if not connection:
            return False

        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO neurotunes_site_versions (site_id, current_version, update_method)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    current_version = VALUES(current_version),
                    update_method = VALUES(update_method),
                    last_updated = CURRENT_TIMESTAMP
            """, (site_id, version_id, update_method))
            connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating site version: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()

    def _check_compatibility_with_existing_versions(self, new_version: ModelVersion):
        """Check compatibility of new version with existing versions."""
        try:
            with self._lock:
                for existing_version in self.version_registry.values():
                    if existing_version.version_id != new_version.version_id:
                        compatibility = self._calculate_compatibility(new_version, existing_version)
                        self._save_compatibility_to_db(compatibility)
                        self.compatibility_matrix[(new_version.version_id, existing_version.version_id)] = compatibility
        except Exception as e:
            logger.error(f"Error checking compatibility: {e}")

    def _calculate_compatibility(self, version_a: ModelVersion, version_b: ModelVersion) -> VersionCompatibility:
        """Calculate compatibility between two versions."""
        score = 1.0
        breaking_changes = []

        try:
            # Check performance degradation
            if version_a.performance_metrics and version_b.performance_metrics:
                perf_a = version_a.performance_metrics.get('validation_loss', 1.0)
                perf_b = version_b.performance_metrics.get('validation_loss', 1.0)

                if abs(perf_a - perf_b) > 0.1:
                    score -= 0.2
                    breaking_changes.append("Significant performance difference")

            # Check clinical metrics compatibility
            if version_a.clinical_metrics and version_b.clinical_metrics:
                clinical_a = version_a.clinical_metrics.get('patient_satisfaction', 0.5)
                clinical_b = version_b.clinical_metrics.get('patient_satisfaction', 0.5)

                if abs(clinical_a - clinical_b) > 0.15:
                    score -= 0.3
                    breaking_changes.append("Clinical effectiveness difference")

            # Check version number compatibility (semantic versioning)
            version_diff = self._compare_version_numbers(version_a.version_number, version_b.version_number)
            if version_diff['major_diff'] > 0:
                score -= 0.4
                breaking_changes.append("Major version difference")

            migration_required = score < 0.7 or len(breaking_changes) > 0

        except Exception as e:
            logger.warning(f"Error calculating compatibility: {e}")
            score = 0.5
            breaking_changes.append("Compatibility calculation error")
            migration_required = True

        return VersionCompatibility(
            version_a=version_a.version_id,
            version_b=version_b.version_id,
            compatibility_score=max(0.0, score),
            breaking_changes=breaking_changes,
            migration_required=migration_required,
            tested_combinations=[]
        )

    def _compare_version_numbers(self, version_a: str, version_b: str) -> Dict:
        """Compare two version numbers."""
        try:
            a_parts = list(map(int, version_a.split('.')))
            b_parts = list(map(int, version_b.split('.')))

            # Pad shorter version with zeros
            while len(a_parts) < 3:
                a_parts.append(0)
            while len(b_parts) < 3:
                b_parts.append(0)

            return {
                'major_diff': abs(a_parts[0] - b_parts[0]),
                'minor_diff': abs(a_parts[1] - b_parts[1]),
                'patch_diff': abs(a_parts[2] - b_parts[2])
            }
        except (ValueError, IndexError):
            return {'major_diff': 1, 'minor_diff': 0, 'patch_diff': 0}

    def _save_compatibility_to_db(self, compatibility: VersionCompatibility) -> bool:
        """Save compatibility information to database."""
        connection = self._get_db_connection()
        if not connection:
            return False

        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO neurotunes_version_compatibility 
                (version_a, version_b, compatibility_score, breaking_changes, 
                 migration_required, tested_combinations)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    compatibility_score = VALUES(compatibility_score),
                    breaking_changes = VALUES(breaking_changes),
                    migration_required = VALUES(migration_required),
                    tested_combinations = VALUES(tested_combinations)
            """, (
                compatibility.version_a,
                compatibility.version_b,
                compatibility.compatibility_score,
                json.dumps(compatibility.breaking_changes),
                compatibility.migration_required,
                json.dumps(compatibility.tested_combinations)
            ))
            connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving compatibility to database: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()

    def get_site_version_info(self, site_id: str) -> Dict:
        """Get version information for a specific site."""
        if not site_id or not site_id.strip():
            return {"error": "Invalid site_id"}

        with self._lock:
            current_version_id = self.site_versions.get(site_id)
            if not current_version_id:
                return {"error": "Site not found"}

            version = self.version_registry.get(current_version_id)
            if not version:
                return {"error": "Version not found"}

            return {
                "site_id": site_id,
                "current_version": asdict(version),
                "available_versions": self._get_compatible_versions(site_id),
                "rollback_candidates": self._get_rollback_candidates(site_id)
            }

    def _get_compatible_versions(self, site_id: str) -> List[Dict]:
        """Get versions compatible with the site's current version."""
        current_version_id = self.site_versions.get(site_id)
        if not current_version_id:
            return []

        compatible_versions = []
        for version_id, version in self.version_registry.items():
            if version_id != current_version_id:
                compatibility_key = (current_version_id, version_id)
                compatibility = self.compatibility_matrix.get(compatibility_key)

                if compatibility and compatibility.compatibility_score >= 0.7:
                    compatible_versions.append({
                        "version_id": version_id,
                        "version_number": version.version_number,
                        "compatibility_score": compatibility.compatibility_score,
                        "migration_required": compatibility.migration_required
                    })

        return sorted(compatible_versions, key=lambda x: x['compatibility_score'], reverse=True)

    def _get_rollback_candidates(self, site_id: str) -> List[Dict]:
        """Get potential rollback candidates for a site."""
        current_version_id = self.site_versions.get(site_id)
        if not current_version_id:
            return []

        current_version = self.version_registry.get(current_version_id)
        if not current_version:
            return []

        candidates = []

        # Add parent version as primary rollback candidate
        if current_version.parent_version and current_version.parent_version in self.version_registry:
            parent_version = self.version_registry[current_version.parent_version]
            candidates.append({
                "version_id": parent_version.version_id,
                "version_number": parent_version.version_number,
                "rollback_type": "parent",
                "risk_level": "low"
            })

        # Add other stable versions
        for version in self.version_registry.values():
            if (version.site_id == site_id and 
                version.version_id != current_version_id and
                version.status == 'active' and
                version.version_id != current_version.parent_version):
                candidates.append({
                    "version_id": version.version_id,
                    "version_number": version.version_number,
                    "rollback_type": "stable",
                    "risk_level": "medium"
                })

        return candidates[:5]  # Limit to top 5 candidates

    def plan_distributed_rollback(self, 
                                 target_version_id: str, 
                                 affected_sites: List[str],
                                 rollback_reason: str,
                                 created_by: str) -> str:
        """Plan a rollback across multiple sites."""
        # Input validation
        if not target_version_id or target_version_id not in self.version_registry:
            raise ValueError(f"Target version {target_version_id} not found")
        if not affected_sites or not all(isinstance(site, str) and site.strip() for site in affected_sites):
            raise ValueError("affected_sites must be a non-empty list of valid site IDs")
        if not rollback_reason or not rollback_reason.strip():
            raise ValueError("rollback_reason cannot be empty")
        if not created_by or not created_by.strip():
            raise ValueError("created_by cannot be empty")

        rollback_id = f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Assess rollback risk
        risk_assessment = self._assess_rollback_risk(target_version_id, affected_sites)

        # Estimate duration
        estimated_duration = len(affected_sites) * 10  # 10 minutes per site

        rollback_plan = RollbackPlan(
            rollback_id=rollback_id,
            target_version=target_version_id,
            affected_sites=affected_sites,
            rollback_reason=rollback_reason,
            estimated_duration=estimated_duration,
            risk_assessment=risk_assessment,
            approval_required=risk_assessment != "low",
            created_at=datetime.now(),
            status='planned'
        )

        # Save to database
        if not self._save_rollback_plan_to_db(rollback_plan):
            raise RuntimeError("Failed to save rollback plan to database")

        with self._lock:
            self.active_rollbacks[rollback_id] = rollback_plan

        logger.info(f"Created rollback plan {rollback_id} for {len(affected_sites)} sites")
        return rollback_id

    def _assess_rollback_risk(self, target_version_id: str, affected_sites: List[str]) -> str:
        """Assess risk level of a rollback operation."""
        target_version = self.version_registry[target_version_id]

        # Check age of target version
        age_days = (datetime.now() - target_version.created_at).days
        if age_days > 30:
            return "high"

        # Check number of affected sites
        if len(affected_sites) > 5:
            return "high"
        elif len(affected_sites) > 2:
            return "medium"

        # Check compatibility scores
        low_compatibility_count = 0
        for site_id in affected_sites:
            current_version_id = self.site_versions.get(site_id)
            if current_version_id:
                compatibility_key = (current_version_id, target_version_id)
                compatibility = self.compatibility_matrix.get(compatibility_key)
                if compatibility and compatibility.compatibility_score < 0.8:
                    low_compatibility_count += 1

        if low_compatibility_count > len(affected_sites) // 2:
            return "high"
        elif low_compatibility_count > 0:
            return "medium"

        return "low"

    def _save_rollback_plan_to_db(self, rollback_plan: RollbackPlan) -> bool:
        """Save rollback plan to database."""
        connection = self._get_db_connection()
        if not connection:
            return False

        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO neurotunes_rollback_plans 
                (rollback_id, target_version, affected_sites, rollback_reason,
                 estimated_duration, risk_assessment, approval_required, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                rollback_plan.rollback_id,
                rollback_plan.target_version,
                json.dumps(rollback_plan.affected_sites),
                rollback_plan.rollback_reason,
                rollback_plan.estimated_duration,
                rollback_plan.risk_assessment,
                rollback_plan.approval_required,
                rollback_plan.status
            ))
            connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving rollback plan to database: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()

    def execute_distributed_rollback(self, rollback_id: str) -> Dict:
        """Execute a planned rollback across multiple sites."""
        if rollback_id not in self.active_rollbacks:
            return {"error": "Rollback plan not found"}

        rollback_plan = self.active_rollbacks[rollback_id]

        if rollback_plan.approval_required and rollback_plan.status != 'approved':
            return {"error": "Rollback requires approval"}

        rollback_plan.status = 'executing'
        self._update_rollback_status(rollback_id, 'executing')

        results = {
            "rollback_id": rollback_id,
            "target_version": rollback_plan.target_version,
            "site_results": {},
            "overall_status": "executing"
        }

        # Execute rollback for each site
        for site_id in rollback_plan.affected_sites:
            try:
                site_result = self._rollback_site_version(site_id, rollback_plan.target_version)
                results["site_results"][site_id] = site_result
            except Exception as e:
                results["site_results"][site_id] = {"status": "failed", "error": str(e)}

        # Determine overall status
        failed_sites = [site for site, result in results["site_results"].items() 
                       if result.get("status") != "success"]

        if not failed_sites:
            rollback_plan.status = 'completed'
            results["overall_status"] = "completed"
        else:
            rollback_plan.status = 'failed'
            results["overall_status"] = "failed"
            results["failed_sites"] = failed_sites

        self._update_rollback_status(rollback_id, rollback_plan.status)

        logger.info(f"Rollback {rollback_id} {rollback_plan.status}")
        return results

    def _rollback_site_version(self, site_id: str, target_version_id: str) -> Dict:
        """Rollback a specific site to target version with actual model loading."""
        if target_version_id not in self.version_registry:
            return {"status": "failed", "error": "Target version not found"}

        target_version = self.version_registry[target_version_id]
        previous_version_id = self.site_versions.get(site_id)

        try:
            # Load model weights from target version
            model_weights_path = Path(target_version.model_weights_path)
            if not model_weights_path.exists():
                return {"status": "failed", "error": "Model weights file not found"}

            with open(model_weights_path, 'rb') as f:
                model_weights = pickle.load(f)

            # Update site version tracking
            with self._lock:
                self.site_versions[site_id] = target_version_id

            # Update database
            if not self._update_site_version(site_id, target_version_id, 'rollback'):
                return {"status": "failed", "error": "Failed to update database"}

            # Update version deployment sites
            if site_id not in target_version.deployment_sites:
                target_version.deployment_sites.append(site_id)

            return {
                "status": "success",
                "previous_version": previous_version_id,
                "new_version": target_version_id,
                "rollback_time": datetime.now().isoformat(),
                "model_loaded": True
            }

        except Exception as e:
            logger.error(f"Error rolling back site {site_id}: {e}")
            return {"status": "failed", "error": str(e)}

    def _update_rollback_status(self, rollback_id: str, status: str) -> bool:
        """Update rollback status in database."""
        connection = self._get_db_connection()
        if not connection:
            return False

        cursor = connection.cursor()
        try:
            cursor.execute("""
                UPDATE neurotunes_rollback_plans 
                SET status = %s 
                WHERE rollback_id = %s
            """, (status, rollback_id))
            connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating rollback status: {e}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()

    def get_version_compatibility_matrix(self) -> Dict:
        """Get compatibility matrix for all versions."""
        with self._lock:
            matrix = {}
            for (version_a, version_b), compatibility in self.compatibility_matrix.items():
                if version_a not in matrix:
                    matrix[version_a] = {}
                matrix[version_a][version_b] = {
                    "compatibility_score": compatibility.compatibility_score,
                    "breaking_changes": compatibility.breaking_changes,
                    "migration_required": compatibility.migration_required
                }
            return matrix

    def get_all_sites_status(self) -> Dict:
        """Get version status for all sites."""
        with self._lock:
            sites_status = {}
            for site_id, version_id in self.site_versions.items():
                version = self.version_registry.get(version_id)
                if version:
                    sites_status[site_id] = {
                        "current_version": version.version_number,
                        "version_id": version_id,
                        "status": version.status,
                        "last_updated": version.created_at.isoformat(),
                        "performance_metrics": version.performance_metrics,
                        "clinical_metrics": version.clinical_metrics
                    }
            return sites_status

    def cleanup_old_versions(self, days_to_keep: int = 90):
        """Cleanup old model versions and files."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        with self._lock:
            versions_to_remove = []
            for version_id, version in self.version_registry.items():
                if (version.created_at < cutoff_date and 
                    version.status == 'deprecated' and
                    version_id not in self.site_versions.values()):
                    versions_to_remove.append(version_id)

            for version_id in versions_to_remove:
                version = self.version_registry[version_id]

                # Remove model file
                try:
                    model_path = Path(version.model_weights_path)
                    if model_path.exists():
                        model_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove model file for {version_id}: {e}")

                # Remove from registry
                del self.version_registry[version_id]

            logger.info(f"Cleaned up {len(versions_to_remove)} old versions")

# Example usage and testing
if __name__ == "__main__":
    # Initialize version manager
    try:
        version_manager = MultiSiteVersionManager()

        # Create test versions
        test_weights = {"layer1": [1, 2, 3], "layer2": [4, 5, 6]}
        test_performance = {"validation_loss": 0.15, "accuracy": 0.85}
        test_clinical = {"patient_satisfaction": 0.8, "symptom_improvement": 0.75}

        # Create version for site 1
        version_id_1 = version_manager.create_new_version(
            site_id="mayo_clinic",
            model_weights=test_weights,
            performance_metrics=test_performance,
            clinical_metrics=test_clinical,
            created_by="system"
        )

        print(f"Created version: {version_id_1}")
        print(f"Site status: {version_manager.get_all_sites_status()}")

    except Exception as e:
        print(f"Error during testing: {e}")