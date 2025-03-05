# Configuration Management System

This document provides an overview of the configuration management system used in the GPU Fleet Manager application.

## Overview

The GPU Fleet Manager uses a centralized configuration system built on Pydantic for strong typing and validation. The system provides:

- Environment variable loading with sensible defaults
- Type validation for all configuration values
- Hierarchical organization of settings
- Secure handling of sensitive information

## Configuration Structure

Our configuration system is organized into hierarchical settings classes:

1. **Settings**: Top-level configuration container
   - General application settings (environment, name, version)
   - Contains all specialized settings categories

2. **DatabaseSettings**: Database connection configuration
   - Connection parameters (host, port, credentials)
   - Schema settings
   - SSL configuration

3. **SupabaseSettings**: Supabase-specific settings
   - URL, API key, and JWT secret

4. **GPUProviderSettings**: Cloud or on-premise GPU provider settings
   - Provider type (on-premise, AWS, GCP, Azure)
   - Provider-specific authentication and region settings

5. **APISettings**: API service configuration
   - Host, port, and worker settings
   - CORS and authentication policies
   - Debug and reload settings

6. **LoggingSettings**: Logging configuration
   - Log level and format
   - Optional file output

7. **MonitoringSettings**: Observability configuration
   - Prometheus metrics settings
   - Tracing configuration

8. **WebhookSettings**: Webhook handling configuration
   - Signing secrets
   - Timeout and retry policies

9. **SecuritySettings**: Security-related settings
   - Secret keys
   - JWT algorithm and expiration

## Using the Configuration System

The configuration system is designed to be used through a singleton instance accessed via the `get_settings()` function:

```python
from src.config import get_settings

# Access settings
settings = get_settings()

# Access nested settings
database_url = settings.database.connection_string
supabase_key = settings.supabase.key.get_secret_value()
```

The `get_settings()` function uses caching to avoid re-parsing environment variables on each call, which is especially important when using FastAPI dependency injection.

## Environment Variables

All configuration settings can be set through environment variables. The system follows these conventions:

1. Environment variables override default values
2. Variable names follow the naming convention of the settings class fields (uppercase with underscores)
3. Nested settings use a flat namespace (e.g., `DATABASE_HOST` for `settings.database.host`)

A template file (`.env.template`) is provided with all available settings and their descriptions.

## Docker Configuration

The Docker setup is designed to work seamlessly with the configuration system:

1. Environment variables can be passed to containers through:
   - `.env` file (via `env_file` in docker-compose.yml)
   - Environment variables in the docker-compose.yml
   - Command-line environment variables when running containers

2. Sensible defaults are provided for development but should be overridden in production

## Secrets Management

Sensitive information (passwords, API keys, etc.) is handled securely:

1. Sensitive values are stored as `SecretStr` in Pydantic models
2. Values are masked in logs and error messages
3. Special methods are required to access actual values (e.g., `password.get_secret_value()`)

In a production environment, you should use a dedicated secrets management solution:

- For Kubernetes: Use Kubernetes Secrets
- For AWS: Use AWS Secrets Manager or Parameter Store
- For GCP: Use GCP Secret Manager

## Best Practices

1. **Never commit secrets to the repository**
   - Use `.env.template` to document required environment variables
   - Actual `.env` files should be in `.gitignore`

2. **Use different configuration for different environments**
   - Set `ENVIRONMENT` variable to switch environments
   - Use environment-specific `.env` files (e.g., `.env.production`)

3. **Validate configuration at startup**
   - The Pydantic models automatically validate all settings
   - Add additional validation as needed

4. **Centralize all configuration**
   - Avoid hardcoded values throughout the codebase
   - Always reference settings through the configuration system
