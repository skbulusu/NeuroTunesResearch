from flask import Flask, request, jsonify
import os
import logging
from datetime import datetime
import json
from typing import Dict, List, Optional

# Ensure logs directory exists
os.makedirs('/app/logs', exist_ok=True)

# Import shared utilities
import sys
#sys.path.append('/app/shared')
from common_utils import setup_logging, validate_request
from rabbitmq_integration import RabbitMQClient

# Import the proper multi-site versioning system
from multi_site_versioning import MultiSiteVersionManager

app = Flask(__name__)
logger = setup_logging('versioning-service')

# Initialize the proper version manager (uses MySQL netraidb)
try:
    version_manager = MultiSiteVersionManager()
    logger.info("Multi-Site Version Manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize version manager: {e}")
    version_manager = None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy' if version_manager else 'unhealthy',
        'service': 'model-versioning',
        'database': 'mysql-netraidb',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/version/register', methods=['POST'])
def register_version():
    """Register a new model version."""
    if not version_manager:
        return jsonify({'error': 'Version manager not initialized'}), 500
        
    try:
        data = request.get_json()
        
        if not validate_request(data, ['site_id', 'model_weights', 'performance_metrics', 'clinical_metrics', 'created_by']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        version_id = version_manager.create_new_version(
            site_id=data['site_id'],
            model_weights=data['model_weights'],
            performance_metrics=data['performance_metrics'],
            clinical_metrics=data['clinical_metrics'],
            created_by=data['created_by'],
            parent_version=data.get('parent_version')
        )
        
        return jsonify({
            'success': True,
            'version_id': version_id,
            'message': 'Version registered successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error in register_version: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/version/latest', methods=['GET'])
def get_latest_version():
    """Get the latest model version for a site."""
    if not version_manager:
        return jsonify({'error': 'Version manager not initialized'}), 500
        
    try:
        site_id = request.args.get('site_id')
        if not site_id:
            return jsonify({'error': 'site_id parameter required'}), 400
            
        result = version_manager.get_site_version_info(site_id)
        
        if 'error' in result:
            return jsonify(result), 404
        else:
            return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in get_latest_version: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/version/history', methods=['GET'])
def get_version_history():
    """Get version history for all sites."""
    if not version_manager:
        return jsonify({'error': 'Version manager not initialized'}), 500
        
    try:
        result = version_manager.get_all_sites_status()
        return jsonify({'success': True, 'sites': result})
        
    except Exception as e:
        logger.error(f"Error in get_version_history: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/version/compatibility', methods=['GET'])
def get_compatibility_matrix():
    """Get version compatibility matrix."""
    if not version_manager:
        return jsonify({'error': 'Version manager not initialized'}), 500
        
    try:
        matrix = version_manager.get_version_compatibility_matrix()
        return jsonify({'success': True, 'compatibility_matrix': matrix})
        
    except Exception as e:
        logger.error(f"Error in get_compatibility_matrix: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/rollback/plan', methods=['POST'])
def plan_rollback():
    """Plan a distributed rollback."""
    if not version_manager:
        return jsonify({'error': 'Version manager not initialized'}), 500
        
    try:
        data = request.get_json()
        
        if not validate_request(data, ['target_version_id', 'affected_sites', 'rollback_reason', 'created_by']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        rollback_id = version_manager.plan_distributed_rollback(
            target_version_id=data['target_version_id'],
            affected_sites=data['affected_sites'],
            rollback_reason=data['rollback_reason'],
            created_by=data['created_by']
        )
        
        return jsonify({
            'success': True,
            'rollback_id': rollback_id,
            'message': 'Rollback planned successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error in plan_rollback: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/rollback/execute', methods=['POST'])
def execute_rollback():
    """Execute a planned rollback."""
    if not version_manager:
        return jsonify({'error': 'Version manager not initialized'}), 500
        
    try:
        data = request.get_json()
        
        if not validate_request(data, ['rollback_id']):
            return jsonify({'error': 'Missing rollback_id'}), 400
        
        result = version_manager.execute_distributed_rollback(data['rollback_id'])
        
        if 'error' in result:
            return jsonify(result), 400
        else:
            return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in execute_rollback: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/maintenance/cleanup', methods=['POST'])
def cleanup_old_versions():
    """Cleanup old model versions."""
    if not version_manager:
        return jsonify({'error': 'Version manager not initialized'}), 500
        
    try:
        data = request.get_json() or {}
        days_to_keep = data.get('days_to_keep', 90)
        
        version_manager.cleanup_old_versions(days_to_keep)
        
        return jsonify({
            'success': True,
            'message': f'Cleanup completed, kept versions from last {days_to_keep} days'
        })
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_versions: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('VERSIONING_PORT', '5002')), debug=False)
