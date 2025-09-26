import json
import os
import time
import threading
from datetime import datetime, timezone
from collections import defaultdict
import logging
import signal
import sys

from kafka import KafkaConsumer, TopicPartition
import psycopg2
from psycopg2.extras import execute_values

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClickstreamConsumer:
    def __init__(self):
        """Initialize the Clickstream Consumer with environment-based configuration"""
        self.kafka_config = self._load_kafka_config()
        self.postgres_config = self._load_postgres_config()
        
        # Session aggregation storage
        self.session_metrics = defaultdict(lambda: {
            'session_id': None,
            'user_id': None,
            'total_events': 0,
            'event_types': defaultdict(int),
            'first_event_timestamp': None,
            'last_event_timestamp': None,
            'unique_pages': set(),
            'total_revenue': 0.0,
            'products_viewed': set(),
            'search_queries': [],
            'referrers': set(),
            'user_agent': None,
            'ip_address': None
        })
        
        # Track session activity for timeout detection
        self.session_last_activity = {}
        
        # Configuration
        self.session_timeout_minutes = 30
        self.batch_size = 50
        self.flush_interval_seconds = 60
        
        # Consumer and database connections
        self.consumer = None
        self.postgres_conn = None
        self.postgres_cursor = None
        
        # Threading and shutdown
        self.running = True
        self.flush_timer = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_kafka_config(self):
        """Load Kafka configuration from environment variables"""
        required_vars = [
            'KAFKA_BOOTSTRAP_SERVERS',
            'KAFKA_TOPIC',
            'KAFKA_SSL_CAFILE',
            'KAFKA_SSL_CERTFILE',
            'KAFKA_SSL_KEYFILE'
        ]
        
        config = {}
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                raise ValueError(f"Required environment variable {var} is not set")
            config[var.lower().replace('kafka_', '')] = value
        
        # Optional variables with defaults
        config['group_id'] = os.getenv('KAFKA_GROUP_ID', 'clickstream-consumer-group')
        
        # Convert bootstrap_servers to list
        config['bootstrap_servers'] = [s.strip() for s in config['bootstrap_servers'].split(',')]
        
        return config
    
    def _load_postgres_config(self):
        """Load PostgreSQL configuration from environment variables"""
        required_vars = [
            'POSTGRES_HOST',
            'POSTGRES_PORT',
            'POSTGRES_DATABASE',
            'POSTGRES_USER',
            'POSTGRES_PASSWORD'
        ]
        
        config = {}
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                raise ValueError(f"Required environment variable {var} is not set")
            key = var.lower().replace('postgres_', '')
            config[key] = int(value) if key == 'port' else value
        
        return config
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        if self.flush_timer:
            self.flush_timer.cancel()
    
    def connect_kafka(self):
        """Establish Kafka consumer connection"""
        try:
            import socket
            import uuid
            
            # Generate unique client ID
            client_id = f"consumer-{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
            
            self.consumer = KafkaConsumer(
                self.kafka_config['topic'],
                bootstrap_servers=self.kafka_config['bootstrap_servers'],
                security_protocol='SSL',
                ssl_cafile=self.kafka_config['ssl_cafile'],
                ssl_certfile=self.kafka_config['ssl_certfile'],
                ssl_keyfile=self.kafka_config['ssl_keyfile'],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                group_id=self.kafka_config['group_id'],
                client_id=client_id,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                consumer_timeout_ms=10000,
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000,
                max_poll_records=100,
                api_version='auto'
            )
            
            logger.info(f"Connected to Kafka topic: {self.kafka_config['topic']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    def connect_postgres(self):
        """Establish PostgreSQL connection and create table"""
        try:
            self.postgres_conn = psycopg2.connect(
                host=self.postgres_config['host'],
                port=self.postgres_config['port'],
                database=self.postgres_config['database'],
                user=self.postgres_config['user'],
                password=self.postgres_config['password'],
                sslmode='require',
                connect_timeout=10
            )
            
            self.postgres_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            self.postgres_cursor = self.postgres_conn.cursor()
            
            # Create table if it doesn't exist
            self._create_table()
            logger.info("Connected to PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False
    
    def _create_table(self):
        """Create the session metrics table"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS session_metrics (
            session_id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            total_events INTEGER NOT NULL,
            event_type_counts JSONB,
            first_event_timestamp TIMESTAMP WITH TIME ZONE,
            last_event_timestamp TIMESTAMP WITH TIME ZONE,
            session_duration_minutes FLOAT,
            unique_pages_count INTEGER,
            unique_pages JSONB,
            total_revenue DECIMAL(10,2),
            products_viewed_count INTEGER,
            products_viewed JSONB,
            search_queries JSONB,
            unique_referrers_count INTEGER,
            referrers JSONB,
            user_agent TEXT,
            ip_address INET,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_session_metrics_user_id ON session_metrics(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_session_metrics_timestamp ON session_metrics(last_event_timestamp);"
        ]
        
        try:
            self.postgres_cursor.execute(create_table_query)
            for index_query in index_queries:
                self.postgres_cursor.execute(index_query)
            self.postgres_conn.commit()
            
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            self.postgres_conn.rollback()
            raise
    
    def process_message(self, message):
        """Process a single Kafka message and update session metrics"""
        try:
            event_data = message.value
            session_id = event_data['session_id']
            
            # Initialize or update session metrics
            session = self.session_metrics[session_id]
            
            if session['session_id'] is None:
                session['session_id'] = session_id
                session['user_id'] = event_data['user_id']
                session['first_event_timestamp'] = datetime.fromisoformat(event_data['timestamp'].replace('Z', '+00:00'))
                session['user_agent'] = event_data.get('user_agent')
                session['ip_address'] = event_data.get('ip_address')
            
            # Update metrics
            session['total_events'] += 1
            session['last_event_timestamp'] = datetime.fromisoformat(event_data['timestamp'].replace('Z', '+00:00'))
            session['event_types'][event_data['event_type']] += 1
            session['unique_pages'].add(event_data['page_url'])
            
            # Track session activity
            self.session_last_activity[session_id] = datetime.now(timezone.utc)
            
            # Process event-specific data
            if 'referrer' in event_data and event_data['referrer']:
                session['referrers'].add(event_data['referrer'])
            
            if 'product_id' in event_data:
                session['products_viewed'].add(event_data['product_id'])
                
            if 'price' in event_data and event_data['event_type'] == 'purchase':
                session['total_revenue'] += event_data['price']
            
            if 'search_query' in event_data:
                session['search_queries'].append(event_data['search_query'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return False
    
    def _prepare_session_data(self, session_id, session):
        """Prepare session data for database insertion"""
        duration_minutes = None
        if session['first_event_timestamp'] and session['last_event_timestamp']:
            duration = session['last_event_timestamp'] - session['first_event_timestamp']
            duration_minutes = duration.total_seconds() / 60
        
        return (
            session_id,
            session['user_id'],
            session['total_events'],
            json.dumps(dict(session['event_types'])),
            session['first_event_timestamp'],
            session['last_event_timestamp'],
            duration_minutes,
            len(session['unique_pages']),
            json.dumps(list(session['unique_pages'])),
            session['total_revenue'],
            len(session['products_viewed']),
            json.dumps(list(session['products_viewed'])),
            json.dumps(session['search_queries']),
            len(session['referrers']),
            json.dumps(list(session['referrers'])),
            session['user_agent'],
            session['ip_address'],
            datetime.now(timezone.utc)
        )
    
    def flush_expired_sessions(self):
        """Flush sessions that have expired due to timeout"""
        current_time = datetime.now(timezone.utc)
        expired_sessions = []
        
        for session_id, last_activity in list(self.session_last_activity.items()):
            if (current_time - last_activity).total_seconds() > (self.session_timeout_minutes * 60):
                expired_sessions.append(session_id)
        
        if expired_sessions:
            self._write_sessions_to_db(expired_sessions, "timeout")
    
    def flush_completed_sessions(self):
        """Flush sessions based on batch size"""
        if len(self.session_metrics) >= self.batch_size:
            session_ids = list(self.session_metrics.keys())[:self.batch_size]
            self._write_sessions_to_db(session_ids, "batch_size")
    
    def _write_sessions_to_db(self, session_ids, reason):
        """Write specified sessions to database"""
        if not session_ids:
            return
        
        try:
            session_data = []
            for session_id in session_ids:
                if session_id in self.session_metrics:
                    session_data.append(self._prepare_session_data(session_id, self.session_metrics[session_id]))
            
            if session_data:
                upsert_query = """
                INSERT INTO session_metrics (
                    session_id, user_id, total_events, event_type_counts,
                    first_event_timestamp, last_event_timestamp, session_duration_minutes,
                    unique_pages_count, unique_pages, total_revenue,
                    products_viewed_count, products_viewed, search_queries,
                    unique_referrers_count, referrers, user_agent, ip_address, updated_at
                ) VALUES %s
                ON CONFLICT (session_id) DO UPDATE SET
                    total_events = EXCLUDED.total_events,
                    event_type_counts = EXCLUDED.event_type_counts,
                    last_event_timestamp = EXCLUDED.last_event_timestamp,
                    session_duration_minutes = EXCLUDED.session_duration_minutes,
                    unique_pages_count = EXCLUDED.unique_pages_count,
                    unique_pages = EXCLUDED.unique_pages,
                    total_revenue = EXCLUDED.total_revenue,
                    products_viewed_count = EXCLUDED.products_viewed_count,
                    products_viewed = EXCLUDED.products_viewed,
                    search_queries = EXCLUDED.search_queries,
                    unique_referrers_count = EXCLUDED.unique_referrers_count,
                    referrers = EXCLUDED.referrers,
                    updated_at = EXCLUDED.updated_at
                """
                
                execute_values(
                    self.postgres_cursor, 
                    upsert_query, 
                    session_data, 
                    template=None, 
                    page_size=100
                )
                
                self.postgres_conn.commit()
                logger.info(f"Flushed {len(session_data)} sessions to database ({reason})")
                
                # Clean up processed sessions
                for session_id in session_ids:
                    if session_id in self.session_metrics:
                        del self.session_metrics[session_id]
                    if session_id in self.session_last_activity:
                        del self.session_last_activity[session_id]
        
        except Exception as e:
            logger.error(f"Error writing sessions to database: {e}")
            try:
                self.postgres_conn.rollback()
            except:
                pass
    
    def _schedule_flush(self):
        """Schedule periodic flush of expired sessions"""
        if self.running:
            self.flush_expired_sessions()
            self.flush_timer = threading.Timer(self.flush_interval_seconds, self._schedule_flush)
            self.flush_timer.start()
    
    def consume_and_process(self):
        """Main consumer loop"""
        if not self.connect_kafka() or not self.connect_postgres():
            return False
        
        # Start periodic flush timer
        self._schedule_flush()
        
        logger.info("Starting message consumption...")
        messages_processed = 0
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                if self.process_message(message):
                    messages_processed += 1
                    
                    # Log progress every 100 messages
                    if messages_processed % 100 == 0:
                        logger.info(f"Processed {messages_processed} messages, tracking {len(self.session_metrics)} sessions")
                    
                    # Check if we should flush based on batch size
                    self.flush_completed_sessions()
        
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
        finally:
            self._shutdown()
        
        return True
    
    def _shutdown(self):
        """Graceful shutdown - flush remaining sessions and close connections"""
        logger.info("Shutting down consumer...")
        self.running = False
        
        if self.flush_timer:
            self.flush_timer.cancel()
        
        # Flush all remaining sessions
        remaining_sessions = list(self.session_metrics.keys())
        if remaining_sessions:
            logger.info(f"Flushing {len(remaining_sessions)} remaining sessions...")
            self._write_sessions_to_db(remaining_sessions, "shutdown")
        
        # Close connections
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")
        
        if self.postgres_cursor:
            self.postgres_cursor.close()
        if self.postgres_conn:
            self.postgres_conn.close()
            logger.info("PostgreSQL connection closed")

def main():
    try:
        consumer = ClickstreamConsumer()
        success = consumer.consume_and_process()
        
        if success:
            logger.info("Consumer completed successfully")
        else:
            logger.error("Consumer failed to start")
            sys.exit(1)
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
