
# ====
# FINAL CORRECTED NeuroTunes Synthetic Data Generator
# 
# Fixes:
# 1. Proper type conversion for MySQL
# 2. Correct function parameter passing
# 3. Shorter mode values for database schema
# ====

import os
import json
import numpy as np
from datetime import datetime, timedelta
import uuid
from data_logger import DataLogger
import logging

logger = logging.getLogger(__name__)

class SyntheticDataGenerator:
    """
    Generates realistic synthetic feedback data for development testing
    """

    def __init__(self):
        self.data_logger = DataLogger()
        self.use_synthetic = os.getenv('USE_SYNTHETIC_DATA', 'false').lower() == 'true'

    def convert_numpy_types(self, data):
        """Convert numpy types to native Python types for MySQL compatibility"""
        if isinstance(data, dict):
            return {key: self.convert_numpy_types(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.convert_numpy_types(item) for item in data]
        elif isinstance(data, np.integer):
            return int(data)
        elif isinstance(data, np.floating):
            return float(data)
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif hasattr(data, 'item'):  # numpy scalar
            return data.item()
        else:
            return data

    def generate_realistic_patient_data(self):
        """Generate realistic patient data patterns"""
        diagnoses = ['depression', 'anxiety', 'post_stroke', 'parkinsons', 'wellness']
        therapy_goals = ['mood_improvement', 'stress_reduction', 'motor_function', 'cognitive']

        data = {
            'age': int(np.random.randint(25, 80)),
            'diagnosis': str(np.random.choice(diagnoses)),
            'therapy_goal': str(np.random.choice(therapy_goals)),
            'stress_level': int(np.random.randint(1, 11)),
            'sleep_quality': int(np.random.randint(1, 11)),
            'energy_level': int(np.random.randint(1, 11)),
            'mood_rating': int(np.random.randint(1, 11)),
            'session_number': int(np.random.randint(1, 20))
        }

        return self.convert_numpy_types(data)

    def generate_realistic_music_params(self):
        """Generate realistic music parameters with shorter mode values"""
        keys = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
        modes = ['major', 'minor', 'dorian']  # SHORTENED to fit database schema
        instruments = ['piano', 'strings', 'ambient', 'nature']

        data = {
            'tempo': int(np.random.randint(60, 140)),
            'key': str(np.random.choice(keys)),
            'mode': str(np.random.choice(modes)),
            'instrument': str(np.random.choice(instruments)),
            'complexity': float(np.random.uniform(0.2, 0.8)),
            'rhythm_stability': float(np.random.uniform(0.3, 0.9)),
            'dynamic_range': float(np.random.uniform(0.2, 0.7)),
            'duration': int(np.random.randint(30, 180))
        }

        return self.convert_numpy_types(data)

    def generate_correlated_feedback(self, patient_data, music_params):
        """Generate feedback that correlates with patient state and music parameters"""

        # Base rating influenced by patient state
        base_rating = 3.0

        # Positive correlations
        if patient_data['therapy_goal'] == 'mood_improvement' and music_params['mode'] == 'major':
            base_rating += 0.5
        if patient_data['stress_level'] > 7 and music_params['tempo'] < 80:
            base_rating += 0.3
        if patient_data['energy_level'] < 4 and music_params['tempo'] > 100:
            base_rating -= 0.4

        # Add some randomness
        rating = max(1, min(5, int(base_rating + np.random.normal(0, 0.5))))

        # Generate correlated mood/stress changes
        mood_changes = ['much_worse', 'worse', 'same', 'better', 'much_better']
        stress_changes = ['much_higher', 'higher', 'same', 'lower', 'much_lower']

        # Higher ratings correlate with better outcomes
        if rating >= 4:
            mood_change = str(np.random.choice(['same', 'better', 'much_better'], p=[0.3, 0.5, 0.2]))
            stress_change = str(np.random.choice(['same', 'lower', 'much_lower'], p=[0.4, 0.4, 0.2]))
        elif rating <= 2:
            mood_change = str(np.random.choice(['much_worse', 'worse', 'same'], p=[0.2, 0.5, 0.3]))
            stress_change = str(np.random.choice(['much_higher', 'higher', 'same'], p=[0.2, 0.4, 0.4]))
        else:
            mood_change = str(np.random.choice(mood_changes, p=[0.1, 0.2, 0.4, 0.2, 0.1]))
            stress_change = str(np.random.choice(stress_changes, p=[0.1, 0.2, 0.4, 0.2, 0.1]))

        # Listen duration correlates with rating
        base_duration = 30 + (rating - 1) * 15
        listen_duration = max(10, int(base_duration + np.random.normal(0, 10)))

        data = {
            'overall_rating': int(rating),
            'effectiveness_rating': int(max(1, min(5, rating + np.random.randint(-1, 2)))),
            'enjoyment_rating': int(max(1, min(5, rating + np.random.randint(-1, 2)))),
            'reported_feeling': f'Synthetic feedback for rating {rating}',
            'mood_change': mood_change,
            'energy_change': str(np.random.choice(['lower', 'same', 'higher'], p=[0.3, 0.4, 0.3])),
            'stress_change': stress_change,
            'feedback_text': f'Generated feedback for development testing - rating {rating}',
            'listen_duration_seconds': int(listen_duration),
            'replay_count': int(np.random.poisson(0.5)) if rating >= 4 else 0,
            'skipped_early': bool(rating <= 2 and np.random.random() < 0.6),
            'would_use_again': bool(rating >= 3)
        }

        return self.convert_numpy_types(data)

    def create_synthetic_session_with_feedback(self, num_tracks=3):
        """Create a complete synthetic session with generation and feedback data"""
        if not self.use_synthetic:
            logger.info("Synthetic data generation disabled (USE_SYNTHETIC_DATA=false)")
            return None

        session_id = str(uuid.uuid4())
        user_name = f"synthetic_user_{int(np.random.randint(1, 100))}"

        # Create session
        self.data_logger.create_session(user_name=user_name, session_id_from_request=session_id)

        patient_data = self.generate_realistic_patient_data()

        generation_ids = []
        for i in range(num_tracks):
            track_id = f"{session_id}_track_{i+1}"
            music_params = self.generate_realistic_music_params()

            # Log generation event
            log_id = self.data_logger.log_generation_event(
                session_id=session_id,
                track_id=track_id,
                patient_data=patient_data,
                music_params=music_params,
                user_name=user_name
            )

            if log_id:
                # Generate and log correlated feedback
                feedback = self.generate_correlated_feedback(patient_data, music_params)

                # FIXED: Proper parameter passing without conflicts
                success = self.data_logger.log_feedback_event(
                    log_id=log_id,
                    rating=feedback['overall_rating'],
                    reported_feeling=feedback['reported_feeling'],
                    feedback_text=feedback['feedback_text'],
                    user_name=user_name,
                    effectiveness_rating=feedback['effectiveness_rating'],
                    enjoyment_rating=feedback['enjoyment_rating'],
                    mood_change=feedback['mood_change'],
                    energy_change=feedback['energy_change'],
                    stress_change=feedback['stress_change'],
                    listen_duration_seconds=feedback['listen_duration_seconds'],
                    replay_count=feedback['replay_count'],
                    skipped_early=feedback['skipped_early'],
                    would_use_again=feedback['would_use_again']
                )

                if success:
                    generation_ids.append(log_id)
                else:
                    logger.error(f"Failed to log feedback for log_id {log_id}")
            else:
                logger.error(f"Failed to log generation event for track {track_id}")

        logger.info(f"Created synthetic session {session_id} with {len(generation_ids)} tracks")
        return session_id, generation_ids

    def generate_batch_synthetic_data(self, num_sessions=20):
        """Generate a batch of synthetic sessions for testing"""
        if not self.use_synthetic:
            logger.info("Synthetic data generation disabled")
            return []

        logger.info(f"Generating {num_sessions} synthetic sessions...")

        sessions = []
        successful_sessions = 0

        for i in range(num_sessions):
            try:
                session_data = self.create_synthetic_session_with_feedback()
                if session_data and session_data[1]:  # Check if tracks were created
                    sessions.append(session_data)
                    successful_sessions += 1
            except Exception as e:
                logger.error(f"Failed to create synthetic session {i}: {e}")

        logger.info(f"Generated {successful_sessions} successful synthetic sessions out of {num_sessions} attempts")
        return sessions

# Usage function for integration
def initialize_synthetic_data_if_enabled():
    """Initialize synthetic data generation if enabled via environment variable"""
    generator = SyntheticDataGenerator()

    if generator.use_synthetic:
        logger.info("USE_SYNTHETIC_DATA=true detected. Generating initial synthetic data...")
        sessions = generator.generate_batch_synthetic_data(num_sessions=25)
        logger.info(f"Synthetic data generation complete. Created {len(sessions)} sessions.")
    else:
        logger.info("Using real data mode (USE_SYNTHETIC_DATA=false)")

    return generator
