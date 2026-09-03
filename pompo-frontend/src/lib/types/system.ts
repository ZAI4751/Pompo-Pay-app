/** Mirrors app/schemas/system.py PlatformConfigResponse. */

export interface PlatformConfig {
  configuration_source: "environment";
  writable: false;
  app_name: string;
  app_version: string;
  app_env: string;
  debug: boolean;
  api_v1_prefix: string;
  allowed_hosts: string[];
  cors_origins: string[];
  database_pool_size: number;
  database_max_overflow: number;
  database_pool_timeout: number;
  database_echo: boolean;
  redis_max_connections: number;
  jwt_algorithm: string;
  jwt_access_token_expire_minutes: number;
  jwt_refresh_token_expire_days: number;
  rate_limit_requests: number;
  rate_limit_window_seconds: number;
  rate_limit_auth_failures: number;
  outbound_webhook_timeout_seconds: number;
  outbound_webhook_max_attempts: number;
  log_level: string;
  log_json: boolean;
}
