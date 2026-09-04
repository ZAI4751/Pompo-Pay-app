"use client";

/**
 * UX-only permission checks. Backend authorization remains authoritative.
 *
 * Codes come from GET /rbac/roles/{role_id} (permission_codes) after login.
 * /auth/me does not return permissions. When the role call is forbidden,
 * permissionCodes is null: hasPermission returns false so a non-admin
 * session cannot appear fully unlocked while APIs return 403.
 */

import { useCallback } from "react";
import { useAuth } from "./AuthContext";

export function usePermissions() {
  const { permissionCodes } = useAuth();

  const hasPermission = useCallback(
    (code: string) => {
      if (permissionCodes === null) return false;
      return permissionCodes.includes(code);
    },
    [permissionCodes],
  );

  return {
    permissions: new Set(permissionCodes ?? []),
    permissionsKnown: permissionCodes !== null,
    hasPermission,
  };
}
