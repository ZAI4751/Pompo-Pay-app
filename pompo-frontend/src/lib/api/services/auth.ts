/**
 * Live authentication against /api/v1/auth. Not gated by USE_MOCKS — demo
 * login is handled in AuthContext so credentials are never sent in demo mode.
 */

import { apiRequest } from "../client";
import type { AuthenticatedUser, LoginRequest, TokenResponse } from "@/lib/types/auth";
import type { ApiResult } from "@/lib/types/common";

export const authService = {
  login(payload: LoginRequest): Promise<ApiResult<TokenResponse>> {
    return apiRequest<TokenResponse>("/auth/login", { method: "POST", body: payload });
  },

  refresh(refreshToken: string): Promise<ApiResult<TokenResponse>> {
    return apiRequest<TokenResponse>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      skipUnauthorizedHandler: true,
    });
  },

  logout(refreshToken: string): Promise<ApiResult<undefined>> {
    return apiRequest<undefined>("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
      skipUnauthorizedHandler: true,
    });
  },

  me(accessToken: string): Promise<ApiResult<AuthenticatedUser>> {
    return apiRequest<AuthenticatedUser>("/auth/me", {
      accessToken,
      skipUnauthorizedHandler: true,
    });
  },
};
