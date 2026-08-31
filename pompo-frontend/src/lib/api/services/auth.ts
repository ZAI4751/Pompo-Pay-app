/**
 * REAL backend integration -- calls the actual pompo-backend M003 endpoints.
 * This is the one service in the app not behind USE_MOCKS, because it's the
 * one part of the backend that's confirmed built and stable.
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
    });
  },

  logout(refreshToken: string): Promise<ApiResult<undefined>> {
    return apiRequest<undefined>("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
    });
  },

  me(accessToken: string): Promise<ApiResult<AuthenticatedUser>> {
    return apiRequest<AuthenticatedUser>("/auth/me", { accessToken });
  },
};
