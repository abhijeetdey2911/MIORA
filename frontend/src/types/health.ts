export interface DatabaseHealth {
  status: 'connected' | 'disconnected';
  latency_ms: number | null;
  dialect: string;
  error?: string | null;
}

export interface ApiHealth {
  status: string;
  uptime_seconds: number;
}

export interface SystemInfo {
  python_version: string;
  environment: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  project: string;
  version: string;
  environment: string;
  timestamp: string;
  services: {
    database: DatabaseHealth;
    api: ApiHealth;
  };
  system: SystemInfo;
}

export type ConnectionState = 'online' | 'degraded' | 'offline' | 'checking';

export interface HealthCheckResult {
  state: ConnectionState;
  data: HealthResponse | null;
  latencyMs: number | null;
  error: string | null;
  lastChecked: Date | null;
}
