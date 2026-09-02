from flask import Flask, request, jsonify
from federation_coordinator import FederationCoordinator
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Initialize federation coordinator
min_sites = int(os.getenv('MIN_SITES', '2'))
max_sites = int(os.getenv('MAX_SITES', '10'))
privacy_epsilon = float(os.getenv('PRIVACY_EPSILON', '1.0'))

coordinator = FederationCoordinator(
    min_sites=min_sites,
    max_sites=max_sites,
    privacy_epsilon=privacy_epsilon
)

logger.info(f"Federation Coordinator initialized with {min_sites}-{max_sites} sites")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "federation-coordinator",
        "registered_sites": len(coordinator.registered_sites),
        "active_sites": len(coordinator.active_sites),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/federation/register', methods=['POST'])
def register_site():
    """Register a new site with the federation coordinator."""
    try:
        data = request.json
        site_name = data.get('site_name', 'Unknown Site')
        location = data.get('location', 'Unknown Location')
        patient_count = data.get('patient_count', 100)
        
        site_id = coordinator.register_site(site_name, location, patient_count)
        
        logger.info(f"Registered new site: {site_name}")
        return jsonify({
            "status": "success",
            "message": f"Site {site_name} registered successfully",
            "site_id": site_id
        })

    except Exception as e:
        logger.error(f"Error in register_site: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/federation/start_round', methods=['POST'])
def start_federation_round():
    """Start a new federated learning round."""
    try:
        data = request.json or {}
        target_sites = data.get('target_sites')

        round_id = coordinator.start_federation_round(target_sites)

        logger.info(f"Started federation round: {round_id}")
        return jsonify({
            "status": "success",
            "round_id": round_id,
            "message": "Federation round started successfully"
        })

    except Exception as e:
        logger.error(f"Error in start_federation_round: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/federation/status', methods=['GET'])
def federation_status():
    """Get current federation status."""
    try:
        status = coordinator.get_federation_status()
        return jsonify({
            "status": "success",
            "data": status,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in federation_status: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/federation/heartbeat', methods=['POST'])
def site_heartbeat():
    """Process heartbeat from a site."""
    try:
        data = request.json
        site_id = data.get('site_id')
        
        if not site_id:
            return jsonify({"error": "site_id required"}), 400
        
        status_update = {
            'status': 'active',
            'patient_count': data.get('patient_count', 100),
            'model_version': data.get('model_version', '1.0.0'),
            'privacy_budget': data.get('privacy_budget', 1.0)
        }
        
        success = coordinator.site_heartbeat(site_id, status_update)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Heartbeat received from {site_id}"
            })
        else:
            return jsonify({"error": "Site not registered"}), 404
    
    except Exception as e:
        logger.error(f"Error processing heartbeat: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('FEDERATION_PORT', '5001')), debug=True)
