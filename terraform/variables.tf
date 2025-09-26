variable "aiven_api_token" {
  description = "Aiven API token for authentication"
  type        = string
  sensitive   = true
}

variable "aiven_project_name" {
  description = "Aiven project name"
  type        = string
}
