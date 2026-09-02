# ====
# NeuroTunes ML Server Application (app.py) - CLEAN VERSION WITH DIVERSITY FIXES
# ====

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
import logging
import threading
from datetime import datetime
import requests
import sys
import whisper
import torch
import librosa
import numpy as np
import re

# Add current directory to Python path
sys.path.append('/app')

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import components with error handling
try:
    from neurotunes_model import NeuroTunesModel
    model = NeuroTunesModel()
    logger.info("NeuroTunesModel loaded successfully")
except Exception as e:
    logger.error(f"Failed to load NeuroTunesModel: {e}")
    model = None

try:
    from music_generator import MusicGenerator
    music_gen = MusicGenerator()
    logger.info("MusicGenerator loaded successfully")
except Exception as e:
    logger.error(f"Failed to load MusicGenerator: {e}")
    music_gen = None

try:
    # Clinical safety-boundary validator (defense-in-depth over generated params)
    from safety_boundaries import safety_validator
    logger.info("SafetyBoundaryValidator loaded successfully")
except Exception as e:
    logger.error(f"Failed to load SafetyBoundaryValidator: {e}")
    safety_validator = None

try:
    # Use DataProcessor from shared common_utils
    from common_utils import DataProcessor
    data_proc = DataProcessor()
    logger.info("DataProcessor loaded from shared utils")
except Exception as e:
    logger.error(f"Failed to load DataProcessor from shared: {e}")
    # Fallback to local common_utils if shared doesn't work
    try:
        from common_utils import DataProcessor
        data_proc = DataProcessor()
        logger.info("DataProcessor loaded from local utils")
    except Exception as e2:
        logger.error(f"Failed to load DataProcessor: {e2}")
        data_proc = None

try:
    # Import DataLogger directly from local file
    from data_logger import DataLogger
    db_logger = DataLogger()
    logger.info("DataLogger loaded successfully")
except Exception as e:
    logger.error(f"Failed to load DataLogger: {e}")
    db_logger = None

# Load Whisper model (add this near other model loading)
whisper_model = whisper.load_model("base")

# Federation configuration
federation_mode = os.getenv('FEDERATION_MODE', 'coordinator')
site_id = os.getenv('SITE_ID', f'site_{uuid.uuid4().hex[:8]}')

# Service URLs
federation_service_url = os.getenv('FEDERATION_SERVICE_URL', 'http://federation-coordinator:5001')
versioning_service_url = os.getenv('VERSIONING_SERVICE_URL', 'http://model-versioning:5002')
clinical_service_url = os.getenv('CLINICAL_SERVICE_URL', 'http://clinical-dashboard:5003')

