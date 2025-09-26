# Service Connection URIs
output "service_uris" {
  description = "Connection URIs for all services"
  value = {
    postgresql = aiven_pg.postgres.service_uri
    kafka      = aiven_kafka.kafka.service_uri
    opensearch = aiven_opensearch.opensearch.service_uri
  }
  sensitive = true
}

# Kafka Topic Information
output "kafka_topic" {
  description = "Kafka topic configuration"
  value = {
    name        = aiven_kafka_topic.clickstream.topic_name
    partitions  = aiven_kafka_topic.clickstream.partitions
    replication = aiven_kafka_topic.clickstream.replication
  }
}

# Service Status
output "services_ready" {
  description = "Service deployment status"
  value = {
    postgresql_state = aiven_pg.postgres.state
    kafka_state      = aiven_kafka.kafka.state
    opensearch_state = aiven_opensearch.opensearch.state
  }
}

# CA Certificate for SSL connections
output "project_ca_cert" {
  description = "Project CA certificate for SSL/TLS connections"
  value       = data.aiven_project.project.ca_cert
  sensitive   = true
}
