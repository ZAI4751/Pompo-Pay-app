"use client";

/**
 * Resolves the current user's effective permissions for UI-level
 * show/hide decisions ONLY -- see docs/admin-ui-architecture.md,
 * "RBAC-aware frontend". The backend remains the sole security boundary;
 * every real mutation still gets its own server-side authorization check
 * regardless of what this hook returns.
 *
 * TEMPORARY BRIDGE: the backend's M003 /auth/me response does not yet
 * include effective permissions (M004's RBAC API was still in development
 * as of this build), so permissions are resolved here from the mock role
 * catalog by the user's role_id. Replace `resolveMockPermissions` with a
 * real call once the backend exposes effective permissions -- the
 * `usePermissions()` call sites elsewhere in the app do not need to change.
 */

import { useMemo } from "react";
import { useAuth } from "./AuthContext";
import { mockRoleDetails } from "@/mocks/data";

function resolveMockPermissions(roleId: string | undefined): Set<string> {
  if (!roleId) return new Set();
  const role = mockRoleDetails[roleId];
  if (!role) return new Set();
  return new Set(role.permissions.map((permission) => permission.code));
}

export function usePermissions() {
  const { user } = useAuth();
  const permissions = useMemo(() => resolveMockPermissions(user?.role_id), [user?.role_id]);

  return {
    permissions,
    hasPermission: (code: string) => permissions.has(code),
  };
}