logger.info(f"ML Server starting in federation mode: {federation_mode}")

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        "service": "NeuroTunes ML Server",
        "status": "running",
        "federation_mode": federation_mode,
        "site_id": site_id
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with service status"""
    services_status = {
        'model': model is not None,
        'music_generator': music_gen is not None,
        'data_processor': data_proc is not None,
        'data_logger': db_logger is not None
    }
    
    # Check external services
    for service_name, url in [
        ('federation', federation_service_url),
        ('versioning', versioning_service_url),
        ('clinical', clinical_service_url)
    ]:
        try:
            response = requests.get(f"{url}/health", timeout=2)
            services_status[service_name] = response.status_code == 200
        except:
            services_status[service_name] = False

    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "services": services_status,
        "federation_mode": federation_mode,
        "site_id": site_id
    })

@app.route('/generate_music', methods=['POST'])
def generate_music():
    """Generate music with proper error handling and diversity fixes"""
    try:
        data = request.json
        logger.info(f"Received generation request: {data}")

        # Check if required components are available
        if not model or not music_gen or not data_proc:
            missing = []
            if not model: missing.append("model")
            if not music_gen: missing.append("music_generator") 
            if not data_proc: missing.append("data_processor")
            return jsonify({"error": f"Missing components: {missing}"}), 503

        session_id = data.get('session_id', str(uuid.uuid4()))

        # Create session if logger available
        if db_logger:
            db_logger.create_session(session_id_from_request=session_id)

        # Process patient data using DataProcessor
        processed_data = data_proc.process_patient_data(data)

        # Generate music with clinical assessment and diversity
        state_vector = model.predict(processed_data, data)
        
        # Create proper user profile with age, diagnosis, severity
        user_profile = {
            'age': data.get('age', 50),
            'diagnosis': data.get('diagnosis', 'general'),
            'severity': data.get('severity', 'moderate'),
            'session_number': data.get('session_number', 1)
        }
        
        # Create therapeutic targets from clinical parameters
        # Drive synthesis from the model's PREDICTED affective state so the
        # (retrained) EmotionNet actually shapes the music. state_vector is
        # [arousal, valence, focus, calm], each in [-1, 1]. Explicit request
        # fields still override for callers that want to set targets directly.
        _sv = state_vector.tolist() if hasattr(state_vector, 'tolist') else list(state_vector)
        _sv = (list(_sv) + [0.0, 0.0, 0.0, 0.0])[:4]
        _m_arousal, _m_valence, _m_focus, _m_calm = _sv
        therapeutic_targets = {
            'arousal': data.get('arousal', float(_m_arousal)),
            'valence': data.get('valence', float(_m_valence)),
            'focus': data.get('focus', float(_m_focus)),
            # generator's energy_state is the activation/energy axis, i.e. model
            # arousal; 'calm' (~ -arousal) is not consumed by the synth today.
            'energy_state': data.get('energy_state', float(_m_arousal))
        }

        # Use generate_therapeutic_music method with clinical assessment algorithms
        tracks = music_gen.generate_therapeutic_music(
            therapeutic_targets=therapeutic_targets,
            user_profile=user_profile,
            num_tracks=3
        )

        # Enforce clinical safety boundaries on generated parameters BEFORE
        # logging/returning, so unsafe values can never reach a patient.
        safety_report = {"safety_validated": False}
        if safety_validator:
            tracks, safety_report = safety_validator.validate_tracks(tracks)
            if safety_report.get("clamped"):
                logger.warning(f"Safety clamps applied: {safety_report['violations']}")

        # Log each track if logger available
        for track_info in tracks:
            if db_logger and track_info:
                log_id = db_logger.log_generation_event(
                    session_id=session_id,
                    track_id=track_info.get('track_id', ''),
                    patient_data=data,
                    music_params=track_info
                )
                track_info['log_id'] = log_id

        # Get clinical parameters for response
        clinical_params = model.map_to_music_params(state_vector, data.get('therapy_goal', 'relaxation'))

        response = {
            "session_id": session_id,
            "patient_state": state_vector.tolist(),
            "music_params": clinical_params,
            "tracks": tracks,
            "user_profile": user_profile,
            "therapeutic_targets": therapeutic_targets,
            "safety": safety_report,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Generated {len(tracks)} diverse therapeutic tracks for session {session_id}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in generate_music: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/generate_music_irb', methods=['POST'])
def generate_music_irb():
    """
    Generate music only for participants with active IRB informed consent.

    This mirrors /generate_music but first enforces a consent gate against the
    neurotunes_irb_consents store. If no active (non-withdrawn) consent exists
    for the supplied participant identifiers, generation is refused with HTTP
    403 so no therapeutic content is ever produced for an unconsented subject.
    The response adds `consent_verified` and `protocol_compliance` so the NUC
    server and clinical dashboard can record the compliance context.
    """
    try:
        data = request.json
        logger.info(f"Received IRB-gated generation request: {data}")

        # Check if required components are available
        if not model or not music_gen or not data_proc:
            missing = []
            if not model: missing.append("model")
            if not music_gen: missing.append("music_generator")
            if not data_proc: missing.append("data_processor")
            return jsonify({"error": f"Missing components: {missing}"}), 503

        session_id = data.get('session_id', str(uuid.uuid4()))

        # ---- IRB consent gate (hard requirement) ----
        if not db_logger:
            # Without the consent store we cannot prove consent; fail closed.
            return jsonify({
                "error": "Consent store unavailable; cannot verify IRB consent",
                "consent_verified": False,
                "irb_compliant": False,
            }), 403

        consent = db_logger.verify_consent(
            user_name=data.get('user_name'),
            user_id=data.get('user_id'),
            session_id=session_id,
        )
        if not consent.get("consent_verified"):
            logger.warning(
                f"IRB consent denied for session {session_id}: {consent.get('reason')}"
            )
            return jsonify({
                "error": f"IRB consent not verified: {consent.get('reason')}",
                "consent_verified": False,
                "irb_compliant": False,
            }), 403

        # Consent confirmed — proceed with the standard generation pipeline.
        if db_logger:
            db_logger.create_session(session_id_from_request=session_id)

        # Process patient data using DataProcessor
        processed_data = data_proc.process_patient_data(data)

        # Generate music with clinical assessment and diversity
        state_vector = model.predict(processed_data, data)

        user_profile = {
            'age': data.get('age', 50),
            'diagnosis': data.get('diagnosis', 'general'),
            'severity': data.get('severity', 'moderate'),
            'session_number': data.get('session_number', 1)
        }

        # Drive synthesis from the model's PREDICTED affective state so the
        # (retrained) EmotionNet actually shapes the music. state_vector is
        # [arousal, valence, focus, calm], each in [-1, 1]. Explicit request
        # fields still override for callers that want to set targets directly.
        _sv = state_vector.tolist() if hasattr(state_vector, 'tolist') else list(state_vector)
        _sv = (list(_sv) + [0.0, 0.0, 0.0, 0.0])[:4]
        _m_arousal, _m_valence, _m_focus, _m_calm = _sv
        therapeutic_targets = {
            'arousal': data.get('arousal', float(_m_arousal)),
            'valence': data.get('valence', float(_m_valence)),
            'focus': data.get('focus', float(_m_focus)),
            # generator's energy_state is the activation/energy axis, i.e. model
            # arousal; 'calm' (~ -arousal) is not consumed by the synth today.
            'energy_state': data.get('energy_state', float(_m_arousal))
        }

        tracks = music_gen.generate_therapeutic_music(
            therapeutic_targets=therapeutic_targets,
            user_profile=user_profile,
            num_tracks=3
        )

        # Enforce clinical safety boundaries before logging/returning.
        safety_report = {"safety_validated": False}
        if safety_validator:
            tracks, safety_report = safety_validator.validate_tracks(tracks)
            if safety_report.get("clamped"):
                logger.warning(f"Safety clamps applied (IRB): {safety_report['violations']}")

        # Log each track if logger available
        for track_info in tracks:
            if db_logger and track_info:
                log_id = db_logger.log_generation_event(
                    session_id=session_id,
                    track_id=track_info.get('track_id', ''),
                    patient_data=data,
                    music_params=track_info
                )
                track_info['log_id'] = log_id

        clinical_params = model.map_to_music_params(
            state_vector, data.get('therapy_goal', 'relaxation')
        )

        # Compliance context returned to the caller for audit/session storage.
        protocol_compliance = {
            "consent_id": consent.get("consent_id"),
            "irb_protocol_number": consent.get("irb_protocol_number"),
            "consent_version": consent.get("consent_version"),
            "verified_at": datetime.now().isoformat(),
        }

        response = {
            "session_id": session_id,
            "patient_state": state_vector.tolist(),
            "music_params": clinical_params,
            "tracks": tracks,
            "user_profile": user_profile,
            "therapeutic_targets": therapeutic_targets,
            "consent_verified": True,
            "protocol_compliance": protocol_compliance,
            "safety": safety_report,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(
            f"Generated {len(tracks)} IRB-compliant tracks for session {session_id} "
            f"(consent_id={consent.get('consent_id')})"
        )
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in generate_music_irb: {e}", exc_info=True)
        return jsonify({"error": str(e), "irb_compliant": False}), 500

@app.route('/feedback', methods=['POST'])
def handle_feedback():
    """Handle feedback with proper error handling"""
    try:
        feedback_data = request.json
        logger.info(f"Received feedback: {feedback_data}")

        if not db_logger:
            logger.warning("DataLogger not available, feedback not saved")
            return jsonify({"status": "warning", "message": "Feedback received but not saved"})

        log_id = feedback_data.get('log_id')
        rating = feedback_data.get('rating')
        reported_feeling = feedback_data.get('reported_feeling')
        feedback_text = feedback_data.get('feedback_text', '')

        if not log_id or rating is None:
            return jsonify({"error": "Missing log_id or rating"}), 400

        success = db_logger.log_feedback_event(log_id, rating, reported_feeling, feedback_text)
        
        if success:
            return jsonify({"status": "success", "message": "Feedback logged successfully"})
        else:
            return jsonify({"status": "error", "message": "Failed to log feedback"}), 500

    except Exception as e:
        logger.error(f"Error in handle_feedback: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Serve generated audio files"""
    try:
        file_path = os.path.join('output', filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Create directories on startup
os.makedirs('output', exist_ok=True)
os.makedirs('logs', exist_ok=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)