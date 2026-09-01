/** Mirrors app/schemas/health.py */

export interface ComponentHealth {
  status: string;
  healthy: boolean;
  details?: Record<string, unknown> | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  components: Record<string, ComponentHealth>;
  response_time_ms: number;
}

export interface ReadinessResponse {
  ready: boolean;
  checks: Record<string, boolean>;
}

export interface LivenessResponse {
  alive: boolean;
}
