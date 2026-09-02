"""
Focused tests for the safety-and-validation additions (PR#7):

  * #2  reward_model  -> k-fold cross-validation + held-out R2/MSE evaluation
  * #3  retraining_scheduler -> champion/challenger backup/restore (rollback)
  * #8  safety_boundaries -> hard clamps + recommended-range warnings

These tests are dependency-light and self-contained. They avoid any database
or network access:
  - the champion/challenger tests bypass RetrainingScheduler.__init__ (which
    would open a DB connection) via object.__new__ and drive only the pure
    artifact backup/restore/rollback helpers against temp files.
  - the reward-model tests exercise cross_validate/_evaluate on synthetic
    tensors, so no training data or DB is required.

Run:  python3 mlServer/test_suite/test_safety_and_validation.py
"""

import os
import sys
import json
import tempfile
import unittest
from types import SimpleNamespace

# Make the mlServer package importable regardless of CWD.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MLSERVER_DIR = os.path.dirname(THIS_DIR)
if MLSERVER_DIR not in sys.path:
    sys.path.insert(0, MLSERVER_DIR)


# --------------------------------------------------------------------------- #
# #8  Safety boundary enforcement
# --------------------------------------------------------------------------- #
class TestSafetyBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from safety_boundaries import SafetyBoundaryValidator
        cls.validator = SafetyBoundaryValidator()

    def test_tempo_clamped_high(self):
        track = {"tempo": 240, "therapy_goal": "relaxation"}
        out, violations = self.validator.validate_track(track)
        self.assertEqual(out["tempo"], 180)  # clamped to hard max
        self.assertTrue(any(v["type"] == "hard" and v["field"] == "tempo"
                            for v in violations))

    def test_tempo_clamped_low(self):
        track = {"tempo": 10}
        out, _ = self.validator.validate_track(track)
        self.assertEqual(out["tempo"], 40)  # clamped to hard min

    def test_duration_and_unit_interval_clamped(self):
        track = {"duration": 0, "complexity": 1.7, "dynamic_range": -0.5}
        out, _ = self.validator.validate_track(track)
        self.assertEqual(out["duration"], 15.0)
        self.assertEqual(out["complexity"], 1.0)
        self.assertEqual(out["dynamic_range"], 0.0)

    def test_binaural_frequency_clamped(self):
        track = {"binaural_frequency": 5000}
        out, _ = self.validator.validate_track(track)
        self.assertEqual(out["binaural_frequency"], 1000)

    def test_recommended_range_warns_but_does_not_clamp(self):
        # 150 BPM is inside the hard limit (40-180) but far above the
        # recommended relaxation range -> warning, value unchanged.
        track = {"tempo": 150, "therapy_goal": "relaxation"}
        out, violations = self.validator.validate_track(track)
        self.assertEqual(out["tempo"], 150)  # not clamped
        self.assertTrue(any(v["type"] == "warning" and v["field"] == "tempo"
                            for v in violations))

    def test_safe_track_passes_clean(self):
        track = {"tempo": 70, "therapy_goal": "relaxation", "duration": 300,
                 "complexity": 0.4}
        out, violations = self.validator.validate_track(track)
        self.assertEqual(violations, [])
        self.assertEqual(out["tempo"], 70)

    def test_validate_tracks_report(self):
        tracks = [
            {"tempo": 300, "therapy_goal": "focus"},   # hard clamp
            {"tempo": 70, "therapy_goal": "relaxation"},  # clean
        ]
        out, report = self.validator.validate_tracks(tracks)
        self.assertTrue(report["safety_validated"])
        self.assertTrue(report["clamped"])
        self.assertEqual(out[0]["tempo"], 180)
        # track_index annotated on violations
        self.assertTrue(all("track_index" in v for v in report["violations"]))

    def test_empty_tracks(self):
        out, report = self.validator.validate_tracks([])
        self.assertEqual(out, [])
        self.assertTrue(report["safety_validated"])
        self.assertFalse(report["clamped"])

    def test_non_numeric_ignored(self):
        track = {"tempo": "not-a-number"}
        out, violations = self.validator.validate_track(track)
        self.assertEqual(out["tempo"], "not-a-number")
        self.assertEqual(violations, [])


