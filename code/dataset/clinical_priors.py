#!/usr/bin/env python3
"""
clinical_priors.py -- shared clinical domain knowledge for the v3 dataset.

This is the single source of truth used by BOTH the profile generator
(gen_profiles.py) and the ensemble labeler (ensemble_label.py), so the
features we sample and the therapeutic targets we assign stay consistent.

It encodes, for every condition NeuroTunes targets:
  * realistic feature priors (age band, stress/sleep/energy tendencies,
    plausible current-mood words, medication relevance),
  * the primary therapy goal,
  * a base therapeutic-affect target (arousal, valence, focus, calm) that a
    music therapist would aim the *music* toward (NOT the patient's mood),
  * how that target should shift with severity and session progression.

All targets are in [-1, 1]. These priors are literature-informed heuristics
for a *research* synthetic set -- they are model/therapist-checkable, not
human ground truth.
"""
import numpy as np

# ---------------------------------------------------------------------------
# Conditions the production generator (music_generator.py clinical_mapping)
# already routes for. The v2 dataset covered only the first 4; v3 covers all.
# ---------------------------------------------------------------------------
# Each entry:
#   goal        : primary therapy goal string (matches platform vocabulary)
#   age         : (low, high, mode)  -- triangular age prior
#   stress      : (mean, sd) on 0-10
#   sleep       : (mean, sd) on 0-10   (higher = better sleep)
#   energy      : (mean, sd) on 0-10
#   moods       : plausible current-mood words for this condition
#   med_relevant: whether medication_state is clinically meaningful
#   target      : base therapeutic (arousal, valence, focus, calm) for the MUSIC
#   prevalence  : rough relative real-world weight (for natural-prevalence set)
CONDITIONS = {
    "Anxiety": dict(
        goal="Relaxation", age=(18, 70, 30), stress=(7.5, 1.5), sleep=(3.5, 1.5),
        energy=(4.0, 2.0), med_relevant=True,
        moods=["Anxious", "Stressed", "Overwhelmed", "Restless", "Tense"],
        target=(-0.55, 0.25, -0.10, 0.75), prevalence=0.19),
    "Depression": dict(
        goal="Apathy & Mood Regulation", age=(18, 75, 35), stress=(6.5, 2.0),
        sleep=(3.5, 2.0), energy=(2.5, 1.5), med_relevant=True,
        moods=["Sad", "Numb", "Withdrawn", "Hopeless", "Tired"],
        target=(0.15, 0.55, 0.10, 0.30), prevalence=0.18),
    "Post-Stroke": dict(
        goal="Gait & Motor Priming", age=(45, 85, 66), stress=(5.0, 2.0),
        sleep=(5.0, 2.0), energy=(4.0, 2.0), med_relevant=False,
        moods=["Determined", "Frustrated", "Tired", "Hopeful", "Focused"],
        target=(0.45, 0.35, 0.30, 0.25), prevalence=0.06),
    "Parkinsons": dict(
        goal="Gait & Motor Priming", age=(50, 85, 68), stress=(5.0, 2.0),
        sleep=(4.5, 2.0), energy=(3.5, 2.0), med_relevant=True,
        moods=["Determined", "Frustrated", "Tired", "Focused", "Neutral"],
        target=(0.50, 0.30, 0.25, 0.20), prevalence=0.05),
    "ADHD": dict(
        goal="Cognitive Enhancement", age=(6, 45, 16), stress=(5.5, 2.0),
        sleep=(4.5, 2.0), energy=(7.0, 2.0), med_relevant=True,
        moods=["Restless", "Distracted", "Energetic", "Frustrated", "Motivated"],
        target=(0.10, 0.30, 0.65, 0.35), prevalence=0.09),
    "PTSD": dict(
        goal="Relaxation", age=(20, 65, 35), stress=(8.0, 1.5), sleep=(2.5, 1.5),
        energy=(4.0, 2.0), med_relevant=True,
        moods=["Anxious", "Overwhelmed", "Numb", "Irritable", "Withdrawn"],
        target=(-0.60, 0.20, -0.05, 0.80), prevalence=0.06),
    "Dementia": dict(
        goal="Cognitive Enhancement", age=(65, 95, 78), stress=(4.5, 2.0),
        sleep=(4.5, 2.0), energy=(3.5, 1.5), med_relevant=True,
        moods=["Confused", "Withdrawn", "Neutral", "Agitated", "Calm"],
        target=(0.05, 0.45, 0.30, 0.45), prevalence=0.05),
    "Autism": dict(
        goal="Cognitive Enhancement", age=(4, 40, 12), stress=(6.0, 2.0),
        sleep=(4.0, 2.0), energy=(5.5, 2.5), med_relevant=False,
        moods=["Overwhelmed", "Focused", "Restless", "Neutral", "Anxious"],
        target=(-0.20, 0.35, 0.45, 0.55), prevalence=0.03),
    "Chronic-Pain": dict(
        goal="Relaxation", age=(25, 80, 50), stress=(7.0, 1.8), sleep=(3.0, 1.5),
        energy=(3.0, 1.5), med_relevant=True,
        moods=["Tired", "Frustrated", "Withdrawn", "Irritable", "Numb"],
        target=(-0.45, 0.30, -0.10, 0.70), prevalence=0.07),
    "Insomnia": dict(
        goal="Relaxation", age=(20, 80, 45), stress=(6.5, 2.0), sleep=(1.8, 1.0),
        energy=(3.0, 1.8), med_relevant=True,
        moods=["Tired", "Restless", "Frustrated", "Overwhelmed", "Numb"],
        target=(-0.70, 0.20, -0.30, 0.85), prevalence=0.08),
    "Panic-Disorder": dict(
        goal="Relaxation", age=(18, 60, 30), stress=(8.5, 1.2), sleep=(3.0, 1.5),
        energy=(4.5, 2.0), med_relevant=True,
        moods=["Anxious", "Overwhelmed", "Restless", "Tense", "Stressed"],
        target=(-0.65, 0.25, -0.15, 0.85), prevalence=0.03),
    "TBI": dict(  # traumatic brain injury -- cognitive + emotional rehab
        goal="Cognitive Enhancement", age=(18, 70, 35), stress=(6.0, 2.0),
        sleep=(4.0, 2.0), energy=(3.5, 2.0), med_relevant=True,
        moods=["Frustrated", "Tired", "Confused", "Determined", "Numb"],
        target=(0.20, 0.35, 0.40, 0.35), prevalence=0.03),
    "Chronic-Stress": dict(  # subclinical burnout / wellness-adjacent
        goal="Relaxation", age=(20, 65, 38), stress=(7.0, 1.8), sleep=(4.0, 1.8),
        energy=(4.5, 2.0), med_relevant=False,
        moods=["Stressed", "Overwhelmed", "Tired", "Irritable", "Numb"],
        target=(-0.40, 0.35, 0.05, 0.65), prevalence=0.09),
    "Healthy": dict(
        goal="Cognitive Enhancement", age=(18, 65, 30), stress=(3.5, 1.8),
        sleep=(6.5, 1.8), energy=(6.5, 1.8), med_relevant=False,
        moods=["Focused", "Motivated", "Determined", "Hopeful", "Neutral"],
        target=(0.35, 0.55, 0.55, 0.35), prevalence=0.09),
}

