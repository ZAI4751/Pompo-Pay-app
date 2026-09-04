/** Master Admin eligibility. Backend remains authoritative. */

export function isPlatformAdminRole(roleCode: string | null | undefined): boolean {
  return roleCode === "platform_admin";
}

export function isDeactivatedLoginMessage(message: string | null | undefined): boolean {
  return Boolean(message && /deactivated/i.test(message));
}