# --------------------------------------------------------------------------- #
# #2  Reward model: cross-validation + held-out evaluation
# --------------------------------------------------------------------------- #
class TestRewardModelCV(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        import numpy as np
        cls.torch = torch
        cls.np = np
        from reward_model import RewardModel, RewardNet
        cls.RewardModel = RewardModel
        cls.RewardNet = RewardNet
        # Deterministic synthetic regression: y is a linear fn of X features.
        torch.manual_seed(0)
        np.random.seed(0)
        n, d = 120, 5
        X = np.random.randn(n, d).astype("float32")
        w = np.array([1.5, -2.0, 0.5, 0.0, 1.0], dtype="float32")
        y = (X @ w + 0.05 * np.random.randn(n)).astype("float32")
        cls.X = torch.from_numpy(X)
        cls.y = torch.from_numpy(y)

    def test_evaluate_returns_sane_metrics(self):
        model = self.RewardModel()  # __init__ only makes /app/models dir
        net = model._train_fold(self.X, self.y, input_size=self.X.shape[1],
                                num_epochs=150)
        metrics = self.RewardModel._evaluate(net, self.X, self.y)
        self.assertIn("r2", metrics)
        self.assertIn("mse", metrics)
        # A well-specified linear problem should be learned well.
        self.assertGreater(metrics["r2"], 0.8)
        self.assertLess(metrics["mse"], 1.0)

    def test_cross_validate_structure_and_quality(self):
        model = self.RewardModel()
        cv = model.cross_validate(self.X, self.y, k=5, num_epochs=120)
        for key in ("r2_mean", "r2_std", "mse_mean", "mse_std", "folds"):
            self.assertIn(key, cv)
        self.assertEqual(cv["folds"], 5)
        self.assertGreater(cv["r2_mean"], 0.7)

    def test_cross_validate_too_few_samples(self):
        model = self.RewardModel()
        cv = model.cross_validate(self.X[:3], self.y[:3], k=5)
        self.assertEqual(cv, {})  # gracefully skipped


# --------------------------------------------------------------------------- #
# #3  Champion / challenger backup + rollback (pure file helpers)
# --------------------------------------------------------------------------- #
class TestChampionChallenger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from retraining_scheduler import RetrainingScheduler
        cls.RetrainingScheduler = RetrainingScheduler

    def _make_scheduler(self, tolerance=0.02):
        # Bypass __init__ (avoids DataLogger/DB); set only what helpers use.
        sched = object.__new__(self.RetrainingScheduler)
        sched.challenger_r2_tolerance = tolerance
        return sched

    def _make_reward_model_stub(self, tmpdir, r2=None):
        """A stand-in reward model exposing the artifact paths used by the
        backup/restore helpers, plus a metrics file if r2 is provided."""
        paths = {
            "model_path": os.path.join(tmpdir, "reward_model.pth"),
            "scaler_path": os.path.join(tmpdir, "reward_scaler.pkl"),
            "encoders_path": os.path.join(tmpdir, "reward_encoders.pkl"),
            "columns_path": os.path.join(tmpdir, "reward_columns.pkl"),
            "metrics_path": os.path.join(tmpdir, "reward_metrics.json"),
        }
        # Write champion artifacts with known content.
        for name, p in paths.items():
            if name == "metrics_path":
                continue
            with open(p, "w") as f:
                f.write("CHAMPION")
        if r2 is not None:
            with open(paths["metrics_path"], "w") as f:
                json.dump({"test_metrics": {"r2": r2, "mse": 0.1}}, f)
        return SimpleNamespace(**paths)

    def test_backup_and_restore_roundtrip(self):
        sched = self._make_scheduler()
        with tempfile.TemporaryDirectory() as tmp:
            rm = self._make_reward_model_stub(tmp, r2=0.75)
            backups = sched._backup_model_artifacts(rm)
            # metrics + 4 artifacts = 5 files backed up
            self.assertEqual(len(backups), 5)

            # Simulate a challenger overwriting the champion files.
            for p in [rm.model_path, rm.scaler_path]:
                with open(p, "w") as f:
                    f.write("CHALLENGER")

            restored = sched._restore_model_artifacts(backups)
            self.assertEqual(restored, 5)
            with open(rm.model_path) as f:
                self.assertEqual(f.read(), "CHAMPION")  # rolled back

    def test_read_champion_r2(self):
        sched = self._make_scheduler()
        with tempfile.TemporaryDirectory() as tmp:
            rm = self._make_reward_model_stub(tmp, r2=0.66)
            self.assertAlmostEqual(sched._read_champion_r2(rm), 0.66)

    def test_read_champion_r2_missing(self):
        sched = self._make_scheduler()
        with tempfile.TemporaryDirectory() as tmp:
            rm = self._make_reward_model_stub(tmp, r2=None)
            self.assertIsNone(sched._read_champion_r2(rm))

    def test_cleanup_backups(self):
        sched = self._make_scheduler()
        with tempfile.TemporaryDirectory() as tmp:
            rm = self._make_reward_model_stub(tmp, r2=0.5)
            backups = sched._backup_model_artifacts(rm)
            for bp in backups.values():
                self.assertTrue(os.path.exists(bp))
            sched._cleanup_backups(backups)
            for bp in backups.values():
                self.assertFalse(os.path.exists(bp))

    def test_promotion_decision_logic(self):
        """Replicate the promote/reject rule the scheduler applies."""
        tol = 0.02

        def decide(champion_r2, challenger_r2):
            if champion_r2 is not None and challenger_r2 is not None:
                return challenger_r2 >= champion_r2 - tol
            if challenger_r2 is None:
                return False
            return True  # no prior champion

        self.assertTrue(decide(0.70, 0.71))   # clear improvement
        self.assertTrue(decide(0.70, 0.69))   # within tolerance
        self.assertFalse(decide(0.70, 0.60))  # clear regression -> reject
        self.assertTrue(decide(None, 0.50))   # first ever model
        self.assertFalse(decide(0.70, None))  # unevaluable challenger


if __name__ == "__main__":
    unittest.main(verbosity=2)
