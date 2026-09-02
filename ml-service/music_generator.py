"""
Music Generator V2 - Enhanced Therapeutic Music Generation
Clinical improvements for neurological rehabilitation and mental health therapy

Clinical Enhancements V2:
- Evidence-based tempo ranges for specific neurological conditions
- Neuroplasticity-promoting harmonic progressions  
- Circadian rhythm synchronization
- Motor cortex activation patterns
- Cognitive load optimization based on age and severity
- Emotional regulation through validated musical parameters
- Binaural beats for brainwave entrainment (alpha, theta, beta, gamma)
- Age-appropriate complexity scaling
- Stroke rehabilitation tempo protocols
- ADHD attention-sustaining rhythmic patterns
- Depression mood-lifting harmonic structures
- Anxiety-reducing frequency selections
- Post-traumatic stress disorder sound therapy protocols
"""

import pretty_midi
import numpy as np
import os
from datetime import datetime
import subprocess
import random
import math

# Map a musical key name to its pitch class (semitone offset from C, 0-11).
# Covers all natural, sharp and flat spellings the generator can emit
# (see the key list in _create_clinical_params). Used to root a track at the
# CORRECT tonic. Previously the code used `hash(params['key']) % 12`, which is
# Python's *string* hash - not musical pitch - so the audible key never matched
# the labelled key, and (because Python salts str hashing per process) it even
# changed between server restarts. This table fixes both problems.
KEY_TO_PITCH_CLASS = {
    'C': 0, 'B#': 0,
    'C#': 1, 'Db': 1,
    'D': 2,
    'D#': 3, 'Eb': 3,
    'E': 4, 'Fb': 4,
    'F': 5, 'E#': 5,
    'F#': 6, 'Gb': 6,
    'G': 7,
    'G#': 8, 'Ab': 8,
    'A': 9,
    'A#': 10, 'Bb': 10,
    'B': 11, 'Cb': 11,
}


def key_pitch_class(key):
    """Return the pitch class (0-11) for a key name, defaulting to C (0)."""
    if isinstance(key, str):
        return KEY_TO_PITCH_CLASS.get(key.strip(), KEY_TO_PITCH_CLASS.get(key.strip().capitalize(), 0))
    return 0


