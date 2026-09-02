"""
Common utilities for NeuroTunes services
"""

import os
import logging
import mysql.connector
from mysql.connector import pooling
from typing import Optional, Dict, Any, List
import json
from datetime import datetime
import numpy as np

def setup_logging(service_name: str, log_level: str = "INFO"):
    """Setup logging for a service."""
    # Ensure logs directory exists
    os.makedirs('/app/logs', exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=f'%(asctime)s - {service_name} - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'/app/logs/{service_name}.log')
        ]
    )
    return logging.getLogger(service_name)

def validate_request(data: Dict, required_fields: List[str]) -> bool:
    """Validate that required fields are present in request data."""
    if not data:
        return False
    
    for field in required_fields:
        if field not in data or data[field] is None:
            return False
    
    return True

def get_database_config() -> Dict[str, Any]:
    """Get database configuration from environment variables."""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_DATABASE', 'netraidb'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'port': int(os.getenv('DB_PORT', 3306))
    }

def create_database_connection():
    """Create a database connection using environment variables."""
    config = get_database_config()
    try:
        connection = mysql.connector.connect(**config)
        return connection
    except mysql.connector.Error as e:
        logging.error(f"Database connection error: {e}")
        return None

def format_response(success: bool, data: Any = None, error: str = None) -> Dict:
    """Format standardized API response."""
    response = {
        'success': success,
        'timestamp': datetime.now().isoformat()
    }
    
    if success and data is not None:
        response['data'] = data
    elif not success and error:
        response['error'] = error
    
    return response

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    import re
    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    return filename[:255]  # Limit length

class ConfigManager:
    """Manage configuration across services."""
    
    @staticmethod
    def get_db_config() -> Dict:
        """Get database configuration from environment."""
        return get_database_config()
    
    @staticmethod
    def get_rabbitmq_config() -> Dict:
        """Get RabbitMQ configuration from environment."""
        return {
            'url': os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/'),
            'exchange': os.getenv('RABBITMQ_EXCHANGE', 'neurotunes'),
            'queue_prefix': os.getenv('RABBITMQ_QUEUE_PREFIX', 'neurotunes')
        }

# DataProcessor class moved from synthetic service
class DataProcessor:
    def __init__(self):
        self.mood_mapping = {
            'very_sad': -2, 'sad': -1, 'neutral': 0, 'happy': 1, 'very_happy': 2
        }
        
        self.diagnosis_mapping = {
            'anxiety': [1, 0, 0, 0],
            'depression': [0, 1, 0, 0],
            'post_stroke': [0, 0, 1, 0],
            'tbi': [0, 0, 0, 1],
            'healthy': [0, 0, 0, 0]
        }
    
    def process_patient_data(self, raw_data):
        """Convert raw patient data to ML model input"""
        try:
            # Extract and normalize features
            features = []
            
            # Age (normalized to 0-1)
            age = raw_data.get('age', 30)
            features.append(min(1.0, age / 100.0))
            
            # Mood (converted to numeric)
            mood = raw_data.get('mood', 'neutral')
            if isinstance(mood, str):
                mood_value = self.mood_mapping.get(mood, 0)
            else:
                mood_value = float(mood)  # Assume numeric scale
            features.append(mood_value / 2.0)  # Normalize to -1 to 1
            
            # Stress level (0-10 scale)
            stress = raw_data.get('stress_level', 5)
            features.append(stress / 10.0)
            
            # Sleep quality (0-10 scale)
            sleep = raw_data.get('sleep_quality', 7)
            features.append(sleep / 10.0)
            
            # Energy level (0-10 scale)
            energy = raw_data.get('energy_levels', 5)
            features.append(energy / 10.0)
            
            # Diagnosis (one-hot encoded)
            diagnosis = raw_data.get('diagnosis', 'healthy')
            diagnosis_vector = self.diagnosis_mapping.get(diagnosis, [0, 0, 0, 0])
            features.extend(diagnosis_vector)
            
            # Therapy session number (experience factor)
            session_num = raw_data.get('session_number', 1)
            features.append(min(1.0, session_num / 20.0))  # Normalize to 0-1
            
            return np.array(features)
            
        except Exception as e:
            print(f"Error processing patient data: {str(e)}")
            # Return default neutral state
            return np.array([0.3, 0.0, 0.5, 0.7, 0.5, 0, 0, 0, 0, 0.05])
    
    def validate_input(self, data):
        """Validate input data"""
        required_fields = ['age', 'mood', 'therapy_goal']
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate age
        if not isinstance(data['age'], (int, float)) or data['age'] < 0 or data['age'] > 120:
            return False, "Invalid age"
        
        # Validate therapy goal
        valid_goals = ['relaxation', 'focus', 'motivation', 'motor_rehab', 'speech_rehab']
        if data['therapy_goal'] not in valid_goals:
            return False, f"Invalid therapy goal. Must be one of: {valid_goals}"
        
        return True, "Valid"
