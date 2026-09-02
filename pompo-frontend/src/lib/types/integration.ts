export interface IntegrationApiKey {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface IntegrationClient {
  id: string;
  public_id: string;
  name: string;
  client_type: "developer" | "merchant_pos" | "partner";
  environment: "sandbox" | "live";
  status: "active" | "disabled" | "revoked";
  merchant_id: string;
  branch_id: string | null;
  till_id: string | null;
  scopes: string[];
  webhook_url: string | null;
  webhook_secret_prefix: string | null;
  rate_limit_requests: number | null;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
  keys: IntegrationApiKey[];
}

export interface IntegrationClientCreated extends IntegrationClient {
  api_key: string;
  webhook_signing_secret: string | null;
}

export interface IntegrationClientCreate {
  name: string;
  client_type: "developer" | "merchant_pos" | "partner";
  environment: "sandbox" | "live";
  merchant_id: string;
  branch_id?: string | null;
  till_id?: string | null;
  scopes?: string[];
  webhook_url?: string | null;
}

export interface OutboundWebhookDelivery {
  public_event_id: string;
  event_type: string;
  destination_url: string;
  status: string;
  attempt_count: number;
  first_attempted_at: string | null;
  last_attempted_at: string | null;
  next_retry_at: string | null;
  response_status_code: number | null;
  failure_category: string | null;
  created_at: string;
}
