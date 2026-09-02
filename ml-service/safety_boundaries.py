"""
Clinical safety-boundary enforcement for generated music parameters.

This is a defense-in-depth layer that runs AFTER music generation and BEFORE
tracks are returned/logged. It is intentionally implemented as a separate
module so the patent-critical music_generator.py core logic is never modified.

Why this exists
---------------
The generator already applies some internal clamps, but a reward-model-driven
or future adaptive pipeline could push parameters outside clinically safe
ranges. For real patients this matters: e.g. an excessively fast tempo can be
over-arousing for anxiety/PTSD, and out-of-range binaural/carrier frequencies
or zero-length tracks are simply invalid. This validator enforces HARD limits
(values are clamped) and emits recommended-range WARNINGS (values are kept but
flagged) so nothing unsafe is ever delivered.

The limits mirror the evidence-based ranges already encoded in
music_generator.py (therapeutic_tempos, binaural_frequencies) plus general
audio-safety bounds; they are deliberately conservative and auditable.
"""

import logging

logger = logging.getLogger(__name__)


class SafetyBoundaryValidator:
    """Validate and clamp generated music parameters to safe clinical ranges."""

    # HARD limits — values outside are clamped to the nearest bound.
    # (field: (min, max))
    HARD_LIMITS = {
        "tempo": (40, 180),                 # BPM — cardiac/arousal safety
        "binaural_frequency": (0.5, 1000),  # Hz — covers beat freqs + solfeggio carriers
        "duration": (15.0, 1800.0),         # seconds — no zero/negative or >30 min
        # unit-interval descriptors
        "complexity": (0.0, 1.0),
        "final_complexity": (0.0, 1.0),
        "dynamic_range": (0.0, 1.0),
        "harmonic_complexity": (0.0, 1.0),
        "melodic_range": (0.0, 1.0),
    }

    # Recommended per-therapy-goal tempo ranges (warn-only; mirrors the
    # generator's therapeutic_tempos table). Values inside HARD_LIMITS but
    # outside these produce a warning, not a clamp.
    RECOMMENDED_TEMPO = {
        "relaxation": (60, 80),
        "stimulation": (100, 140),
        "focus": (80, 100),
        "motor_recovery": (90, 120),
        "gait_training": (100, 130),
        "cognitive_rehab": (70, 90),
        "depression": (80, 110),
        "anxiety": (60, 85),
        "adhd": (90, 110),
        "ptsd": (65, 80),
        "autism": (70, 95),
        "dementia": (75, 95),
        "pain_management": (60, 75),
        "sleep_induction": (50, 70),
    }

    def validate_track(self, track):
        """Validate/clamp a single track dict in place.

        Returns (track, violations) where violations is a list of dicts
        describing every clamp ('hard') or flag ('warning') applied.
        """
        violations = []
        if not isinstance(track, dict):
            return track, violations

        # Enforce hard numeric limits (clamp).
        for field, (lo, hi) in self.HARD_LIMITS.items():
            if field not in track or track[field] is None:
                continue
            try:
                value = float(track[field])
            except (TypeError, ValueError):
                continue
            clamped = max(lo, min(hi, value))
            if clamped != value:
                violations.append({
                    "field": field,
                    "type": "hard",
                    "original": value,
                    "clamped_to": clamped,
                    "limit": [lo, hi],
                })
                track[field] = clamped
                logger.warning(
                    f"Safety clamp: {field}={value} -> {clamped} (limit {lo}-{hi})"
                )

        # Warn (do not clamp) when tempo is outside the recommended range for
        # the track's therapy goal.
        goal = track.get("therapy_goal")
        tempo = track.get("tempo")
        if goal in self.RECOMMENDED_TEMPO and tempo is not None:
            lo, hi = self.RECOMMENDED_TEMPO[goal]
            try:
                tempo_v = float(tempo)
                if tempo_v < lo or tempo_v > hi:
                    violations.append({
                        "field": "tempo",
                        "type": "warning",
                        "value": tempo_v,
                        "recommended": [lo, hi],
                        "therapy_goal": goal,
                    })
                    logger.info(
                        f"Tempo {tempo_v} outside recommended {lo}-{hi} for goal '{goal}'"
                    )
            except (TypeError, ValueError):
                pass

        return track, violations

    def validate_tracks(self, tracks):
        """Validate/clamp a list of tracks.

        Returns (tracks, report) where report summarizes all violations and
        whether any hard clamp was applied.
        """
        all_violations = []
        if not tracks:
            return tracks, {"safety_validated": True, "clamped": False, "violations": []}

        for idx, track in enumerate(tracks):
            _, violations = self.validate_track(track)
            for v in violations:
                v["track_index"] = idx
            all_violations.extend(violations)

        report = {
            "safety_validated": True,
            "clamped": any(v["type"] == "hard" for v in all_violations),
            "warnings": sum(1 for v in all_violations if v["type"] == "warning"),
            "violations": all_violations,
        }
        return tracks, report


# Module-level singleton for convenient reuse.
safety_validator = SafetyBoundaryValidator()
