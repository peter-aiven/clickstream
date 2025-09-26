# Real-Time Clickstream Data Pipeline

A complete real-time data streaming pipeline that simulates, processes, and stores website clickstream data using Aiven's managed services and modern data engineering practices.

## 📋 Project Overview

This project demonstrates a production-ready data pipeline that:
- **Generates** realistic website clickstream events with user sessions and e-commerce activities
- **Streams** data through Apache Kafka with dual processing paths
- **Aggregates** events into session-level metrics stored in PostgreSQL
- **Indexes** raw events in real-time to OpenSearch for immediate analysis
- **Visualizes** live data through interactive OpenSearch dashboards
- **Monitors** system performance and user behavior in real-time

## 🏗️ Architecture

```
                                    ┌─────────────────┐
                                    │  Clickstream    │
                                    │   Producer      │
                                    └─────────┬───────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │   Aiven Kafka   │
                                    │   (Streaming)   │
                                    └─────────┬───────┘
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        ▼                                           ▼
              ┌─────────────────┐                         ┌─────────────────┐
              │   Consumer &    │                         │ Kafka Connect   │
              │   Aggregator    │                         │ Sink Connector  │
              └─────────┬───────┘                         └─────────┬───────┘
                        │                                           │
                        ▼                                           ▼
              ┌─────────────────┐                         ┌─────────────────┐
              │ Aiven PostgreSQL│                         │ Aiven OpenSearch│
              │   (Session      │                         │  (Real-time     │
              │   Analytics)    │                         │  Visualization) │
              └─────────────────┘                         └─────────┬───────┘
                                                                    │
                                                                    ▼
                                                          ┌─────────────────┐
                                                          │   OpenSearch    │
                                                          │   Dashboards    │
                                                          │ (Live Analytics)│
                                                          └─────────────────┘
```

### Components:
- **Aiven Kafka**: Managed Kafka cluster for real-time event streaming with dual data paths
- **Aiven PostgreSQL**: Managed database for aggregated session-level analytics and reporting
- **Aiven OpenSearch**: Managed search and analytics engine with real-time event indexing
- **Kafka Connect Sink**: Streams raw events directly to OpenSearch for real-time analysis
- **OpenSearch Dashboards**: Interactive visualization and monitoring of live clickstream data
- **Terraform**: Infrastructure as Code for provisioning all Aiven services
- **Python Scripts**: Producer and consumer applications

### Data Flow:
1. **Event Generation**: Producer generates realistic clickstream events
2. **Stream Distribution**: Kafka distributes events to multiple consumers
3. **Dual Processing**:
   - **Session Aggregation**: Consumer processes events into PostgreSQL session metrics
   - **Real-time Indexing**: Sink connector streams raw events to OpenSearch
4. **Visualization**: OpenSearch Dashboards provide real-time analytics and monitoring

## 🚦 Prerequisites