GENDERS = ["Female", "Male", "Other"]
SEVERITIES = ["mild", "moderate", "severe"]
TIMES_OF_DAY = ["morning", "afternoon", "evening"]
MED_STATES = ["none", "on", "off"]  # 'off' = due for/without meds (matters PD/ADHD)

TARGETS = ["arousal", "valence", "focus", "calm"]


def severity_shift(target, severity):
    """Nudge the base target by severity.

    Severe cases get GENTLER music (lower arousal, higher calm) for
    over-arousal conditions, and a softer push for under-arousal ones --
    the standard 'meet them where they are' iso-principle.
    """
    a, v, f, c = target
    if severity == "severe":
        # pull toward soothing / less demanding
        a -= 0.15 if a > 0 else 0.10
        c += 0.10
        f -= 0.10
    elif severity == "mild":
        a += 0.05
        f += 0.05
    return (a, v, f, c)


def session_shift(target, session_number, goal):
    """Therapy trajectory: music can progress across sessions.

    Iso-principle -> gradual change. e.g. depression/apathy work ramps
    arousal & valence upward over a course of care; relaxation work deepens
    calm. Kept small so early sessions stay safe.
    """
    a, v, f, c = target
    prog = min(0.20, max(0, session_number - 1) * 0.015)  # cap +0.20 by ~session 14
    if goal in ("Apathy & Mood Regulation", "Cognitive Enhancement"):
        a += prog
        v += prog * 0.6
    elif goal == "Relaxation":
        c += prog
        a -= prog * 0.5
    elif goal == "Gait & Motor Priming":
        a += prog * 0.5
        f += prog * 0.5
    return (a, v, f, c)


def clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))



# ===========================================================================
# RICH PATIENT REALISM (opt-in via gen_profiles.py --rich)
# ---------------------------------------------------------------------------
# The block below adds *patient-level* heterogeneity so a scaled dataset looks
# like a real caseload of distinct people, not resampled draws from one
# distribution. Every axis here is a literature-informed heuristic for a
# RESEARCH synthetic set -- model/therapist-checkable, NOT human ground truth.
# Nothing below is referenced by the original single-snapshot path, so the
# committed v3 CSVs remain byte-identical.
# ===========================================================================

# --- responder archetypes: how a patient's course of care actually unfolds ---
#   resp       : per-session therapeutic drift toward healthier state (bigger=faster)
#   setback_p  : probability of a setback session (symptom flare)
#   oscillate  : extra session-to-session volatility (relapsing-remitting look)
#   plateau_at : fraction of the course after which improvement flattens
#   dropout_p  : base per-session probability the patient disengages / ends early
ARCHETYPES = {
    "rapid_responder":     dict(p=0.20, resp=(0.45, 0.70), setback_p=0.06,
                                oscillate=0.5, plateau_at=0.55, dropout_p=0.02),
    "gradual_responder":   dict(p=0.42, resp=(0.20, 0.40), setback_p=0.12,
                                oscillate=0.7, plateau_at=0.70, dropout_p=0.03),
    "non_responder":       dict(p=0.20, resp=(0.00, 0.12), setback_p=0.14,
                                oscillate=0.8, plateau_at=0.30, dropout_p=0.06),
    "relapsing_remitting": dict(p=0.18, resp=(0.20, 0.45), setback_p=0.28,
                                oscillate=1.6, plateau_at=0.60, dropout_p=0.04),
}

# --- medication adherence (only meaningful when a condition is med_relevant) --
ADHERENCE_LEVELS = ["adherent", "partial", "non_adherent"]
ADHERENCE_P = [0.55, 0.30, 0.15]
# how adherence scales therapeutic responsiveness and the chance of an 'off' med
ADHERENCE_RESP = {"adherent": 1.0, "partial": 0.75, "non_adherent": 0.5}
ADHERENCE_OFF_P = {"adherent": 0.08, "partial": 0.25, "non_adherent": 0.55}

# --- chronotype: interacts with time_of_day (misaligned sessions perform worse)
CHRONOTYPES = ["morning", "intermediate", "evening"]
CHRONOTYPE_P = [0.30, 0.45, 0.25]
CHRONO_BEST_TIME = {"morning": "morning", "evening": "evening",
                    "intermediate": "afternoon"}

# --- social support: buffers setbacks and reduces dropout -------------------
SUPPORT_LEVELS = ["low", "moderate", "high"]
SUPPORT_P = [0.25, 0.50, 0.25]
SUPPORT_RESP = {"low": 0.85, "moderate": 1.0, "high": 1.12}

# --- realistic comorbidity co-occurrence -----------------------------------
# For each primary condition, the comorbid conditions clinicians actually see,
# with rough relative weights. Replaces the old uniform-random second dx.
COMORBIDITY_MATRIX = {
    "Anxiety":        {"Depression": 0.40, "Insomnia": 0.20, "Panic-Disorder": 0.15,
                       "Chronic-Pain": 0.10, "Chronic-Stress": 0.15},
    "Depression":     {"Anxiety": 0.38, "Insomnia": 0.20, "Chronic-Pain": 0.17,
                       "Chronic-Stress": 0.15, "PTSD": 0.10},
    "PTSD":           {"Depression": 0.32, "Anxiety": 0.28, "Insomnia": 0.22,
                       "Chronic-Pain": 0.10, "Panic-Disorder": 0.08},
    "Panic-Disorder": {"Anxiety": 0.45, "Depression": 0.25, "Insomnia": 0.18,
                       "Chronic-Stress": 0.12},
    "Insomnia":       {"Anxiety": 0.34, "Depression": 0.30, "Chronic-Pain": 0.20,
                       "Chronic-Stress": 0.16},
    "Chronic-Pain":   {"Depression": 0.38, "Anxiety": 0.24, "Insomnia": 0.24,
                       "Chronic-Stress": 0.14},
    "Chronic-Stress": {"Anxiety": 0.36, "Insomnia": 0.24, "Depression": 0.24,
                       "Chronic-Pain": 0.16},
    "ADHD":           {"Anxiety": 0.34, "Depression": 0.26, "Autism": 0.22,
                       "Insomnia": 0.18},
    "Autism":         {"ADHD": 0.34, "Anxiety": 0.34, "Depression": 0.20,
                       "Insomnia": 0.12},
    "Parkinsons":     {"Depression": 0.40, "Insomnia": 0.24, "Anxiety": 0.22,
                       "Dementia": 0.14},
    "Post-Stroke":    {"Depression": 0.42, "Anxiety": 0.24, "Insomnia": 0.18,
                       "Dementia": 0.16},
    "Dementia":       {"Depression": 0.40, "Anxiety": 0.28, "Insomnia": 0.20,
                       "Parkinsons": 0.12},
    "TBI":            {"Depression": 0.36, "Anxiety": 0.30, "PTSD": 0.18,
                       "Insomnia": 0.16},
    "Healthy":        {},  # healthy controls carry no comorbidity
}

