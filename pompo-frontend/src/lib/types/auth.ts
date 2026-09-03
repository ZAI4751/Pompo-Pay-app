/**
 * Mirrors the CONFIRMED backend contract from pompo-backend M003
 * (app/schemas/auth.py, app/api/v1/auth.py) exactly -- field names and
 * shapes are not invented. This is the one service in this app backed by
 * a real, already-implemented API (see docs/admin-ui-architecture.md,
 * "Mock/API boundary").
 */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  is_email_verified?: boolean;
}

export interface AuthenticatedUser {
  id: string;
  email: string;
  full_name: string;
  merchant_id: string | null;
  branch_id: string | null;
  role_id: string;
  role_code?: string;
  is_active: boolean;
  is_email_verified?: boolean;
  phone?: string | null;
}
