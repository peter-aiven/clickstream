terraform {
  required_providers {
    aiven = {
      source  = "aiven/aiven"
      version = ">= 4.0.0, < 5.0.0"
    }
  }
}

provider "aiven" {
  api_token = var.aiven_api_token
}

# Project reference for CA certificate
data "aiven_project" "project" {
  project = var.aiven_project_name
}

# PostgreSQL Service
resource "aiven_pg" "postgres" {
  project      = var.aiven_project_name
  cloud_name   = "aws-us-east-1"
  plan         = "startup-4"
  service_name = "postgres-demo"

  pg_user_config {
    pg_version = "16"
  }

  tag {
    key   = "purpose"
    value = "demo"
  }
}

# Kafka Service with Connect enabled
resource "aiven_kafka" "kafka" {
  project      = var.aiven_project_name
  cloud_name   = "aws-us-east-1"
  plan         = "business-4"
  service_name = "kafka-demo"

  kafka_user_config {
    kafka_version = "3.8"
    kafka_connect = true
  }

  tag {
    key   = "purpose"
    value = "demo"
  }
}

# Kafka Topic for clickstream data
resource "aiven_kafka_topic" "clickstream" {
  project      = var.aiven_project_name
  service_name = aiven_kafka.kafka.service_name
  topic_name   = "clickstream-analytics"
  partitions   = 3
  replication  = 2

  config {
    cleanup_policy      = "delete"
    retention_ms        = "604800000" # 7 days
    segment_ms          = "86400000"  # 1 day
    min_insync_replicas = "1"
  }
}

# OpenSearch Service
resource "aiven_opensearch" "opensearch" {
  project      = var.aiven_project_name
  cloud_name   = "aws-us-east-1"
  plan         = "startup-4"
  service_name = "opensearch-demo"

  opensearch_user_config {
    opensearch_version = "2"
  }

  tag {
    key   = "purpose"
    value = "demo"
  }
}

# Kafka Connector - Stream data from Kafka to OpenSearch
resource "aiven_kafka_connector" "opensearch_sink" {
  project        = var.aiven_project_name
  service_name   = aiven_kafka.kafka.service_name
  connector_name = "clickstream-to-opensearch"

  config = {
    "name"                           = "clickstream-to-opensearch"
    "connector.class"                = "io.aiven.kafka.connect.opensearch.OpensearchSinkConnector"
    "topics"                         = aiven_kafka_topic.clickstream.topic_name
    "connection.url"                 = "https://${aiven_opensearch.opensearch.service_host}:${aiven_opensearch.opensearch.service_port}"
    "connection.username"            = aiven_opensearch.opensearch.service_username
    "connection.password"            = aiven_opensearch.opensearch.service_password
    "type.name"                      = "_doc"
    "schema.ignore"                  = "true"
    "key.ignore"                     = "true"
    "tasks.max"                      = "1"
    "key.converter"                  = "org.apache.kafka.connect.storage.StringConverter"
    "value.converter"                = "org.apache.kafka.connect.json.JsonConverter"
    "value.converter.schemas.enable" = "false"
  }

  depends_on = [
    aiven_kafka.kafka,
    aiven_opensearch.opensearch,
    aiven_kafka_topic.clickstream
  ]
}
