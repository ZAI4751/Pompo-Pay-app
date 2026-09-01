"use client";

/**
 * UX-only permission checks. Backend authorization remains authoritative.
 *
 * Codes come from GET /rbac/roles/{role_id} (permission_codes) after login.
 * /auth/me does not return permissions. When the role call is forbidden,
 * permissionCodes is null: hasPermission returns true so we do not hide
 * capabilities we cannot prove the user lacks.
 */

import { useCallback } from "react";
import { useAuth } from "./AuthContext";

export function usePermissions() {
  const { permissionCodes } = useAuth();

  const hasPermission = useCallback(
    (code: string) => {
      if (permissionCodes === null) return true;
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
