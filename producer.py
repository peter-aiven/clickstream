import json
import os
import time
import random
from datetime import datetime, timezone
from kafka import KafkaProducer
from faker import Faker
import uuid

class ClickstreamProducer:
    def __init__(self):
        """Initialize the Clickstream Producer with environment-based configuration"""
        self.faker = Faker()
        
        # Load configuration from environment variables
        kafka_config = {
            'bootstrap_servers': [os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')],
            'security_protocol': 'SSL',
            'ssl_cafile': os.getenv('KAFKA_SSL_CAFILE'),
            'ssl_certfile': os.getenv('KAFKA_SSL_CERTFILE'),
            'ssl_keyfile': os.getenv('KAFKA_SSL_KEYFILE'),
            'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
            'key_serializer': lambda k: str(k).encode('utf-8') if k else None,
            'metadata_max_age_ms': 30000,  # Refresh metadata every 30 seconds
            'request_timeout_ms': 30000,   # 30 second timeout for requests
            'retries': 3
        }
        
        # Remove SSL config if certificates not provided (for local dev)
        ssl_files = [kafka_config['ssl_cafile'], kafka_config['ssl_certfile'], kafka_config['ssl_keyfile']]
        if not all(ssl_files):
            kafka_config = {k: v for k, v in kafka_config.items() 
                          if not k.startswith('ssl_') and k != 'security_protocol'}
        
        # Print connection info for debugging
        print(f"Connecting to: {kafka_config['bootstrap_servers']}")
        print(f"SSL enabled: {'security_protocol' in kafka_config}")
        if 'security_protocol' in kafka_config:
            print(f"Certificate files exist: {[os.path.exists(f) for f in ssl_files if f]}")
        
        self.producer = KafkaProducer(**kafka_config)
        self.topic_name = os.getenv('KAFKA_TOPIC', 'clickstream-analytics')
        
        print(f"Connected successfully to topic: {self.topic_name}")
        
        # Static data for event generation
        self.page_urls = [
            '/home', '/products', '/products/electronics', '/products/clothing',
            '/product/laptop-123', '/product/phone-456', '/cart', '/checkout',
            '/account', '/login', '/search', '/about'
        ]
        
        self.event_types = ['page_view', 'click', 'scroll', 'add_to_cart', 'purchase', 'search', 'login']
        self.event_weights = [0.4, 0.2, 0.15, 0.08, 0.05, 0.07, 0.05]
        
        # Session management
        self.active_sessions = {}
        self.user_pool = [str(uuid.uuid4()) for _ in range(50)]
    
    def _get_session_id(self, user_id):
        """Get or create session ID for user"""
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = {
                'session_id': str(uuid.uuid4()),
                'start_time': datetime.now(timezone.utc),
                'page_count': 0
            }
        
        session = self.active_sessions[user_id]
        session_duration = datetime.now(timezone.utc) - session['start_time']
        
        # Create new session after 10 pages or 30 minutes
        if session['page_count'] > 10 or session_duration.seconds > 1800:
            self.active_sessions[user_id] = {
                'session_id': str(uuid.uuid4()),
                'start_time': datetime.now(timezone.utc),
                'page_count': 0
            }
        
        return self.active_sessions[user_id]['session_id']
    
    def _generate_event(self):
        """Generate a single clickstream event"""
        user_id = random.choice(self.user_pool)
        session_id = self._get_session_id(user_id)
        self.active_sessions[user_id]['page_count'] += 1
        
        event_type = random.choices(self.event_types, weights=self.event_weights)[0]
        
        # Context-aware page selection
        if event_type == 'purchase':
            page_url = '/checkout'
        elif event_type == 'add_to_cart':
            page_url = random.choice([url for url in self.page_urls if '/product' in url])
        elif event_type in ['search', 'login']:
            page_url = f'/{event_type}'
        else:
            page_url = random.choice(self.page_urls)
        
        event_data = {
            'user_id': user_id,
            'session_id': session_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'page_url': page_url,
            'event_type': event_type,
            'user_agent': self.faker.user_agent(),
            'ip_address': self.faker.ipv4(),
            'referrer': random.choice([None, '/home', '/products'])
        }
        
        # Add event-specific data
        if event_type in ['add_to_cart', 'purchase']:
            event_data.update({
                'product_id': f"prod_{random.randint(1000, 9999)}",
                'product_category': random.choice(['electronics', 'clothing', 'books']),
                'price': round(random.uniform(10.0, 500.0), 2)
            })
        
        if event_type == 'search':
            event_data['search_query'] = self.faker.word()
        
        if event_type == 'click':
            event_data['element_id'] = f"btn_{random.choice(['header', 'nav', 'main'])}"
        
        return event_data
    
    def produce_events(self, num_events=100, delay_range=(0.1, 1.0)):
        """Produce clickstream events to Kafka topic"""
        for i in range(num_events):
            event = self._generate_event()
            self.producer.send(self.topic_name, key=event['user_id'], value=event)
            
            if (i + 1) % 10 == 0:
                print(f"Produced {i + 1}/{num_events} events")
            
            time.sleep(random.uniform(*delay_range))
        
        self.producer.flush()
    
    def close(self):
        """Close the producer connection"""
        self.producer.close()

def main():
    producer = ClickstreamProducer()
    
    try:
        producer.produce_events(num_events=1000, delay_range=(0.1, 1.0))
        print("Event production completed successfully")
    except KeyboardInterrupt:
        print("Production interrupted")
    except Exception as e:
        print(f"Production failed: {e}")
    finally:
        producer.close()

if __name__ == "__main__":
    main()