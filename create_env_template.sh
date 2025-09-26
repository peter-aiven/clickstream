#!/bin/bash

# Create .env template - No interactive input required
# Edit the generated file manually with your values

echo "Creating .env template file..."

cat > .env << 'EOF'
# Kafka Configuration - Replace with your Aiven Kafka details
export KAFKA_BOOTSTRAP_SERVERS="your-kafka-service.aivencloud.com:12345"
export KAFKA_TOPIC="clickstream-analytics"
export KAFKA_GROUP_ID="clickstream-consumer-group"
export KAFKA_SSL_CAFILE="ca.pem"
export KAFKA_SSL_CERTFILE="service.cert"
export KAFKA_SSL_KEYFILE="service.key"

# PostgreSQL Configuration - Replace with your Aiven PostgreSQL details
export POSTGRES_HOST="your-postgres-service.aivencloud.com"
export POSTGRES_PORT="12345"
export POSTGRES_DATABASE="your_database_name"
export POSTGRES_USER="your_username"
export POSTGRES_PASSWORD="your_password"

EOF

echo "✅ .env template created successfully!"
echo
echo "Next steps:"
echo "1. Edit the .env file with your actual connection details"
echo "2. Replace the placeholder values with your Terraform output or Aiven console values"
echo "3. Load the environment: source .env"
echo "4. Run the applications: python consumer.py & python producer.py"
echo
echo "To edit the file:"
echo "  nano .env"
echo "  # or"
echo "  vim .env"
echo
echo "Required values to replace:"
echo "- KAFKA_BOOTSTRAP_SERVERS (from Terraform output or Aiven console)"
echo "- POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE, POSTGRES_USER, POSTGRES_PASSWORD"
echo "- Ensure SSL certificate files (ca.pem, service.cert, service.key) are present"
