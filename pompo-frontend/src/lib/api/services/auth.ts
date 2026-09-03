/**
 * Live authentication against /api/v1/auth. Not gated by USE_MOCKS — demo
 * login is handled in AuthContext so credentials are never sent in demo mode.
 */

import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { AuthenticatedUser, LoginRequest, TokenResponse } from "@/lib/types/auth";
import type { ApiResult } from "@/lib/types/common";

export const authService = {
  login(payload: LoginRequest): Promise<ApiResult<TokenResponse>> {
    return apiRequest<TokenResponse>("/auth/login", { method: "POST", body: payload });
  },

  registerCustomer(payload: {
    email: string;
    password: string;
    full_name: string;
    phone: string;
  }): Promise<
    ApiResult<
      TokenResponse & {
        user_id: string;
        email: string;
        full_name: string;
        phone: string;
      }
    >
  > {
    return apiRequest("/customers/register", { method: "POST", body: payload });
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

  changePassword(currentPassword: string, newPassword: string): Promise<ApiResult<undefined>> {
    if (USE_MOCKS) {
      return Promise.resolve({
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot change passwords. Sign in against the backend.",
      });
    }
    return apiRequest<undefined>("/auth/change-password", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
    });
  },

  logoutAll(): Promise<ApiResult<undefined>> {
    if (USE_MOCKS) {
      return Promise.resolve({
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot revoke sessions. Sign in against the backend.",
      });
    }
    return apiRequest<undefined>("/auth/logout-all", { method: "POST" });
  },
};
