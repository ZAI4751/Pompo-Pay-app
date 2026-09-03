"use client";

import { PageShell } from "@/components/layout/PageShell";
import { BackendUnavailable } from "@/components/ui/ComingSoon";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { useAuth } from "@/lib/auth/AuthContext";

export default function UsersPage() {
  const { isDemoSession } = useAuth();
  return (
    <PageShell
      title="Users"
      breadcrumb={[{ label: "Organization" }, { label: "Users" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
      <BackendUnavailable
        feature="User directory"
        detail="The backend has no user list or user CRUD API, so Master Admin cannot yet display account lifecycle (ACTIVE / DEACTIVATED / SUSPENDED) in a directory. Role assignment exists at PUT /api/v1/rbac/users/{user_id}/role. GET /auth/me already returns account_status for the signed-in user. This screen will not invent a staff directory."
      />
    </PageShell>
  );
}