# --- per-condition bands for the extra latent traits -----------------------
# (low, high, mode) triangular unless noted. Defaults used when a condition is
# not listed. cognition/motor are 0-10 (10 = unimpaired); sensory & trait_anx
# are 0-10 (10 = highly sensitive / highly anxious temperament).
_DUR_DEFAULT = (0.2, 12.0, 3.0)      # years since diagnosis / symptom onset
DURATION_YEARS = {
    "Anxiety": (0.3, 20, 5), "Depression": (0.3, 20, 5), "PTSD": (0.5, 25, 6),
    "Panic-Disorder": (0.3, 15, 3), "Insomnia": (0.2, 15, 3),
    "Chronic-Pain": (0.5, 25, 8), "Chronic-Stress": (0.2, 8, 2),
    "ADHD": (3, 30, 12), "Autism": (3, 30, 14), "Dementia": (0.5, 10, 3),
    "Parkinsons": (0.5, 15, 4), "Post-Stroke": (0.1, 8, 1.5),
    "TBI": (0.2, 12, 2.5), "Healthy": (0.0, 1.0, 0.0),
}
COGNITION_BAND = {  # baseline cognitive function 0-10
    "Dementia": (0, 5, 2), "TBI": (2, 7, 4), "Post-Stroke": (3, 8, 5),
    "Parkinsons": (4, 9, 6), "ADHD": (4, 9, 6),
}
_COG_DEFAULT = (6, 10, 8)
MOTOR_BAND = {      # baseline motor function 0-10 (10 = unimpaired)
    "Post-Stroke": (1, 7, 3), "Parkinsons": (2, 8, 4), "Dementia": (4, 9, 6),
    "TBI": (3, 9, 6),
}
_MOTOR_DEFAULT = (7, 10, 9)
SENSORY_BAND = {    # sensitivity to musical intensity 0-10 (10 = very sensitive)
    "Autism": (6, 10, 8), "PTSD": (5, 10, 7), "Panic-Disorder": (5, 9, 7),
    "Anxiety": (4, 9, 6), "Dementia": (4, 9, 6), "Chronic-Pain": (4, 9, 6),
}
_SENS_DEFAULT = (2, 7, 4)
TRAIT_ANX_BAND = {  # trait (temperamental) anxiety 0-10
    "Anxiety": (6, 10, 8), "Panic-Disorder": (6, 10, 8), "PTSD": (6, 10, 8),
    "Depression": (4, 9, 6), "Chronic-Stress": (5, 9, 7), "Insomnia": (4, 9, 6),
}
_TRAIT_DEFAULT = (2, 8, 5)

RICH_CATEG = ["archetype", "medication_adherence", "chronotype", "social_support"]
RICH_NUMERIC = ["illness_duration_years", "comorbidity_count", "baseline_cognition",
                "motor_function", "sensory_sensitivity", "trait_anxiety",
                "music_engagement", "life_event"]


# ---------------------------------------------------------------------------
# label-side response functions for the rich axes (used by ensemble_label.py).
# All are guarded: if a field is absent (base datasets) they return zeros, so
# the labeler stays backward compatible.
# ---------------------------------------------------------------------------
def _fget(profile, key, default=None):
    v = profile.get(key, default)
    if v is None or v == "":
        return default
    return v


