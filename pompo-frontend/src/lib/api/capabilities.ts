/**
 * Classification of Master Admin capabilities against the live backend.
 * "live" = a real /api/v1 contract exists. "unavailable" = no endpoint yet;
 * the UI must not present mock records as production data when mocks are off.
 */

export type CapabilityStatus = "live" | "unavailable";

export const API_CAPABILITIES = {
  auth: "live",
  merchants: "live",
  branches: "live",
  roles: "live",
  permissions: "live",
  rolePermissionGrants: "live",
  userRoleAssign: "live",
  usersDirectory: "unavailable",
  paymentsGet: "live",
  paymentsCreate: "live",
  paymentsCancel: "live",
  paymentsProcess: "live",
  paymentsList: "unavailable",
  providers: "live",
  health: "live",
  tills: "live",
  webhooks: "unavailable",
  auditLogs: "unavailable",
  apiKeys: "unavailable",
  reports: "unavailable",
} as const satisfies Record<string, CapabilityStatus>;
