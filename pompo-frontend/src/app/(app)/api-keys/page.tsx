"use client";

import { useEffect, useState, type FormEvent } from "react";
import { KeySquare } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Table, TableHead, Th, TableBody, Tr, Td, MonoId } from "@/components/ui/Table";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ConfirmationDialog } from "@/components/ui/ConfirmationDialog";
import { merchantsService } from "@/lib/api/services/merchants";
import { branchesService } from "@/lib/api/services/branches";
import { tillsService } from "@/lib/api/services/tills";
import { integrationsService } from "@/lib/api/services/integrations";
import { useAuth } from "@/lib/auth/AuthContext";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useToast } from "@/components/ui/Toast";
import type { Branch, Merchant, Till } from "@/lib/types/merchant";
import type { IntegrationClient, OutboundWebhookDelivery } from "@/lib/types/integration";
import type { ApiResult } from "@/lib/types/common";

const selectClass =
  "mt-1 block w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm text-text";

export default function ApiKeysPage() {
  const { isDemoSession } = useAuth();
  const { hasPermission } = usePermissions();
  const { push } = useToast();
  const canRead = hasPermission("api_keys:read");
  const canCreate = hasPermission("api_keys:create");
  const canRevoke = hasPermission("api_keys:revoke");

  const [merchantsResult, setMerchantsResult] = useState<ApiResult<Merchant[]> | null>(null);
  const [merchantId, setMerchantId] = useState("");
  const [branches, setBranches] = useState<Branch[]>([]);
  const [tills, setTills] = useState<Till[]>([]);
  const [result, setResult] = useState<ApiResult<IntegrationClient[]> | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [clientType, setClientType] = useState<"developer" | "merchant_pos" | "partner">("merchant_pos");
  const [branchId, setBranchId] = useState("");
  const [tillId, setTillId] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [secretOpen, setSecretOpen] = useState(false);
  const [oneTimeKey, setOneTimeKey] = useState("");
  const [oneTimeWebhook, setOneTimeWebhook] = useState("");
  const [revokeTarget, setRevokeTarget] = useState<IntegrationClient | null>(null);
  const [revoking, setRevoking] = useState(false);
  const [selected, setSelected] = useState<IntegrationClient | null>(null);
  const [deliveries, setDeliveries] = useState<OutboundWebhookDelivery[] | null>(null);

  useEffect(() => {
    void merchantsService.list().then((list) => {
      setMerchantsResult(list);
      if (list.status === "success" && list.data[0] && !merchantId) {
        setMerchantId(list.data[0].id);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!merchantId) return;
    void integrationsService.list(merchantId).then(setResult);
    void branchesService.list(merchantId).then((list) => {
      if (list.status === "success") {
        setBranches(list.data);
        setBranchId(list.data[0]?.id ?? "");
      }
    });
  }, [merchantId]);

  useEffect(() => {
    if (!branchId) return;
    let cancelled = false;
    void tillsService.list(branchId).then((list) => {
      if (cancelled) return;
      if (list.status === "success") {
        setTills(list.data);
        setTillId(list.data[0]?.id ?? "");
      }
    });
    return () => {
      cancelled = true;
    };
  }, [branchId]);

  const merchants = merchantsResult?.status === "success" ? merchantsResult.data : [];
  const items = result?.status === "success" ? result.data : [];

  async function onCreate(event?: FormEvent) {
    event?.preventDefault();
    setSaving(true);
    setFormError(null);
    const created = await integrationsService.create({
      name,
      client_type: clientType,
      environment: "sandbox",
      merchant_id: merchantId,
      branch_id: branchId || null,
      till_id: tillId || null,
      webhook_url: webhookUrl || null,
    });
    setSaving(false);
    if (created.status === "error") {
      setFormError(created.message);
      return;
    }
    setFormOpen(false);
    setName("");
    setWebhookUrl("");
    setOneTimeKey(created.data.api_key);
    setOneTimeWebhook(created.data.webhook_signing_secret ?? "");
    setSecretOpen(true);
    push("Integration client created", "success");
    void integrationsService.list(merchantId).then(setResult);
  }

  async function onRotate(row: IntegrationClient) {
    const rotated = await integrationsService.rotateKey(row.id);
    if (rotated.status === "error") {
      push(rotated.message, "error");
      return;
    }
    setOneTimeKey(rotated.data.api_key);
    setOneTimeWebhook("");
    setSecretOpen(true);
    push("API key rotated. Copy it now — it will not be shown again.", "success");
    void integrationsService.list(merchantId).then(setResult);
  }

  async function onRevoke() {
    if (!revokeTarget) return;
    setRevoking(true);
    const removed = await integrationsService.revoke(revokeTarget.id);
    setRevoking(false);
    if (removed.status === "error") {
      push(removed.message, "error");
      return;
    }
    setRevokeTarget(null);
    push("Integration revoked", "success");
    void integrationsService.list(merchantId).then(setResult);
  }

  async function openDeliveries(row: IntegrationClient) {
    setSelected(row);
    const listed = await integrationsService.listDeliveries(row.id);
    setDeliveries(listed.status === "success" ? listed.data : []);
  }

  return (
    <PageShell
      title="API Keys"
      breadcrumb={[{ label: "Platform" }, { label: "API Keys" }]}
      actions={
        <div className="flex items-center gap-2">
          {isDemoSession && <MockDataBadge />}
          {canCreate && (
            <Button size="sm" onClick={() => setFormOpen(true)} disabled={!merchantId}>
              New integration
            </Button>
          )}
        </div>
      }
    >
      {!canRead && (
        <ErrorState kind="forbidden" description="You do not have permission to view API clients." />
      )}

      {canRead && (
        <div className="mb-4">
          <label className="text-sm text-text-muted">
            Merchant
            <select
              className={selectClass}
              value={merchantId}
              onChange={(event) => setMerchantId(event.target.value)}
            >
              {merchants.map((merchant) => (
                <option key={merchant.id} value={merchant.id}>
                  {merchant.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {canRead && result === null && <TableSkeleton rows={5} cols={6} />}

      {canRead && result?.status === "error" && (
        <ErrorState kind={result.kind} description={result.message} requestId={result.requestId} />
      )}

      {canRead && result?.status === "success" && items.length === 0 && (
        <EmptyState
          icon={KeySquare}
          title="No integration clients"
          description="Create a POS or developer client to issue a hashed API key. The secret is shown only once."
        />
      )}

      {canRead && result?.status === "success" && items.length > 0 && (
        <Table>
          <TableHead>
            <tr>
              <Th>Client</Th>
              <Th>Type</Th>
              <Th>Key prefix</Th>
              <Th>Last used</Th>
              <Th>Status</Th>
              <Th>Actions</Th>
            </tr>
          </TableHead>
          <TableBody>
            {items.map((row) => {
              const activeKey = row.keys.find((key) => key.is_active && !key.revoked_at);
              return (
                <Tr key={row.id}>
                  <Td>
                    <div className="font-medium">{row.name}</div>
                    <MonoId>{row.public_id}</MonoId>
                  </Td>
                  <Td>{row.client_type}</Td>
                  <Td>
                    <MonoId>{activeKey?.key_prefix ?? "—"}</MonoId>
                  </Td>
                  <Td>{row.last_used_at ? new Date(row.last_used_at).toLocaleString() : "—"}</Td>
                  <Td>
                    <ActiveBadge isActive={row.status === "active"} />
                    <span className="ml-2 capitalize">{row.status}</span>
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="secondary" size="sm" onClick={() => void openDeliveries(row)}>
                        Deliveries
                      </Button>
                      {canCreate && row.status === "active" && (
                        <Button variant="secondary" size="sm" onClick={() => void onRotate(row)}>
                          Rotate key
                        </Button>
                      )}
                      {canRevoke && row.status !== "revoked" && (
                        <Button variant="secondary" size="sm" onClick={() => setRevokeTarget(row)}>
                          Revoke
                        </Button>
                      )}
                    </div>
                  </Td>
                </Tr>
              );
            })}
          </TableBody>
        </Table>
      )}

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title="New integration client">
        <form className="space-y-3" onSubmit={(event) => void onCreate(event)}>
          <Input label="Name" value={name} onChange={(event) => setName(event.target.value)} required />
          <label className="text-sm text-text-muted">
            Client type
            <select
              className={selectClass}
              value={clientType}
              onChange={(event) =>
                setClientType(event.target.value as "developer" | "merchant_pos" | "partner")
              }
            >
              <option value="merchant_pos">Merchant POS</option>
              <option value="developer">Developer</option>
              <option value="partner">Partner</option>
            </select>
          </label>
          <label className="text-sm text-text-muted">
            Branch
            <select className={selectClass} value={branchId} onChange={(event) => setBranchId(event.target.value)}>
              {branches.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-text-muted">
            Till
            <select className={selectClass} value={tillId} onChange={(event) => setTillId(event.target.value)}>
              {tills.map((till) => (
                <option key={till.id} value={till.id}>
                  {till.name}
                </option>
              ))}
            </select>
          </label>
          <Input
            label="Partner webhook URL (optional)"
            value={webhookUrl}
            onChange={(event) => setWebhookUrl(event.target.value)}
            placeholder="https://example.com/pompo/webhooks"
          />
          {formError && <p className="text-sm text-error">{formError}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={saving}>
              Create
            </Button>
          </div>
        </form>
      </Modal>

      <Modal open={secretOpen} onClose={() => setSecretOpen(false)} title="Copy credentials now">
        <p className="mb-3 text-sm text-text-muted">
          These secrets are shown once. POMPO stores only hashes and prefixes.
        </p>
        <label className="text-sm text-text-muted">
          API key
          <textarea
            readOnly
            className="mt-1 h-20 w-full rounded-sm border border-border bg-surface-elevated p-2 font-mono text-xs"
            value={oneTimeKey}
          />
        </label>
        {oneTimeWebhook ? (
          <label className="mt-3 block text-sm text-text-muted">
            Webhook signing secret
            <textarea
              readOnly
              className="mt-1 h-20 w-full rounded-sm border border-border bg-surface-elevated p-2 font-mono text-xs"
              value={oneTimeWebhook}
            />
          </label>
        ) : null}
        <div className="mt-4 flex justify-end">
          <Button onClick={() => setSecretOpen(false)}>I have copied the secrets</Button>
        </div>
      </Modal>

      <Modal
        open={selected !== null}
        onClose={() => {
          setSelected(null);
          setDeliveries(null);
        }}
        title={selected ? `Deliveries · ${selected.name}` : "Deliveries"}
      >
        {deliveries && deliveries.length === 0 && <p className="text-sm text-text-muted">No outbound events yet.</p>}
        {deliveries && deliveries.length > 0 && (
          <ul className="space-y-2 text-sm">
            {deliveries.map((row) => (
              <li key={row.public_event_id} className="rounded-sm border border-border p-2">
                <MonoId>{row.public_event_id}</MonoId>
                <div>
                  {row.event_type} · {row.status} · attempts {row.attempt_count}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Modal>

      <ConfirmationDialog
        open={revokeTarget !== null}
        onCancel={() => setRevokeTarget(null)}
        title="Revoke integration?"
        description="The client and all API keys will stop working immediately."
        confirmLabel="Revoke"
        destructive
        loading={revoking}
        onConfirm={() => void onRevoke()}
      />
    </PageShell>
  );
}