def adherence_response(profile):
    """Non-adherence on a med-relevant condition -> the *music* must compensate
    (steadier, more supportive), mirroring a patient who is under-medicated."""
    adh = _fget(profile, "medication_adherence", "adherent")
    dx = profile.get("diagnosis", "")
    if adh == "non_adherent":
        if dx in ("Parkinsons", "Post-Stroke"):
            return np.array([0.08, 0.0, 0.10, -0.03])   # more motor priming
        if dx == "ADHD":
            return np.array([-0.06, 0.0, 0.12, 0.04])    # more focus scaffolding
        if dx in ("Anxiety", "PTSD", "Panic-Disorder", "Depression"):
            return np.array([-0.06, 0.02, 0.0, 0.08])    # more soothing
    elif adh == "partial":
        return np.array([-0.02, 0.0, 0.02, 0.02])
    return np.zeros(4)


def chronotype_response(profile):
    """A session run at the patient's off-peak time -> gentler, less demanding
    target (they have less regulatory headroom)."""
    ct = _fget(profile, "chronotype")
    tod = _fget(profile, "time_of_day")
    if ct is None or tod is None:
        return np.zeros(4)
    best = CHRONO_BEST_TIME.get(ct)
    if best is not None and tod != best:
        return np.array([-0.05, 0.0, -0.05, 0.05])  # calmer, less focus push
    return np.zeros(4)


def trait_response(profile):
    """High trait anxiety -> lean the target calmer/lower-arousal regardless of
    the momentary state; low trait anxiety tolerates a touch more activation."""
    ta = _fget(profile, "trait_anxiety")
    if ta is None:
        return np.zeros(4)
    z = (float(ta) - 5.0) / 5.0
    return np.array([-0.06 * z, 0.0, -0.02 * z, 0.06 * z])


def cognition_response(profile):
    """Low baseline cognition -> simpler, calmer, more focus-supportive music."""
    cog = _fget(profile, "baseline_cognition")
    if cog is None:
        return np.zeros(4)
    z = (float(cog) - 7.0) / 7.0   # <0 means below-typical cognition
    if z < 0:
        return np.array([0.05 * z, 0.0, -0.06 * z, -0.04 * z])
    return np.zeros(4)


def motor_response(profile):
    """Greater motor impairment on a motor-priming goal -> stronger rhythmic
    priming (higher arousal/focus) to entrain gait."""
    motor = _fget(profile, "motor_function")
    if motor is None or profile.get("therapy_goal") != "Gait & Motor Priming":
        return np.zeros(4)
    impair = (7.0 - float(motor)) / 7.0   # >0 means impaired
    if impair > 0:
        return np.array([0.10 * impair, 0.0, 0.08 * impair, -0.03 * impair])
    return np.zeros(4)


def sensory_response(profile):
    """High sensory sensitivity -> gentler music (lower arousal, higher calm),
    the classic accommodation for autistic / hyper-aroused listeners."""
    sens = _fget(profile, "sensory_sensitivity")
    if sens is None:
        return np.zeros(4)
    z = (float(sens) - 5.0) / 5.0
    if z > 0:
        return np.array([-0.10 * z, 0.02 * z, -0.04 * z, 0.10 * z])
    return np.zeros(4)


def chronicity_response(profile):
    """Long-standing (chronic) illness -> slightly more conservative target;
    the iso-principle move is smaller because change is harder-won."""
    dur = _fget(profile, "illness_duration_years")
    if dur is None:
        return np.zeros(4)
    if float(dur) >= 10:
        return np.array([-0.03, -0.02, 0.0, 0.03])
    return np.zeros(4)


def life_event_response(profile):
    """An acute life stressor this session -> meet them where they are: pull the
    target toward soothing / lower demand for that session."""
    le = _fget(profile, "life_event", 0)
    try:
        le = float(le)
    except (TypeError, ValueError):
        le = 0.0
    if le >= 1:
        return np.array([-0.10, -0.03, -0.05, 0.10])
    return np.zeros(4)


def rich_ambiguity(profile):
    """Extra inter-rater spread contributed by the rich axes (harder cases)."""
    extra = 0.0
    if _fget(profile, "medication_adherence") == "non_adherent":
        extra += 0.03
    if _fget(profile, "archetype") == "relapsing_remitting":
        extra += 0.03
    ct, tod = _fget(profile, "chronotype"), _fget(profile, "time_of_day")
    if ct is not None and tod is not None and CHRONO_BEST_TIME.get(ct) != tod:
        extra += 0.015
    cog = _fget(profile, "baseline_cognition")
    if cog is not None and float(cog) <= 3:
        extra += 0.03
    try:
        if float(_fget(profile, "comorbidity_count", 0)) >= 2:
            extra += 0.03
    except (TypeError, ValueError):
        pass
    try:
        if float(_fget(profile, "life_event", 0)) >= 1:
            extra += 0.02
    except (TypeError, ValueError):
        pass
    return extra
