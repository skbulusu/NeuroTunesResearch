# ====
# NeuroTunes Data Logger (Fully Compatible with netraidb Schema)
#
# This module provides a dedicated DataLogger class that perfectly matches
# the comprehensive netraidb schema structure, including user integration,
# rich feedback collection, and proper session management.
# ====

import os
import mysql.connector
from mysql.connector import Error
import json
import logging
from datetime import datetime
import uuid

# Configure logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLogger:
    """
    Handles all database connections and logging operations for NeuroTunes,
    fully compatible with the comprehensive netraidb schema.
    """
    def __init__(self):
        self.connection = None
        self.db_config = {
            'host': os.getenv('DB_HOST', 'define_db'),
            'database': os.getenv('DB_DATABASE', 'netraidb'),
            'user': os.getenv('DB_USER', 'john'),
            'password': os.getenv('DB_PASSWORD', 'john'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'autocommit': False,
            'connection_timeout': 10,
            'pool_reset_session': True
        }
        self._connect()

    def _connect(self):
        """Establish database connection with retry logic."""
        try:
            if self.connection and self.connection.is_connected():
                return True
                
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                logger.info(f"Successfully connected to netraidb database.")
                return True
        except Error as e:
            logger.error(f"Error while connecting to MySQL: {e}")
            self.connection = None
            return False

    def _ensure_connection(self):
        """Ensure database connection is active, reconnect if needed."""
        try:
            if not self.connection or not self.connection.is_connected():
                logger.warning("Database connection lost, attempting to reconnect...")
                return self._connect()
            
            # Test the connection with a simple query
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
            
        except Error as e:
            logger.warning(f"Connection test failed: {e}, reconnecting...")
            return self._connect()

    def get_or_create_user(self, user_name="anonymous"):
        """
        Gets existing user or creates anonymous user for NeuroTunes sessions.
        Returns user_id.
        """
        if not self._ensure_connection():
            return None

        cursor = self.connection.cursor()
        try:
            # Try to find existing user
            cursor.execute("SELECT id FROM users WHERE user_name = %s", (user_name,))
            result = cursor.fetchone()

            if result:
                return result[0]
            else:
                # Create anonymous user for NeuroTunes
                cursor.execute("""
                INSERT INTO users (user_name, hashed_password, points, average_rating)
                VALUES (%s, 'neurotunes_anonymous', 0, 0.0)
                """, (user_name,))
                self.connection.commit()
                return cursor.lastrowid

        except Error as e:
            logger.error(f"Error managing user {user_name}: {e}")
            return None
        finally:
            cursor.close()

    def verify_consent(self, user_name=None, user_id=None, session_id=None):
        """
        Verify active IRB informed consent for a participant.

        A consent is valid when a row in neurotunes_irb_consents exists with
        consent_given = 1 AND withdrawal_timestamp IS NULL, matching any of the
        provided identifiers (session_id, user_id, or user_name). session_id is
        the most specific, so it is preferred when supplied.

        Returns a dict:
            {
              "consent_verified": bool,
              "consent_id": int | None,
              "irb_protocol_number": str | None,
              "consent_version": str | None,
              "reason": str            # human-readable status
            }
        The generation endpoint treats consent_verified == False as a hard 403.
        """
        result = {
            "consent_verified": False,
            "consent_id": None,
            "irb_protocol_number": None,
            "consent_version": None,
            "reason": "no matching consent record",
        }

        if not (user_name or user_id or session_id):
            result["reason"] = "no participant identifier supplied"
            return result

        if not self._ensure_connection():
            result["reason"] = "consent store unavailable"
            return result

        cursor = self.connection.cursor(dictionary=True)
        try:
            clauses = []
            params = []
            if session_id:
                clauses.append("session_id = %s")
                params.append(session_id)
            if user_id is not None:
                clauses.append("user_id = %s")
                params.append(user_id)
            if user_name:
                clauses.append("user_name = %s")
                params.append(user_name)

            # Match ANY supplied identifier; require an active (non-withdrawn) grant.
            query = (
                "SELECT consent_id, consent_given, withdrawal_timestamp, "
                "irb_protocol_number, consent_version "
                "FROM neurotunes_irb_consents "
                "WHERE (" + " OR ".join(clauses) + ") "
                "AND consent_given = 1 AND withdrawal_timestamp IS NULL "
                "ORDER BY consent_timestamp DESC LIMIT 1"
            )
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()

            if row:
                result.update({
                    "consent_verified": True,
                    "consent_id": row.get("consent_id"),
                    "irb_protocol_number": row.get("irb_protocol_number"),
                    "consent_version": row.get("consent_version"),
                    "reason": "active consent on file",
                })
            else:
                result["reason"] = "consent not granted or has been withdrawn"
        except Error as e:
            logger.error(f"Error verifying consent: {e}")
            result["reason"] = f"consent lookup error: {e}"
        finally:
            cursor.close()

        return result

    def create_session(self, user_name="anonymous", session_id_from_request=None):
        """
        Creates a new music session if it doesn't already exist.
        Uses the session_id from the frontend to ensure consistency.
        This operation is idempotent.
        """
        if not self._ensure_connection():
            return None

        session_id = session_id_from_request or str(uuid.uuid4())
        user_id = self.get_or_create_user(user_name)

        if not user_id:
            return None

        cursor = self.connection.cursor()
        try:
            # IDEMPOTENCY CHECK: See if the session already exists.
            cursor.execute("SELECT session_id FROM neurotunes_music_sessions WHERE session_id = %s", (session_id,))
            if cursor.fetchone():
                logger.info(f"Session {session_id} already exists. Proceeding.")
                return session_id

            # If not, create it.
            cursor.execute("""
            INSERT INTO neurotunes_music_sessions
            (session_id, user_id, user_name, session_name)
            VALUES (%s, %s, %s, %s)
            """, (session_id, user_id, user_name, f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"))

            self.connection.commit()
            logger.info(f"Created new session {session_id} for user {user_name}")
            return session_id
        except Error as e:
            logger.error(f"Failed to create or find session: {e}")
            return None
        finally:
            cursor.close()

    def log_generation_event(self, session_id, track_id, patient_data, music_params, user_name="anonymous"):
        """
        Logs music generation event with full schema compatibility.
        Returns log_id or None on failure.
        """
        if not self._ensure_connection():
            logger.error("Cannot log generation event: No database connection.")
            return None

        user_id = self.get_or_create_user(user_name)
        if not user_id:
            return None

        cursor = self.connection.cursor()
        try:
            # Extract specific fields from music_params for indexing
            tempo = music_params.get('tempo', 120)
            music_key = music_params.get('key', 'C')
            mode = music_params.get('mode', 'major')
            therapy_goal = patient_data.get('therapy_goal', 'General Wellness')
            duration = music_params.get('duration', 60)

            # Generate filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            midi_filename = f"{track_id}_{timestamp}.mid"
            audio_filename = f"{track_id}_{timestamp}.wav"

            query = """
            INSERT INTO neurotunes_generation_log
            (session_id, user_id, user_name, track_id, patient_data, music_params,
            tempo, music_key, mode, therapy_goal, duration, midi_filename, audio_filename,
            model_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                session_id, user_id, user_name, track_id,
                json.dumps(patient_data), json.dumps(music_params),
                tempo, music_key, mode, therapy_goal, duration,
                midi_filename, audio_filename, "1.0.0"
            ))

            self.connection.commit()
            log_id = cursor.lastrowid
            logger.info(f"Successfully logged generation event with log_id: {log_id}")
            return log_id

        except Error as e:
            logger.error(f"Failed to log generation event: {e}")
            self.connection.rollback()
            return None
        finally:
            cursor.close()

    def log_feedback_event(self, log_id, rating, reported_feeling, feedback_text, user_name="anonymous", **kwargs):
        """
        Logs comprehensive user feedback matching the rich schema structure.
        Handles both log_id (int) and track_id (string) formats.
        """
        if not self._ensure_connection():
            logger.error("Cannot log feedback event: No database connection.")
            return False

        user_id = self.get_or_create_user(user_name)
        if not user_id:
            return False

        cursor = self.connection.cursor()
        try:
            # Handle track_id format (convert to generation_log_id)
            generation_log_id = None
            if isinstance(log_id, str) and '_track_' in log_id:
                # Extract session_id and track number from track_id
                parts = log_id.split('_track_')
                if len(parts) == 2:
                    session_part = parts[0]
                    track_num = parts[1]

                    # Find the generation_log_id for this track
                    cursor.execute("""
                    SELECT log_id FROM neurotunes_generation_log
                    WHERE session_id LIKE %s AND track_id LIKE %s
                    ORDER BY generation_time DESC LIMIT 1
                    """, (f"%{session_part}%", f"%track_{track_num}%"))

                    result = cursor.fetchone()
                    if result:
                        generation_log_id = result[0]
            else:
                generation_log_id = log_id

            if not generation_log_id:
                logger.error(f"Could not resolve generation_log_id for {log_id}")
                return False

            # Extract additional feedback parameters
            effectiveness_rating = kwargs.get('effectiveness_rating', rating)
            enjoyment_rating = kwargs.get('enjoyment_rating', rating)
            mood_change = kwargs.get('mood_change', 'same')
            energy_change = kwargs.get('energy_change', 'same')
            stress_change = kwargs.get('stress_change', 'same')
            listen_duration = kwargs.get('listen_duration_seconds', 30)
            replay_count = kwargs.get('replay_count', 0)
            skipped_early = kwargs.get('skipped_early', False)
            would_use_again = kwargs.get('would_use_again', True)

            query = """
            INSERT INTO neurotunes_feedback_log
            (generation_log_id, user_id, user_name, overall_rating, effectiveness_rating,
            enjoyment_rating, reported_feeling, mood_change, energy_change, stress_change,
            feedback_text, listen_duration_seconds, replay_count, skipped_early, would_use_again)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                generation_log_id, user_id, user_name, rating, effectiveness_rating,
                enjoyment_rating, reported_feeling, mood_change, energy_change, stress_change,
                feedback_text, listen_duration, replay_count, skipped_early, would_use_again
            ))

            self.connection.commit()
            logger.info(f"Successfully logged feedback for generation_log_id: {generation_log_id}")
            return True

        except Error as e:
            logger.error(f"Failed to log feedback event for {log_id}: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def get_user_statistics(self, user_name):
        """
        Retrieves comprehensive user statistics using the dashboard view.
        """
        if not self._ensure_connection():
            return None

        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute("""
            SELECT * FROM neurotunes_user_dashboard_data
            WHERE user_name = %s
            """, (user_name,))

            return cursor.fetchone()

        except Error as e:
            logger.error(f"Failed to get user statistics for {user_name}: {e}")
            return None
        finally:
            cursor.close()

    def get_rlhf_training_data(self, limit=1000):
        """
        Retrieves training data for RLHF using the specialized view.
        """
        if not self._ensure_connection():
            return []

        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute("""
            SELECT * FROM neurotunes_rlhf_training_data
            ORDER BY feedback_time DESC
            LIMIT %s
            """, (limit,))

            return cursor.fetchall()

        except Error as e:
            logger.error(f"Failed to get RLHF training data: {e}")
            return []
        finally:
            cursor.close()

    def log_model_training(self, model_version, training_data_count, validation_accuracy, hyperparameters):
        """
        Logs model training run information.
        """
        if not self._ensure_connection():
            return None

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
            INSERT INTO neurotunes_reward_model_training
            (model_version, training_data_count, validation_accuracy, hyperparameters, training_status)
            VALUES (%s, %s, %s, %s, 'completed')
            """, (model_version, training_data_count, validation_accuracy, json.dumps(hyperparameters)))

            self.connection.commit()
            training_id = cursor.lastrowid
            logger.info(f"Logged model training run: {training_id}")
            return training_id

        except Error as e:
            logger.error(f"Failed to log model training: {e}")
            return None
        finally:
            cursor.close()

    def __del__(self):
        """Destructor to ensure the database connection is closed."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("MySQL connection closed.")
