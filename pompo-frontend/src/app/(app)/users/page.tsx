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
        detail="The backend has no user list or user CRUD API. Role assignment exists at PUT /api/v1/rbac/users/{user_id}/role and removal is rejected because every user must retain one role. This screen will not invent a staff directory."
      />
    </PageShell>
  );
}
