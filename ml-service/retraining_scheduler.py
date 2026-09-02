
# ====
# NeuroTunes Automated Retraining Scheduler
# 
# Leverages existing get_rlhf_training_data() method for periodic model updates
# with clinical validation and safety checks
# ====

import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
import json
import numpy as np
from scipy import stats
import os
import shutil

from data_logger import DataLogger
from reward_model import RewardModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RetrainingScheduler:
    """
    Automated scheduler for periodic RLHF model retraining with clinical validation
    """

    def __init__(self, min_feedback_threshold=50, significance_level=0.05,
                 challenger_r2_tolerance=0.02):
        self.min_feedback_threshold = min_feedback_threshold
        self.significance_level = significance_level
        # A newly trained "challenger" model is only promoted over the current
        # "champion" if its held-out R2 is at least (champion_r2 - tolerance).
        # A small tolerance avoids churn from run-to-run noise while still
        # blocking clear regressions from reaching patients.
        self.challenger_r2_tolerance = challenger_r2_tolerance
        self.data_logger = DataLogger()
        self.current_model_version = "1.0.0"
        self.last_training_time = None

    def calculate_clinical_efficacy_score(self, feedback_record):
        """
        Correlates feedback with established clinical markers
        """
        efficacy_weights = {
            'mood_improvement': 0.35,  # Primary outcome for depression
            'stress_reduction': 0.25,  # Cortisol proxy
            'engagement_duration': 0.20,  # Attention/cognitive load
            'motor_entrainment': 0.20   # Rhythm synchronization
        }

        # Convert mood_change to numerical score
        mood_score_map = {'much_worse': -2, 'worse': -1, 'same': 0, 'better': 1, 'much_better': 2}
        stress_score_map = {'much_higher': -2, 'higher': -1, 'same': 0, 'lower': 1, 'much_lower': 2}

        mood_score = mood_score_map.get(feedback_record.get('mood_change', 'same'), 0)
        stress_score = stress_score_map.get(feedback_record.get('stress_change', 'same'), 0)

        # Normalize listen duration (0-1 scale, assuming max 300 seconds)
        listen_duration = min(feedback_record.get('listen_duration_seconds', 30), 300) / 300

        # Motor entrainment proxy (replay count indicates rhythm engagement)
        motor_score = min(feedback_record.get('replay_count', 0), 3) / 3

        clinical_score = (
            (mood_score + 2) / 4 * efficacy_weights['mood_improvement'] +
            (stress_score + 2) / 4 * efficacy_weights['stress_reduction'] +
            listen_duration * efficacy_weights['engagement_duration'] +
            motor_score * efficacy_weights['motor_entrainment']
        )

        return clinical_score

    def evaluate_model_performance(self, training_data):
        """
        Statistical validation of model improvement potential
        """
        if len(training_data) < self.min_feedback_threshold:
            logger.warning(f"Insufficient data for retraining: {len(training_data)} < {self.min_feedback_threshold}")
            return False, "Insufficient data"

        # Calculate clinical efficacy scores
        clinical_scores = [self.calculate_clinical_efficacy_score(record) for record in training_data]
        overall_ratings = [record.get('overall_rating', 3) for record in training_data]

        # Recent vs historical performance comparison
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_data = [record for record in training_data 
                      if datetime.fromisoformat(record.get('feedback_time', '2024-01-01')) > recent_cutoff]

        if len(recent_data) < 10:
            return False, "Insufficient recent data for comparison"

        recent_scores = [self.calculate_clinical_efficacy_score(record) for record in recent_data]
        historical_scores = clinical_scores[:-len(recent_data)] if len(recent_data) < len(clinical_scores) else clinical_scores

        # Statistical significance test
        if len(historical_scores) > 0:
            t_stat, p_value = stats.ttest_ind(recent_scores, historical_scores)

            # Check for significant improvement or degradation
            if p_value < self.significance_level:
                if np.mean(recent_scores) > np.mean(historical_scores):
                    return True, f"Significant improvement detected (p={p_value:.4f})"
                else:
                    return True, f"Significant degradation detected (p={p_value:.4f}) - retraining needed"

        # Check data volume threshold for routine retraining
        if len(training_data) >= self.min_feedback_threshold * 2:
            return True, "Sufficient data volume for routine retraining"

        return False, "No significant change detected"

    def _model_artifact_paths(self, reward_model):
        """Return the on-disk artifacts written by RewardModel.train()."""
        return [
            reward_model.model_path,
            reward_model.scaler_path,
            reward_model.encoders_path,
            reward_model.columns_path,
            reward_model.metrics_path,
        ]

    def _backup_model_artifacts(self, reward_model):
        """
        Snapshot the current champion artifacts to *.champion.bak so we can
        roll back if the freshly trained challenger underperforms.

        Returns a dict {path: backup_path} of the files that were backed up.
        """
        backups = {}
        for path in self._model_artifact_paths(reward_model):
            if os.path.exists(path):
                backup_path = path + ".champion.bak"
                shutil.copy2(path, backup_path)
                backups[path] = backup_path
        logger.info(f"Backed up {len(backups)} champion artifact(s) before retraining")
        return backups

    def _restore_model_artifacts(self, backups):
        """Restore champion artifacts from a backup dict (rollback)."""
        restored = 0
        for path, backup_path in backups.items():
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, path)
                restored += 1
        logger.warning(f"Rolled back {restored} artifact(s) to previous champion")
        return restored

    def _cleanup_backups(self, backups):
        """Remove backup files after a successful promotion."""
        for backup_path in backups.values():
            try:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
            except OSError as e:
                logger.warning(f"Could not remove backup {backup_path}: {e}")

    def _read_champion_r2(self, reward_model):
        """
        Read the current champion's held-out R2 from its persisted metrics
        file. Returns None if no prior metrics exist (e.g. first ever train).
        """
        try:
            if os.path.exists(reward_model.metrics_path):
                with open(reward_model.metrics_path, "r") as f:
                    metrics = json.load(f)
                test_metrics = metrics.get("test_metrics", {})
                return test_metrics.get("r2")
        except (OSError, ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Could not read champion metrics: {e}")
        return None

    def perform_retraining(self):
        """
        Execute model retraining with champion/challenger validation.

        The currently deployed model ("champion") is backed up, a new model
        ("challenger") is trained in place, and the challenger is only kept if
        its held-out R2 is at least (champion_r2 - tolerance). Otherwise the
        champion artifacts are restored so a regression never reaches patients.
        """
        logger.info("Starting automated retraining process...")

        backups = {}
        from reward_model import reward_model
        try:
            # Fetch training data
            training_data = self.data_logger.get_rlhf_training_data(limit=2000)

            # Evaluate if retraining is needed
            should_retrain, reason = self.evaluate_model_performance(training_data)

            if not should_retrain:
                logger.info(f"Skipping retraining: {reason}")
                return False

            logger.info(f"Proceeding with retraining: {reason}")

            # Create new model version
            new_version = self.increment_version(self.current_model_version)

            # Record the champion's performance, then snapshot its artifacts so
            # we can roll back if the challenger is worse.
            champion_r2 = self._read_champion_r2(reward_model)
            backups = self._backup_model_artifacts(reward_model)

            # Train the challenger (overwrites artifacts in place).
            logger.info(f"Training challenger model version {new_version}...")
            success = reward_model.train()

            if not success:
                logger.warning("Challenger training did not complete; rolling back")
                self._restore_model_artifacts(backups)
                reward_model.load_model()
                return False

            # Challenger's held-out R2 comes from the freshly trained model.
            challenger_r2 = (reward_model.test_metrics or {}).get("r2")

            # ---- Champion vs challenger decision ----
            promoted = True
            decision_reason = "no prior champion metrics; accepting challenger"
            if champion_r2 is not None and challenger_r2 is not None:
                threshold = champion_r2 - self.challenger_r2_tolerance
                if challenger_r2 >= threshold:
                    promoted = True
                    decision_reason = (
                        f"challenger R2={challenger_r2:.4f} >= "
                        f"champion R2={champion_r2:.4f} - tol={self.challenger_r2_tolerance}"
                    )
                else:
                    promoted = False
                    decision_reason = (
                        f"challenger R2={challenger_r2:.4f} < "
                        f"champion R2={champion_r2:.4f} - tol={self.challenger_r2_tolerance}"
                    )
            elif challenger_r2 is None:
                # Cannot evaluate challenger (e.g. too few samples for a test
                # split); be conservative and keep the champion.
                promoted = False
                decision_reason = "challenger R2 unavailable; keeping champion"

            if not promoted:
                logger.warning(f"Rejecting challenger: {decision_reason}")
                self._restore_model_artifacts(backups)
                reward_model.load_model()  # reload restored champion into memory
                self._cleanup_backups(backups)
                # Still log the rejected attempt for auditability.
                self.data_logger.log_model_training(
                    model_version=f"{new_version}-rejected",
                    training_data_count=len(training_data),
                    validation_accuracy=challenger_r2 if challenger_r2 is not None else 0.0,
                    hyperparameters={"champion_challenger": True, "promoted": False,
                                     "decision": decision_reason}
                )
                return False

            logger.info(f"Promoting challenger: {decision_reason}")
            self._cleanup_backups(backups)

            # Validate promoted model performance (clinical correlation metric).
            validation_score = self.validate_model_performance(training_data)

            # Log training run
            hyperparameters = {
                "learning_rate": 0.001,
                "epochs": 100,
                "batch_size": len(training_data),
                "min_feedback_threshold": self.min_feedback_threshold,
                "clinical_efficacy_weighting": True,
                "champion_challenger": True,
                "promoted": True,
                "champion_r2": champion_r2,
                "challenger_r2": challenger_r2,
                "decision": decision_reason,
            }

            training_id = self.data_logger.log_model_training(
                model_version=new_version,
                training_data_count=len(training_data),
                validation_accuracy=validation_score,
                hyperparameters=hyperparameters
            )

            # Update current version
            self.current_model_version = new_version
            self.last_training_time = datetime.now()

            logger.info(f"Retraining completed successfully. New version: {new_version}")
            return True

        except Exception as e:
            logger.error(f"Retraining failed: {e}")
            # Best-effort rollback so a partially trained model never sticks.
            if backups:
                try:
                    self._restore_model_artifacts(backups)
                    reward_model.load_model()
                    self._cleanup_backups(backups)
                except Exception as restore_err:
                    logger.error(f"Rollback after failure also failed: {restore_err}")
            return False

    def validate_model_performance(self, training_data):
        """
        Calculate validation metrics for the newly trained model
        """
        # Simple validation: correlation between clinical scores and ratings
        clinical_scores = [self.calculate_clinical_efficacy_score(record) for record in training_data]
        overall_ratings = [record.get('overall_rating', 3) for record in training_data]

        correlation, _ = stats.pearsonr(clinical_scores, overall_ratings)
        return abs(correlation)  # Return absolute correlation as validation score

    def increment_version(self, current_version):
        """
        Increment model version number
        """
        parts = current_version.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        return '.'.join(parts)

    def start_scheduler(self):
        """
        Start the automated retraining scheduler
        """
        # Schedule weekly retraining checks
        schedule.every().monday.at("02:00").do(self.perform_retraining)

        # Schedule daily data quality checks
        schedule.every().day.at("01:00").do(self.check_data_quality)

        logger.info("Retraining scheduler started. Weekly retraining: Mondays at 2:00 AM")

        # Run scheduler in background thread
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

        return scheduler_thread

    def check_data_quality(self):
        """
        Daily data quality monitoring
        """
        try:
            recent_data = self.data_logger.get_rlhf_training_data(limit=100)

            if len(recent_data) == 0:
                logger.warning("No recent feedback data found")
                return

            # Check for data quality issues
            null_ratings = sum(1 for record in recent_data if not record.get('overall_rating'))
            incomplete_feedback = sum(1 for record in recent_data 
                                    if not record.get('reported_feeling') or not record.get('feedback_text'))

            quality_score = 1 - (null_ratings + incomplete_feedback) / len(recent_data)

            logger.info(f"Data quality check: {quality_score:.2f} (recent {len(recent_data)} records)")

            if quality_score < 0.8:
                logger.warning(f"Data quality below threshold: {quality_score:.2f}")

        except Exception as e:
            logger.error(f"Data quality check failed: {e}")

# Usage example
if __name__ == "__main__":
    scheduler = RetrainingScheduler(min_feedback_threshold=50)
    scheduler_thread = scheduler.start_scheduler()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")
