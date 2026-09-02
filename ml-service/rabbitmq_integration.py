"""
RabbitMQ integration for NeuroTunes services
"""

import pika
import json
import logging
from typing import Dict, Any, Callable

class RabbitMQClient:
    def __init__(self, connection_url: str = 'amqp://guest:guest@localhost:5672/'):
        self.connection_url = connection_url
        self.connection = None
        self.channel = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = pika.BlockingConnection(pika.URLParameters(self.connection_url))
            self.channel = self.connection.channel()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def publish_message(self, exchange: str, routing_key: str, message: Dict[str, Any]):
        """Publish a message to RabbitMQ"""
        if not self.channel:
            if not self.connect():
                return False
        
        try:
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(message)
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to publish message: {e}")
            return False
    
    def close(self):
        """Close RabbitMQ connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