class MusicGenerator:
    def __init__(self):
        # Clinical Evidence-Based Scales for Neurotherapy
        self.scales = {
            'major': [0, 2, 4, 5, 7, 9, 11],           # Mood elevation, positive affect
            'minor': [0, 2, 3, 5, 7, 8, 10],           # Emotional processing, introspection
            'pentatonic': [0, 2, 4, 7, 9],             # Universal appeal, cultural neutrality
            'blues': [0, 3, 5, 6, 7, 10],              # Emotional expression, catharsis
            'dorian': [0, 2, 3, 5, 7, 9, 10],          # Balanced mood, contemplative
            'mixolydian': [0, 2, 4, 5, 7, 9, 10],      # Uplifting without tension
            'lydian': [0, 2, 4, 6, 7, 9, 11],          # Dreamy, expansive feeling
            'phrygian': [0, 1, 3, 5, 7, 8, 10],        # Exotic, attention-grabbing
            'whole_tone': [0, 2, 4, 6, 8, 10],         # Cognitive stimulation
            'chromatic': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # Maximum complexity
        }

        self.therapeutic_durations = {
            'relaxation': (180, 300),      # 3-5 minutes
            'stimulation': (120, 240),     # 2-4 minutes
            'focus': (240, 360),           # 4-6 minutes
            'motor_recovery': (180, 300),  # 3-5 minutes
            'cognitive_rehab': (300, 480), # 5-8 minutes
            'sleep_induction': (600, 900)  # 10-15 minutes
        }

        # Clinical Therapeutic Chord Progressions
        self.therapeutic_progressions = {
            'relaxation': {
                'major': [[0, 2, 4], [5, 0, 2], [3, 5, 0], [0, 2, 4]],  # I-vi-IV-I (parasympathetic activation)
                'minor': [[0, 2, 4], [5, 0, 2], [1, 3, 5], [0, 2, 4]]   # i-VI-ii-i (emotional release)
            },
            'stimulation': {
                'major': [[0, 2, 4], [1, 3, 5], [4, 6, 1], [0, 2, 4]],  # I-ii-V-I (dopamine activation)
                'minor': [[0, 2, 4], [3, 5, 0], [4, 6, 1], [0, 2, 4]]   # i-III-V-i (energy without agitation)
            },
            'focus': {
                'major': [[0, 2, 4], [2, 4, 6], [1, 3, 5], [0, 2, 4]],  # I-iii-ii-I (attention networks)
                'minor': [[0, 2, 4], [2, 4, 6], [5, 0, 2], [0, 2, 4]]   # i-III-VI-i (sustained attention)
            },
            'motor_recovery': {
                'major': [[0, 2, 4], [4, 6, 1], [5, 0, 2], [0, 2, 4]],  # I-V-vi-I (motor cortex entrainment)
                'minor': [[0, 2, 4], [4, 6, 1], [3, 5, 0], [0, 2, 4]]   # i-V-III-i (movement facilitation)
            },
            'cognitive_rehab': {
                'major': [[0, 2, 4], [3, 5, 0], [1, 3, 5], [4, 6, 1], [0, 2, 4]],  # Extended progression for working memory
                'minor': [[0, 2, 4], [1, 3, 5], [5, 0, 2], [3, 5, 0], [0, 2, 4]]   # Complex pattern recognition
            },
            'emotional_regulation': {
                'major': [[0, 2, 4], [0, 2, 4, 6], [5, 0, 2], [3, 5, 0], [0, 2, 4]],  # Seventh chords for complexity
                'minor': [[0, 2, 4], [0, 2, 4, 6], [3, 5, 0], [1, 3, 5], [0, 2, 4]]   # Emotional depth
            }
        }

        # Evidence-Based Therapeutic Tempo Ranges (BPM) - Clinical Research
        self.therapeutic_tempos = {
            'relaxation': (60, 80),           # Heart rate synchronization, parasympathetic
            'stimulation': (100, 140),        # Arousal increase, sympathetic activation
            'focus': (80, 100),               # Optimal cognitive performance zone
            'motor_recovery': (90, 120),      # Gait training, movement therapy
            'gait_training': (100, 130),      # Specific for Parkinson's, stroke
            'cognitive_rehab': (70, 90),      # Working memory, attention training
            'depression': (80, 110),          # Mood elevation without overstimulation
            'anxiety': (60, 85),              # Anxiety reduction, calming
            'adhd': (90, 110),                # Attention without hyperactivity
            'ptsd': (65, 80),                 # Trauma-informed, non-triggering
            'autism': (70, 95),               # Sensory-friendly, predictable
            'dementia': (75, 95),             # Memory activation, familiar patterns
            'pain_management': (60, 75),      # Endorphin release, distraction
            'sleep_induction': (50, 70)       # Circadian rhythm entrainment
        }

        # Neurotherapeutic Binaural Beat Frequencies (Hz) - Clinical Applications
        self.binaural_frequencies = {
            'delta': (0.5, 4),        # Deep sleep, healing, pain relief
            'theta': (4, 8),          # Meditation, creativity, PTSD therapy
            'alpha': (8, 13),         # Relaxation, focus, anxiety reduction
            'beta': (13, 30),         # Alertness, concentration, cognitive enhancement
            'gamma': (30, 100),       # Cognitive processing, memory consolidation
            'schumann': 7.83,         # Earth resonance, grounding
            'solfeggio_396': 396,     # Fear release, guilt reduction
            'solfeggio_528': 528,     # DNA repair, love frequency
            'solfeggio_741': 741      # Problem solving, expression
        }

        # Clinical Instrument Selection for Therapeutic Goals
        self.therapeutic_instruments = {
            'relaxation': [0, 11, 48, 73, 88, 89],           # Piano, Vibraphone, Strings, Flute, Warm Pad
            'stimulation': [25, 26, 80, 81, 104, 120],       # Guitar, Jazz Guitar, Synth Lead, Square, Reverse Cymbal
            'focus': [0, 4, 5, 73, 74, 75],                  # Piano, E.Piano, Harpsichord, Flute, Recorder, Ocarina
            'motor_recovery': [0, 25, 32, 40, 127, 115],     # Piano, Guitar, Bass, Violin, Percussion, Woodblock
            'cognitive_rehab': [0, 8, 11, 48, 73, 72],       # Piano, Celesta, Vibraphone, Strings, Flute, Piccolo
            'depression': [0, 1, 25, 40, 73, 88],            # Piano, Bright Piano, Guitar, Violin, Flute, Warm Pad
            'anxiety': [0, 11, 48, 88, 89, 95],              # Piano, Vibraphone, Strings, Warm Pad, New Age Pad
            'adhd': [0, 25, 40, 73, 114, 115],               # Piano, Guitar, Violin, Flute, Agogo, Woodblock
            'ptsd': [0, 48, 73, 88, 89, 92],                 # Piano, Strings, Flute, Warm Pad, Choir Aahs
            'autism': [0, 8, 11, 73, 88, 89],                # Piano, Celesta, Vibraphone, Flute, Warm Pad
            'stroke': [0, 25, 32, 40, 115, 127],             # Piano, Guitar, Bass, Violin, Woodblock, Percussion
            'parkinson': [0, 25, 115, 116, 117, 127]         # Piano, Guitar, Woodblock, Taiko, Agogo, Percussion
        }

        # Age-Appropriate Complexity Scaling
        self.age_complexity_factors = {
            'child': (0.3, 0.6),      # Ages 3-12: Simple, engaging
            'teen': (0.5, 0.8),       # Ages 13-17: Moderate complexity
            'adult': (0.4, 1.0),      # Ages 18-64: Full range
            'elderly': (0.3, 0.7)     # Ages 65+: Reduced complexity
        }

        # Severity-Based Adjustments
        self.severity_adjustments = {
            'mild': 1.0,              # Full complexity
            'moderate': 0.7,          # Reduced complexity
            'severe': 0.4             # Minimal complexity
        }

        # Ensure output directory exists
        os.makedirs('output', exist_ok=True)

    # Add therapeutic phases:
    def create_therapeutic_phases(self, duration):
        return {
            'intro': (0, duration * 0.15),           # Gentle entry
            'development': (duration * 0.15, duration * 0.7),  # Main therapy
            'climax': (duration * 0.7, duration * 0.85),       # Peak effect
            'resolution': (duration * 0.85, duration)          # Gentle exit
        }

    def generate_therapeutic_music(self, therapeutic_targets, user_profile, num_tracks=3):
        """Generate multiple diverse therapeutic music tracks with clinical precision"""
        tracks = []
        
        # Clinical assessment and goal determination
        primary_goal = self._clinical_assessment(therapeutic_targets, user_profile)
        secondary_goals = self._identify_secondary_goals(therapeutic_targets, user_profile)
        
        # Generate tracks with maximum diversity
        for i in range(num_tracks):
            # Create clinically diverse parameters
            params = self._create_clinical_params(
                therapeutic_targets, 
                user_profile, 
                primary_goal, 
                secondary_goals, 
                i
            )
            
            track_name = f"therapeutic_track_{i+1}_{primary_goal}_{user_profile.get('diagnosis', 'general')}"
            track = self.generate_track(params, track_name)
            
            if track:
                # Add clinical metadata
                track['clinical_goal'] = primary_goal
                track['secondary_goals'] = secondary_goals
                track['user_diagnosis'] = user_profile.get('diagnosis', 'general')
                track['session_number'] = user_profile.get('session_number', 1)
                track['severity_level'] = user_profile.get('severity', 'moderate')
                tracks.append(track)
            
        return tracks

    def _clinical_assessment(self, therapeutic_targets, user_profile):
        """Clinical decision-making for primary therapeutic goal"""
        diagnosis = user_profile.get('diagnosis', 'general').lower()
        severity = user_profile.get('severity', 'moderate')
        session_number = user_profile.get('session_number', 1)
        
        # Evidence-based diagnosis mapping
        clinical_mapping = {
            'depression': 'stimulation' if session_number > 5 else 'emotional_regulation',
            'major_depression': 'stimulation',
            'anxiety': 'relaxation',
            'generalized_anxiety': 'relaxation',
            'panic_disorder': 'relaxation',
            'post_stroke': 'motor_recovery',
            'stroke': 'motor_recovery',
            'adhd': 'focus',
            'attention_deficit': 'focus',
            'ptsd': 'relaxation',
            'trauma': 'emotional_regulation',
            'parkinson': 'motor_recovery',
            'parkinsons': 'motor_recovery',
            'dementia': 'cognitive_rehab',
            'alzheimer': 'cognitive_rehab',
            'autism': 'focus',
            'asd': 'focus',
            'chronic_pain': 'relaxation',
            'fibromyalgia': 'relaxation',
            'insomnia': 'relaxation',
            'sleep_disorder': 'relaxation',
            'healthy': 'focus',
            'general': 'relaxation'
        }
        
        primary_goal = clinical_mapping.get(diagnosis, 'relaxation')
        
        # Severity adjustments
        if severity == 'severe' and primary_goal == 'stimulation':
            primary_goal = 'emotional_regulation'  # Gentler approach for severe cases
        
        return primary_goal

    def _identify_secondary_goals(self, therapeutic_targets, user_profile):
        """Identify secondary therapeutic goals for comprehensive treatment"""
        secondary = []
        
        arousal = therapeutic_targets.get('arousal', 0.5)
        valence = therapeutic_targets.get('valence', 0.0)
        focus = therapeutic_targets.get('focus', 0.0)
        energy = therapeutic_targets.get('energy_state', 0.0)
        
        # Multi-target approach
        if arousal < 0.3:
            secondary.append('stimulation')
        if valence < -0.3:
            secondary.append('emotional_regulation')
        if focus < 0.3:
            secondary.append('cognitive_rehab')
        if energy < -0.3:
            secondary.append('motor_recovery')
            
        return secondary[:2]  # Limit to 2 secondary goals

    def _create_clinical_params(self, therapeutic_targets, user_profile, primary_goal, secondary_goals, track_index):
        """Create clinically-informed parameters with maximum diversity"""
        
        # Extract clinical parameters
        arousal = therapeutic_targets.get('arousal', 0.5)
        valence = therapeutic_targets.get('valence', 0.0)
        focus = therapeutic_targets.get('focus', 0.0)
        energy = therapeutic_targets.get('energy_state', 0.0)
        
        age = user_profile.get('age', 50)
        severity = user_profile.get('severity', 'moderate')
        diagnosis = user_profile.get('diagnosis', 'general')
        session_number = user_profile.get('session_number', 1)
        
        # Age-based complexity
        if age < 13:
            age_group = 'child'
        elif age < 18:
            age_group = 'teen'
        elif age < 65:
            age_group = 'adult'
        else:
            age_group = 'elderly'
        
        complexity_range = self.age_complexity_factors[age_group]
        severity_factor = self.severity_adjustments[severity]
        
        # Create maximally diverse variations
        track_variations = [
            {  # Track 1: Primary therapeutic approach
                'scale_type': 'major' if valence > -0.2 else 'minor',
                'tempo_goal': primary_goal,
                'tempo_modifier': 1.0,
                'complexity_base': complexity_range[0],
                'instrument_set': 0,
                'binaural_type': 'alpha',
                'rhythm_pattern': 'standard',
                'harmonic_goal': primary_goal,
                'dynamic_profile': 'gentle'
            },
            {  # Track 2: Secondary goal emphasis with contrasting elements
                'scale_type': 'pentatonic' if arousal > 0.5 else 'dorian',
                'tempo_goal': secondary_goals[0] if secondary_goals else primary_goal,
                'tempo_modifier': 1.4 if energy > 0 else 0.75,
                'complexity_base': complexity_range[1],
                'instrument_set': 1,
                'binaural_type': 'beta' if focus > 0 else 'theta',
                'rhythm_pattern': 'syncopated' if arousal > 0.5 else 'legato',
                'harmonic_goal': secondary_goals[0] if secondary_goals else 'emotional_regulation',
                'dynamic_profile': 'varied'
            },
            {  # Track 3: Maximum contrast for diversity
                'scale_type': 'blues' if valence < -0.4 else 'lydian',
                'tempo_goal': 'cognitive_rehab' if age > 65 else 'motor_recovery',
                'tempo_modifier': 0.6 if severity == 'severe' else 1.6,
                'complexity_base': (complexity_range[0] + complexity_range[1]) / 2,
                'instrument_set': 2,
                'binaural_type': 'gamma' if diagnosis in ['dementia', 'alzheimer'] else 'delta',
                'rhythm_pattern': 'triplets' if primary_goal == 'motor_recovery' else 'sustained',
                'harmonic_goal': 'cognitive_rehab',
                'dynamic_profile': 'dramatic'
            }
        ]
        
        variation = track_variations[track_index % len(track_variations)]
        
        # Calculate clinical tempo
        tempo_goal = variation['tempo_goal']
        tempo_range = self.therapeutic_tempos.get(tempo_goal, (70, 100))
        base_tempo = random.randint(tempo_range[0], tempo_range[1])
        tempo = int(base_tempo * variation['tempo_modifier'])
        tempo = max(50, min(180, tempo))  # Clinical safety limits
        
        # Progressive session adjustments
        if session_number > 10:
            tempo = int(tempo * 1.1)  # Gradual increase for adaptation
        
        # Select therapeutic instruments
        instrument_goal = diagnosis if diagnosis in self.therapeutic_instruments else primary_goal
        instrument_options = self.therapeutic_instruments.get(instrument_goal, self.therapeutic_instruments['relaxation'])
        
        primary_instrument = instrument_options[variation['instrument_set'] % len(instrument_options)]
        instruments = [primary_instrument]
        
        # Add complementary instruments for complexity
        if variation['complexity_base'] > 0.6:
            secondary_instrument = instrument_options[(variation['instrument_set'] + 2) % len(instrument_options)]
            instruments.append(secondary_instrument)
        
        # Diverse key selection for neuroplasticity
        keys = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'Db', 'Eb', 'Gb', 'Ab', 'Bb']
        key = keys[(track_index * 3 + session_number) % len(keys)]  # Session-progressive key changes
        
        # Clinical complexity calculation
        base_complexity = variation['complexity_base'] * severity_factor
        session_progression = min(0.2, session_number * 0.02)  # Gradual complexity increase
        final_complexity = min(1.0, base_complexity + session_progression)
        
        params_out = {
            'duration': 180.0 + random.uniform(-30, 60),  # 25-35 second range
            'tempo': tempo,
            'key': key,
            'mode': variation['scale_type'],
            'complexity': final_complexity,
            'instruments': instruments,
            'therapy_goal': primary_goal,
            'secondary_goals': secondary_goals,
            'binaural_frequency': self._get_clinical_binaural_frequency(variation['binaural_type'], diagnosis),
            'rhythm_pattern': variation['rhythm_pattern'],
            'dynamic_range': self._calculate_dynamic_range(arousal, age_group, severity),
            'harmonic_complexity': self._calculate_harmonic_complexity(focus, age_group, session_number),
            'melodic_range': self._calculate_melodic_range(energy, age_group, diagnosis),
            'user_age': age,
            'diagnosis': diagnosis,
            'severity': severity,
            'session_number': session_number,
            'harmonic_goal': variation['harmonic_goal'],
            'dynamic_profile': variation['dynamic_profile']
        }

        # ------------------------------------------------------------------
        # AFFECT MAPPING (Stage-2 perceptual calibration)
        # Make the intended (valence, arousal) targets drive the musical
        # features that a perceptual critic (Music2Emo / MERT) — and human
        # listeners — actually respond to: tempo, dynamics, register,
        # instrument brightness, mode and note density. Without this, the
        # therapy-goal presets pin every track into a slow / low / mellow
        # "sad" corner regardless of the requested affect (validated with
        # the Stage-2 critic: arousal r≈0, perceived valence always < 0).
        # ------------------------------------------------------------------
        self._apply_affect_mapping(params_out, valence, arousal)
        return params_out

    @staticmethod
    def _lerp(x, x0, x1, y0, y1):
        """Clamped linear interpolation: map x in [x0,x1] onto [y0,y1]."""
        if x1 == x0:
            return y0
        t = (float(x) - x0) / (x1 - x0)
        t = max(0.0, min(1.0, t))
        return y0 + t * (y1 - y0)

    def _apply_affect_mapping(self, params, valence, arousal):
        """Override musical parameters so perceived affect tracks intent.

        valence, arousal are the intended targets in roughly [-1, 1] (the
        continuous EmotionNet output). Mappings below are monotonic so that
        raising intended valence/arousal reliably raises perceived
        valence/arousal, as measured by the Stage-2 Music2Emo critic.
        """
        v = max(-1.0, min(1.0, float(valence)))
        a = max(-1.0, min(1.0, float(arousal)))

        # --- Tempo: arousal is the dominant cue; valence gives a small lift.
        tempo = self._lerp(a, -1, 1, 50, 166) + self._lerp(v, -1, 1, -4, 8)
        params['tempo'] = int(max(46, min(172, round(tempo))))

        # --- Mode / scale: graded by valence (dark -> bright). Mode is the
        # single strongest, most reliable valence cue for the critic; keep it
        # to consonant families (avoid lydian's tense #4 at the top end).
        if v < -0.55:
            params['mode'] = 'minor'        # clearly sad
        elif v < -0.20:
            params['mode'] = 'dorian'       # subdued / introspective
        elif v < 0.15:
            params['mode'] = 'mixolydian'   # warm / mildly positive
        else:
            params['mode'] = 'major'        # clearly happy

        # --- Register offset (semitones). Keep this moderate: pushing the
        # melody too high reads as *tense* (low valence) to the critic, so
        # arousal drives most of the lift and valence only a little.
        reg = self._lerp(v, -1, 1, -4, 5) + self._lerp(a, -1, 1, -2, 6)
        params['register_offset'] = int(round(reg))

        # --- Dynamics: louder with arousal.
        params['dynamic_range'] = self._lerp(a, -1, 1, 0.30, 1.0)
        # Expose raw affect for velocity/energy scaling downstream.
        params['affect_valence'] = v
        params['affect_arousal'] = a

        # --- Note density (melody + chords): sparse/slow at low arousal,
        # busy/short at high arousal.
        if a < -0.4:
            params['note_durations'] = [1.5, 2.0, 3.0, 4.0]
            params['chord_durations'] = [4.0, 6.0]
        elif a < 0.1:
            params['note_durations'] = [1.0, 1.5, 2.0]
            params['chord_durations'] = [3.0, 4.0]
        elif a < 0.5:
            params['note_durations'] = [0.5, 0.75, 1.0, 1.5]
            params['chord_durations'] = [2.0, 3.0]
        else:
            params['note_durations'] = [0.25, 0.33, 0.5, 0.75]
            params['chord_durations'] = [1.0, 1.5, 2.0]

        # --- Instrument brightness ladder (GM programs), driven ONLY by
        # valence so it does not leak into perceived arousal. Warm pads/
        # strings read as sadder; mallets/bright keys read as happier.
        if v < -0.55:
            bright = [89, 48, 0]          # Warm Pad, Strings, Ac. Grand
        elif v < -0.20:
            bright = [0, 48, 89]          # Ac. Grand, Strings, Warm Pad
        elif v < 0.15:
            bright = [0, 11, 73]          # Ac. Grand, Vibraphone, Flute
        elif v < 0.55:
            bright = [11, 0, 73]          # Vibraphone, Ac. Grand, Flute
        else:
            bright = [11, 12, 0]          # Vibraphone, Marimba, Ac. Grand (warm-bright)
        params['instruments'] = bright if params.get('complexity', 0.5) <= 0.6 else bright + [bright[1]]

        # Keep melodic movement biased upward for positive valence.
        params['valence_bias'] = v

    def _get_clinical_binaural_frequency(self, binaural_type, diagnosis):
        """Get clinically appropriate binaural beat frequency"""
        
        # Diagnosis-specific binaural protocols
        clinical_binaural_mapping = {
            'depression': 'beta',      # Activation
            'anxiety': 'alpha',        # Calming
            'adhd': 'beta',           # Focus
            'ptsd': 'theta',          # Processing
            'insomnia': 'delta',      # Sleep
            'dementia': 'gamma',      # Cognitive
            'stroke': 'alpha',        # Recovery
            'parkinson': 'beta'       # Motor
        }
        
        # Override binaural type based on diagnosis
        if diagnosis in clinical_binaural_mapping:
            binaural_type = clinical_binaural_mapping[diagnosis]
        
        if binaural_type in self.binaural_frequencies:
            freq_range = self.binaural_frequencies[binaural_type]
            if isinstance(freq_range, tuple):
                return random.uniform(freq_range[0], freq_range[1])
            else:
                return freq_range
        
        return 10.0  # Default alpha frequency

    def _calculate_dynamic_range(self, arousal, age_group, severity):
        """Calculate clinically appropriate dynamic range"""
        base_range = 0.3 + (arousal * 0.4)
        
        # Age adjustments
        age_factors = {
            'child': 0.8,      # Moderate dynamics
            'teen': 1.0,       # Full range
            'adult': 1.0,      # Full range
            'elderly': 0.6     # Gentler dynamics
        }
        
        # Severity adjustments
        severity_factors = {
            'mild': 1.0,
            'moderate': 0.8,
            'severe': 0.5
        }
        
        return base_range * age_factors[age_group] * severity_factors[severity]

    def _calculate_harmonic_complexity(self, focus, age_group, session_number):
        """Calculate age and session-appropriate harmonic complexity"""
        base_complexity = 0.2 + (focus * 0.5)
        
        # Progressive complexity over sessions
        session_factor = 1.0 + (session_number * 0.05)
        
        # Age-appropriate limits
        age_limits = {
            'child': 0.6,
            'teen': 0.8,
            'adult': 1.0,
            'elderly': 0.7
        }
        
        complexity = base_complexity * session_factor
        return min(complexity, age_limits[age_group])

    def _calculate_melodic_range(self, energy, age_group, diagnosis):
        """Calculate appropriate melodic range for condition"""
        base_range = 12 + int(energy * 12)  # 12-24 semitones
        
        # Diagnosis-specific adjustments
        diagnosis_ranges = {
            'autism': 8,       # Limited range for comfort
            'dementia': 10,    # Familiar, simple ranges
            'stroke': 15,      # Moderate challenge
            'parkinson': 12,   # Steady, predictable
            'adhd': 18,        # Engaging variety
            'depression': 16   # Uplifting range
        }
        
        if diagnosis in diagnosis_ranges:
            base_range = diagnosis_ranges[diagnosis]
        
        # Age adjustments
        if age_group == 'elderly':
            base_range = min(base_range, 14)
        elif age_group == 'child':
            base_range = min(base_range, 16)
        
        return base_range

    def generate_track(self, params, track_name):
        """Generate a complete music track with clinical precision"""
        try:
            params = self._ensure_required_params(params)
            
            # Create MIDI file with clinical diversity
            midi_file = self.create_clinical_midi(params, track_name)
            
            if not midi_file or not os.path.exists(midi_file):
                print(f"Failed to create MIDI file for {track_name}")
                return None
            
            # Convert to audio
            audio_file = self.midi_to_audio(midi_file, track_name)
            
            return {
                'track_id': track_name,
                'filename': os.path.basename(audio_file) if audio_file else None,
                'midi_filename': os.path.basename(midi_file),
                'midi_file': midi_file,
                'audio_file': audio_file,
                'duration': params['duration'],
                'tempo': params['tempo'],
                'key': params['key'],
                'mode': params['mode'],
                'therapy_goal': params.get('therapy_goal', 'general'),
                'secondary_goals': params.get('secondary_goals', []),
                'binaural_frequency': params.get('binaural_frequency', 10),
                'clinical_complexity': params.get('complexity', 0.5),
                'user_diagnosis': params.get('diagnosis', 'general'),
                'session_number': params.get('session_number', 1),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating track {track_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def create_clinical_midi(self, params, track_name):
        """Create MIDI file with maximum clinical diversity"""
        try:
            midi = pretty_midi.PrettyMIDI(initial_tempo=params['tempo'])
            
            # Get scale and clinical parameters
            scale = self.scales[params['mode']]
            duration = params['duration']
            
            # Create main therapeutic instrument
            main_instrument = pretty_midi.Instrument(
                program=params['instruments'][0], 
                name=f"Therapeutic_{params['therapy_goal']}"
            )
            
            # Generate clinically diverse chord progression
            chords = self._generate_clinical_chords(params, duration, scale)
            for chord in chords:
                for note in chord['notes']:
                    midi_note = pretty_midi.Note(
                        velocity=chord['velocity'],
                        pitch=note,
                        start=chord['start'],
                        end=chord['end']
                    )
                    main_instrument.notes.append(midi_note)
            
            # Generate therapeutic melody
            melody_notes = self._generate_therapeutic_melody(params, duration, scale)
            for note in melody_notes:
                midi_note = pretty_midi.Note(
                    velocity=note['velocity'],
                    pitch=note['pitch'],
                    start=note['start'],
                    end=note['end']
                )
                main_instrument.notes.append(midi_note)
            
            midi.instruments.append(main_instrument)
            
            # Add complementary therapeutic instrument
            if len(params['instruments']) > 1:
                comp_instrument = self._create_therapeutic_complement(params, duration, scale)
                midi.instruments.append(comp_instrument)
            
            # Add clinical binaural beats. Skip on high-arousal targets: the
            # constant low warm-pad drone reads as "calm" and would suppress
            # the perceived energy we are deliberately raising.
            if params.get('binaural_frequency') and params.get('affect_arousal', -1.0) < 0.3:
                binaural_instrument = self._create_clinical_binaural_track(params, duration)
                midi.instruments.append(binaural_instrument)
            
            # Add rhythmic support for motor recovery
            if params.get('therapy_goal') in ['motor_recovery', 'gait_training']:
                rhythm_instrument = self._create_motor_rhythm_track(params, duration)
                midi.instruments.append(rhythm_instrument)
            
            # Save MIDI file
            filename = f"output/{track_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mid"
            midi.write(filename)
            
            return filename
            
        except Exception as e:
            print(f"Error creating clinical MIDI: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_clinical_chords(self, params, duration, scale):
        """Generate clinically optimized chord progressions"""
        chords = []
        therapy_goal = params.get('therapy_goal', 'relaxation')
        harmonic_goal = params.get('harmonic_goal', therapy_goal)
        rhythm_pattern = params.get('rhythm_pattern', 'standard')
        dynamic_profile = params.get('dynamic_profile', 'gentle')
        
        # Clinical chord duration patterns
        rhythm_durations = {
            'sustained': [4.0, 6.0],
            'standard': [2.0, 3.0],
            'syncopated': [1.0, 1.5, 2.0],
            'triplets': [2.0/3.0 * 3, 4.0/3.0 * 3],
            'legato': [3.0, 4.0, 5.0]
        }
        
        # Affect mapping supplies arousal-driven chord density when present.
        durations = params.get('chord_durations') or rhythm_durations.get(rhythm_pattern, [2.0])
        
        current_time = 0
        chord_index = 0
        
        # Get therapeutic progression. Affect-driven modes (dorian/mixolydian/
        # lydian) reuse the major/minor progression families by brightness.
        progressions = self.therapeutic_progressions.get(harmonic_goal, self.therapeutic_progressions['relaxation'])
        _bright_modes = {'major', 'mixolydian', 'lydian', 'pentatonic'}
        _prog_family = 'major' if params['mode'] in _bright_modes else 'minor'
        progression = progressions.get(params['mode'], progressions.get(_prog_family, progressions['major']))
        
        # Clinical base note calculation (shifted by affect register offset)
        register_offset = int(params.get('register_offset', 0))
        base_note = 48 + key_pitch_class(params['key']) + register_offset
        
        # Add octave variation for diversity
        octave_shift = (chord_index % 3) * 12  # Vary octaves
        base_note += octave_shift
        
        while current_time < duration:
            chord_duration = random.choice(durations)
            
            # Ensure we don't exceed duration
            if current_time + chord_duration > duration:
                chord_duration = duration - current_time
            
            chord_pattern = progression[chord_index % len(progression)]
            
            chord_notes = []
            for interval in chord_pattern:
                note = base_note + scale[interval % len(scale)]
                chord_notes.append(note)
                
                # Add clinical harmonic extensions
                harmonic_complexity = params.get('harmonic_complexity', 0.5)
                if harmonic_complexity > 0.7:
                    # Add seventh for emotional depth
                    seventh = note + scale[(interval + 6) % len(scale)]
                    if seventh not in chord_notes:
                        chord_notes.append(seventh)
                
                if harmonic_complexity > 0.8:
                    # Add ninth for cognitive stimulation
                    ninth = note + scale[(interval + 1) % len(scale)] + 12
                    if ninth not in chord_notes and ninth < 96:
                        chord_notes.append(ninth)
            
            # Clinical dynamic calculation
            velocity = self._calculate_clinical_velocity(
                dynamic_profile, 
                params.get('dynamic_range', 0.5),
                current_time / duration,  # Position in track
                params.get('session_number', 1)
            )
            
            chords.append({
                'notes': chord_notes,
                'start': current_time,
                'end': current_time + chord_duration,
                'velocity': velocity
            })
            
            current_time += chord_duration
            chord_index += 1
        
        return chords

    def _generate_therapeutic_melody(self, params, duration, scale):
        """Generate clinically optimized melodies"""
        melody = []
        rhythm_pattern = params.get('rhythm_pattern', 'standard')
        melodic_range = params.get('melodic_range', 12)
        therapy_goal = params.get('therapy_goal', 'relaxation')
        diagnosis = params.get('diagnosis', 'general')
        
        # Clinical note duration patterns
        rhythm_note_durations = {
            'legato': [1.0, 1.5, 2.0, 2.5],
            'standard': [0.5, 1.0, 1.5],
            'syncopated': [0.25, 0.5, 0.75, 1.0, 1.25],
            'triplets': [0.33, 0.67, 1.0, 1.33],
            'sustained': [2.0, 3.0, 4.0]
        }
        
        # Affect mapping supplies arousal-driven note density when present.
        note_durations = params.get('note_durations') or rhythm_note_durations.get(rhythm_pattern, [0.5, 1.0])
        
        current_time = 0
        register_offset = int(params.get('register_offset', 0))
        base_note = 60 + key_pitch_class(params['key']) + register_offset
        current_note_index = len(scale) // 2  # Start in middle of scale
        
        # Diagnosis-specific melodic patterns
        movement_patterns = {
            'depression': [-1, 0, 1, 2],      # Upward tendency
            'anxiety': [-1, 0, 1],            # Gentle movement
            'adhd': [-2, -1, 1, 2, 3],        # More variety
            'autism': [-1, 0, 1],             # Predictable
            'stroke': [-1, 1],                # Simple intervals
            'parkinson': [0, 1],              # Steady progression
            'dementia': [-1, 0, 1],           # Familiar patterns
            'general': [-2, -1, 0, 1, 2]      # Balanced
        }
        
        movements = movement_patterns.get(diagnosis, movement_patterns['general'])
        
        while current_time < duration:
            note_duration = random.choice(note_durations)
            
            # Ensure we don't exceed duration
            if current_time + note_duration > duration:
                note_duration = duration - current_time
            
            # Clinical melodic movement
            complexity = params.get('complexity', 0.5)
            if random.random() < complexity:
                movement = random.choice(movements)
            else:
                # Simple stepwise movement for lower complexity
                movement = random.choice([-1, 0, 1])
            
            current_note_index = max(0, min(len(scale)-1, current_note_index + movement))
            
            # Apply melodic range with clinical considerations
            octave_shifts = list(range(melodic_range // 12 + 1))
            octave_shift = random.choice(octave_shifts)
            pitch = base_note + scale[current_note_index] + (octave_shift * 12)
            
            # Clinical pitch range limits
            pitch = max(48, min(96, pitch))
            
            # Therapeutic velocity calculation
            velocity = self._calculate_therapeutic_velocity(
                params.get('dynamic_range', 0.5),
                current_time / duration,
                therapy_goal,
                complexity
            )
            
            melody.append({
                'pitch': pitch,
                'start': current_time,
                'end': current_time + note_duration,
                'velocity': velocity
            })
            
            current_time += note_duration
        
        return melody

    def _calculate_clinical_velocity(self, dynamic_profile, dynamic_range, position, session_number):
        """Calculate clinically appropriate velocity"""
        base_velocity = 40
        
        # Dynamic profile patterns
        if dynamic_profile == 'gentle':
            velocity_curve = 0.8 + 0.2 * math.sin(position * math.pi)  # Gentle arc
        elif dynamic_profile == 'varied':
            velocity_curve = 0.6 + 0.4 * math.sin(position * 2 * math.pi)  # More variation
        elif dynamic_profile == 'dramatic':
            velocity_curve = 0.5 + 0.5 * (1 - abs(position - 0.5) * 2)  # Peak in middle
        else:
            velocity_curve = 0.7  # Steady
        
        # Apply dynamic range
        velocity = base_velocity + int(40 * dynamic_range * velocity_curve)
        
        # Session progression (gradual increase in dynamics)
        session_boost = min(10, session_number)
        velocity += session_boost
        
        return max(20, min(110, velocity))

    def _calculate_therapeutic_velocity(self, dynamic_range, position, therapy_goal, complexity):
        """Calculate velocity for therapeutic melody"""
        base_velocity = 50
        
        # Therapy goal adjustments
        goal_adjustments = {
            'relaxation': 0.7,
            'stimulation': 1.3,
            'focus': 1.0,
            'motor_recovery': 1.2,
            'cognitive_rehab': 0.9,
            'emotional_regulation': 1.1
        }
        
        goal_factor = goal_adjustments.get(therapy_goal, 1.0)
        
        # Position-based dynamics (musical phrasing)
        phrase_curve = 0.8 + 0.2 * math.sin(position * 4 * math.pi)
        
        velocity = base_velocity * goal_factor * phrase_curve
        # dynamic_range is affect-driven (∝ arousal): let it dominate loudness
        # so higher intended arousal is perceived as more energetic.
        velocity += int(45 * dynamic_range)
        velocity += int(10 * dynamic_range * complexity)
        
        return max(30, min(120, int(velocity)))

    def _create_therapeutic_complement(self, params, duration, scale):
        """Create complementary therapeutic instrument"""
        instrument = pretty_midi.Instrument(
            program=params['instruments'][1], 
            name=f"Complement_{params.get('therapy_goal', 'general')}"
        )
        
        therapy_goal = params.get('therapy_goal', 'relaxation')
        
        # Therapy-specific complement patterns
        if therapy_goal in ['motor_recovery', 'gait_training']:
            # Steady bass pattern for motor entrainment
            return self._create_motor_bass_line(params, duration, scale, instrument)
        elif therapy_goal == 'cognitive_rehab':
            # Counter-melody for cognitive stimulation
            return self._create_cognitive_counter_melody(params, duration, scale, instrument)
        else:
            # Harmonic support
            return self._create_harmonic_support(params, duration, scale, instrument)

    def _create_motor_bass_line(self, params, duration, scale, instrument):
        """Create bass line for motor recovery"""
        base_note = 36 + (key_pitch_class(params['key']))
        note_duration = 60.0 / params['tempo']  # Quarter note duration
        
        current_time = 0
        scale_index = 0
        
        while current_time < duration:
            pitch = base_note + scale[scale_index % len(scale)]
            velocity = 40 + int(20 * params.get('complexity', 0.5))
            
            note = pretty_midi.Note(
                velocity=velocity,
                pitch=pitch,
                start=current_time,
                end=current_time + note_duration
            )
            instrument.notes.append(note)
            
            current_time += note_duration
            scale_index += 1
        
        return instrument

    def _create_cognitive_counter_melody(self, params, duration, scale, instrument):
        """Create counter-melody for cognitive stimulation"""
        base_note = 72 + (key_pitch_class(params['key']))  # Higher octave
        note_durations = [0.75, 1.0, 1.5]  # Varied durations for complexity
        
        current_time = 0
        scale_index = len(scale) - 1  # Start from top of scale
        
        while current_time < duration:
            note_duration = random.choice(note_durations)
            
            if current_time + note_duration > duration:
                note_duration = duration - current_time
            
            # Descending pattern with variations
            movement = random.choice([-2, -1, 0])
            scale_index = max(0, scale_index + movement)
            
            pitch = base_note + scale[scale_index]
            velocity = 35 + int(15 * params.get('harmonic_complexity', 0.5))
            
            note = pretty_midi.Note(
                velocity=velocity,
                pitch=pitch,
                start=current_time,
                end=current_time + note_duration
            )
            instrument.notes.append(note)
            
            current_time += note_duration
        
        return instrument

    def _create_harmonic_support(self, params, duration, scale, instrument):
        """Create harmonic support instrument"""
        base_note = 48 + (key_pitch_class(params['key']))
        chord_duration = 3.0
        
        current_time = 0
        chord_index = 0
        
        # Simple harmonic rhythm
        while current_time < duration:
            if current_time + chord_duration > duration:
                chord_duration = duration - current_time
            
            # Play root and fifth
            root_index = chord_index % len(scale)
            fifth_index = (chord_index + 4) % len(scale)
            
            root_pitch = base_note + scale[root_index]
            fifth_pitch = base_note + scale[fifth_index]
            
            velocity = 25 + int(15 * params.get('dynamic_range', 0.5))
            
            for pitch in [root_pitch, fifth_pitch]:
                note = pretty_midi.Note(
                    velocity=velocity,
                    pitch=pitch,
                    start=current_time,
                    end=current_time + chord_duration
                )
                instrument.notes.append(note)
            
            current_time += chord_duration
            chord_index += 1
        
        return instrument

    def _create_clinical_binaural_track(self, params, duration):
        """Create clinical binaural beat track"""
        instrument = pretty_midi.Instrument(program=89, name="Clinical_Binaural")  # Warm pad
        
        # Clinical binaural parameters
        base_freq = 200  # Base frequency in Hz
        binaural_freq = params.get('binaural_frequency', 10)
        
        # Convert to MIDI notes (approximate)
        base_note = int(12 * math.log2(base_freq / 440) + 69)
        
        # Create binaural pair with clinical precision
        left_note = pretty_midi.Note(
            velocity=20,  # Very low volume for subliminal effect
            pitch=base_note,
            start=0,
            end=duration
        )
        
        # Right ear frequency = base + binaural frequency
        right_freq = base_freq + binaural_freq
        right_note_pitch = int(12 * math.log2(right_freq / 440) + 69)
        
        right_note = pretty_midi.Note(
            velocity=20,
            pitch=right_note_pitch,
            start=0,
            end=duration
        )
        
        instrument.notes.extend([left_note, right_note])
        return instrument

    def _create_motor_rhythm_track(self, params, duration):
        """Create rhythmic track for motor recovery"""
        instrument = pretty_midi.Instrument(program=115, name="Motor_Rhythm", is_drum=False)  # Woodblock
        
        # Motor entrainment rhythm
        beat_duration = 60.0 / params['tempo']  # Quarter note
        
        current_time = 0
        beat_count = 0
        
        while current_time < duration:
            # Accent every 4th beat
            velocity = 60 if beat_count % 4 == 0 else 40
            
            note = pretty_midi.Note(
                velocity=velocity,
                pitch=60,  # Middle C
                start=current_time,
                end=current_time + 0.1  # Short percussive note
            )
            instrument.notes.append(note)
            
            current_time += beat_duration
            beat_count += 1
        
        return instrument

    def _ensure_required_params(self, params):
        """Ensure all required clinical parameters exist"""
        defaults = {
            'duration': 30.0,
            'instruments': [0],
            'tempo': 80,
            'key': 'C',
            'mode': 'major',
            'complexity': 0.5,
            'therapy_goal': 'relaxation',
            'secondary_goals': [],
            'rhythm_pattern': 'standard',
            'dynamic_range': 0.5,
            'harmonic_complexity': 0.5,
            'melodic_range': 12,
            'binaural_frequency': 10.0,
            'diagnosis': 'general',
            'severity': 'moderate',
            'session_number': 1,
            'harmonic_goal': 'relaxation',
            'dynamic_profile': 'gentle'
        }
        
        for key, default_value in defaults.items():
            if key not in params:
                params[key] = default_value
        
        return params

    def midi_to_audio(self, midi_file, track_name):
        """Convert MIDI to audio using FluidSynth"""
        try:
            audio_filename = midi_file.replace('.mid', '.wav')
            
            if not self._check_fluidsynth():
                print("FluidSynth not available, returning MIDI file only")
                return None
            
            # -g raises FluidSynth's synth gain from its default of 0.2. The
            # therapeutic MIDI uses low note velocities (~20-44/127), so with the
            # default gain the rendered WAV comes out near-silent (~-54 dBFS RMS).
            cmd = [
                'fluidsynth',
                '-ni',
                '-g', '2.0',
                '/usr/share/sounds/sf2/FluidR3_GM.sf2',
                midi_file,
                '-F', audio_filename,
                '-r', '44100'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(audio_filename):
                # Peak-normalize the rendered WAV to a healthy playback level.
                # FluidSynth gain alone is not enough to guarantee a consistent
                # loudness across tracks, so we run the repo's existing, safe
                # (no-clipping, fade in/out) post-processor. This never raises
                # into the generation path: on any failure we keep the raw WAV.
                self._normalize_audio(audio_filename)
                return audio_filename
            else:
                print(f"FluidSynth error: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error converting MIDI to audio: {str(e)}")
            return None

    def _check_fluidsynth(self):
        """Check if FluidSynth is available"""
        try:
            result = subprocess.run(['which', 'fluidsynth'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def _normalize_audio(self, audio_filename, target_dbfs=-1.0):
        """Peak-normalize a rendered WAV to a healthy playback level.

        Delegates to the co-located audio_postprocess.normalize_wav
        (stdlib wave + numpy, no clipping, short fade in/out). This is best-effort:
        any import or processing failure is swallowed so the raw WAV is still
        returned and generation never breaks.
        """
        try:
            try:
                from audio_postprocess import normalize_wav
            except ImportError:
                # Fallback when the mlServer dir isn't on sys.path: add this
                # file's own directory (where audio_postprocess.py lives) explicitly.
                import sys
                _here = os.path.dirname(os.path.abspath(__file__))
                if _here not in sys.path:
                    sys.path.insert(0, _here)
                from audio_postprocess import normalize_wav
            normalize_wav(audio_filename, target_dbfs=target_dbfs, inplace=True)
        except Exception as e:
            print(f"Audio normalization skipped ({str(e)}); returning raw WAV")

    # Legacy methods for backward compatibility
    def add_variation(self, base_params, variation_index):
        """Legacy method - now handled by clinical parameter generation"""
        return self._create_clinical_params({}, {}, 'relaxation', [], variation_index)

    def create_midi(self, params, track_name):
        """Legacy method - redirects to clinical MIDI creation"""
        return self.create_clinical_midi(params, track_name)

    def generate_chord_progression(self, params, duration):
        """Legacy method - redirects to clinical chord generation"""
        scale = self.scales.get(params.get('mode', 'major'), self.scales['major'])
        return self._generate_clinical_chords(params, duration, scale)

    def generate_melody(self, params, duration, scale):
        """Legacy method - redirects to therapeutic melody generation"""
        return self._generate_therapeutic_melody(params, duration, scale)

    def add_strings(self, params, duration, scale):
        """Legacy method - redirects to therapeutic complement creation"""
        instrument = pretty_midi.Instrument(program=48, name='Strings')
        return self._create_harmonic_support(params, duration, scale, instrument)