- **Aiven Account**: Sign up at [Aiven.io](https://aiven.io) and get your API token
- **Terraform**: Version 1.0 or higher ([Installation Guide](https://terraform.io/downloads))
- **Python**: Version 3.8 or higher
- **Required Python packages**:
  ```bash
  pip install kafka-python psycopg2-binary faker
  ```

## ⚙️ Environment Variables

Both producer and consumer scripts use environment variables for configuration. Create a `.env` file or export these variables:

### Kafka Configuration (Required)
```bash
# Aiven Kafka connection details (from Terraform output)
export KAFKA_BOOTSTRAP_SERVERS="your-kafka-service.aivencloud.com:12345"
export KAFKA_TOPIC="clickstream-events"

# SSL Configuration (required for Aiven)
export KAFKA_SSL_CAFILE="ca.pem"
export KAFKA_SSL_CERTFILE="service.cert"
export KAFKA_SSL_KEYFILE="service.key"
```

### PostgreSQL Configuration (Consumer only)
```bash
# Aiven PostgreSQL connection details (from Terraform output)
export POSTGRES_HOST="your-postgres-service.aivencloud.com"
export POSTGRES_PORT="12345"
export POSTGRES_DATABASE="your_database_name"
export POSTGRES_USER="your_username"
export POSTGRES_PASSWORD="your_password"
```

## 🚀 Getting Started

### 1. Clone
```bash
git clone https://github.com/peter-aiven/clickstream.git
cd clickstream
```

### 2. Infrastructure Provisioning
```bash
cd terraform

# Initialize Terraform
terraform init

# Configure your Aiven API token
echo 'aiven_api_token = "your_aiven_api_token"' > terraform.tfvars
echo 'aiven_project_name = "your_avent_project_name"' >> terraform.tfvars

# Deploy infrastructure
terraform apply
```

### 3. SSL Certificate Setup
After Terraform deployment, download the SSL certificates:

```bash
# Get connection details
terraform output

# Download Kafka SSL certificates from Aiven Console
# Place them in your project root as:
# - ca.pem (CA certificate)
# - service.cert (Service certificate)  
# - service.key (Service private key)
```

### 4. Generate Environment Variables

#### Option 1: Environment Variable Script (Recommended)
Use the provided setup script to generate a .env file containing necessary variables:

```bash
# Make the script executable
chmod +x create_env_template.sh

# Run the template setup
./create_env_template.sh

# Edit the environment variables
vim .env

# Source them to your shell
source .env
```

#### Option 2: Manual Configuration
Alternatively, export the variables manually:
```bash
# Export the connection details from Terraform output
export KAFKA_BOOTSTRAP_SERVERS="$(terraform output -raw kafka_service_uri)"
export POSTGRES_HOST="$(terraform output -raw postgres_host)"
export POSTGRES_PORT="$(terraform output -raw postgres_port)"
export POSTGRES_DATABASE="$(terraform output -raw postgres_database)"
export POSTGRES_USER="$(terraform output -raw postgres_user)"
export POSTGRES_PASSWORD="$(terraform output -raw postgres_password)"

# Set SSL certificate paths
export KAFKA_SSL_CAFILE="ca.pem"
export KAFKA_SSL_CERTFILE="service.cert"
export KAFKA_SSL_KEYFILE="service.key"
```


### 5. Start the Data Pipeline

#### Terminal 1 - Start the Consumer (recommended to start first)
```bash
python consumer.py
```

#### Terminal 2 - Start the Producer
```bash
python producer.py
```

### 6. Monitor the Pipeline
Watch both terminals for progress:
- **Producer**: Shows event generation progress for every ten events
- **Consumer**: Shows processing of events

### 7. Access Real-time Dashboards
Navigate to your OpenSearch Dashboards (connection details from Terraform output):
```bash
# Get OpenSearch dashboard URL
terraform output opensearch_dashboard_url

# Login with your OpenSearch credentials
# Default index pattern: clickstream-events-*
```

### 8. Verify Data Storage

#### PostgreSQL Session Analytics
Connect to PostgreSQL to view aggregated results:
```sql
-- Check session metrics
SELECT 
    session_id,
    user_id,
    total_events,
    session_duration_minutes,
    total_revenue,
    event_type_counts
FROM session_metrics 
ORDER BY last_event_timestamp DESC 
LIMIT 10;

-- Analytics queries
SELECT 
    COUNT(*) as total_sessions,
    AVG(total_events) as avg_events_per_session,
    SUM(total_revenue) as total_revenue,
    AVG(session_duration_minutes) as avg_session_duration
FROM session_metrics;
```

#### OpenSearch Real-time Analytics
Access OpenSearch Dashboards to configure:
- **Real-time Event Stream**: View events as they arrive
- **User Journey Analysis**: Track page flows and session patterns
- **Conversion Funnels**: Monitor e-commerce conversion rates
- **Geographic Insights**: Analyze user locations and behavior
- **Performance Monitoring**: Track system throughput and latency

## 📊 Data Architecture

The pipeline implements a dual-storage approach for different analytical needs:

### PostgreSQL: Session Analytics
Stores aggregated session-level metrics optimized for business intelligence:

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | VARCHAR(255) | Unique session identifier (Primary Key) |
| `user_id` | VARCHAR(255) | User identifier |
| `total_events` | INTEGER | Total events in session |
| `event_type_counts` | JSONB | Count of each event type |
| `first_event_timestamp` | TIMESTAMP | Session start time |
| `last_event_timestamp` | TIMESTAMP | Session end time |
| `session_duration_minutes` | FLOAT | Session length in minutes |
| `unique_pages_count` | INTEGER | Number of unique pages visited |
| `unique_pages` | JSONB | Array of unique page URLs |
| `total_revenue` | DECIMAL(10,2) | Revenue from purchases |
| `products_viewed_count` | INTEGER | Number of unique products viewed |
| `products_viewed` | JSONB | Array of product IDs |
| `search_queries` | JSONB | Array of search terms |
| `unique_referrers_count` | INTEGER | Number of unique referrer sources |
| `referrers` | JSONB | Array of referrer URLs |
| `user_agent` | TEXT | Browser user agent |
| `ip_address` | INET | User IP address |

### OpenSearch: Real-time Event Analytics
Stores raw events optimized for real-time analysis and exploration:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | DATE | Event timestamp |
| `user_id` | KEYWORD | User identifier |
| `session_id` | KEYWORD | Session identifier |
| `event_type` | KEYWORD | Type of event (page_view, click, etc.) |
| `page_url` | KEYWORD | Page URL visited |
| `referrer` | KEYWORD | Referrer source |
| `user_agent` | TEXT | Browser user agent |
| `ip_address` | IP | User IP address |
| `device_type` | KEYWORD | Device category (desktop, mobile, tablet) |
| `product_id` | KEYWORD | Product identifier (for e-commerce events) |
| `product_category` | KEYWORD | Product category |
| `price` | FLOAT | Product price |
| `search_query` | TEXT | Search terms |
| `element_id` | KEYWORD | UI element identifier (for click events) |
| `viewport_size` | KEYWORD | Browser viewport dimensions |

## 🎯 Generated Event Types

The producer generates realistic events with appropriate weights:

| Event Type | Weight | Description |
|------------|--------|-------------|
| `page_view` | 35% | Page navigation |
| `click` | 20% | Button/link clicks |
| `scroll` | 15% | Page scrolling |
| `hover` | 8% | Element hover |
| `add_to_cart` | 6% | Product added to cart |
| `search` | 4% | Search queries |
| `login` | 2.5% | User authentication |
| `purchase` | 0.8% | Purchase completion |
| `share` | 1% | Social sharing |

## 🛠️ Troubleshooting

### Common Issues:

1. **SSL Certificate Error**
   ```bash
   # Manually check certificates
   ls -la *.pem *.cert *.key
   
   # Check file permissions
   chmod 600 *.key
   chmod 644 *.pem *.cert
   ```

2. **OpenSearch Connection Issues**
   ```bash
   # Test OpenSearch connectivity
   curl -X GET "https://your-opensearch-host:443/_cluster/health" \
        --cert service.cert --key service.key --cacert ca.pem
   
   # Verify sink connector status
   # Check Kafka Connect logs in Aiven Console
   ```

3. **Dashboard Not Showing Data**
   ```bash
   # Verify index pattern exists
   # Check OpenSearch index: clickstream-events-*
   # Ensure time field is mapped correctly
   
   # Test data ingestion
   curl -X GET "https://your-opensearch-host:443/clickstream-events-*/_search?size=5" \
        --cert service.cert --key service.key --cacert ca.pem
   ```
4. **Kafka Connection Failed**
   ```bash
   # Verify bootstrap servers format
   echo $KAFKA_BOOTSTRAP_SERVERS
   # Should be: hostname:port (not a URL)
   ```

5. **Consumer Group Issues**
   ```bash
   # Try a different consumer group
   export KAFKA_GROUP_ID="test-consumer-$(date +%s)"
   ```

6. **PostgreSQL Connection Error**
   ```bash
   # Test connection manually
   psql "postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DATABASE?sslmode=require"
   ```

## 🎨 Demo Features

### Producer Highlights:
- 🎯 **Realistic User Journeys**: Session-based navigation with natural timeouts
- 💰 **E-commerce Simulation**: Product views, cart operations, purchases with revenue tracking
- 📱 **Multi-device Support**: Desktop, mobile, tablet simulation
- 🔍 **Contextual Events**: Search on search pages, purchases on checkout pages

### Consumer Highlights:
- ⚡ **Real-time Aggregation**: Session metrics updated as events arrive
- 🔄 **Fault Tolerance**: Graceful error handling and recovery
- 📊 **Rich Analytics**: 15+ metrics per session for deep insights
- 💾 **Efficient Storage**: Bulk database operations with UPSERT logic

## 🔧 Customization

### Adding New Event Types:
1. Update `event_types` and `event_weights` in `producer.py`
2. Add event-specific data generation in `_add_event_specific_data()`
3. Update consumer aggregation logic if needed

### Custom Analytics:
1. Modify the `session_metrics` table schema
2. Update `_prepare_session_data()` in the consumer
3. Add new aggregation fields to track additional metrics

### Integration with Other Systems:
- **Machine Learning Pipelines**: Stream events to ML services for real-time predictions
- **Data Lakes**: Add S3/GCS output for long-term storage and batch processing
- **Alert Systems**: Integrate with PagerDuty/Slack for anomaly detection alerts
- **A/B Testing Platforms**: Connect with experimentation frameworks for feature flagging

## 🧹 Project Teardown

**Important**: Destroy infrastructure to avoid ongoing charges:

```bash
cd terraform
terraform destroy
```

Confirm with `yes` when prompted. This will delete all Aiven services and associated data.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ using Aiven, Apache Kafka, and modern data engineering practices**
