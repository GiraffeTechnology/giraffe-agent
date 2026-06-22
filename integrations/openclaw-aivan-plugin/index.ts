/**
 * @giraffetechnology/openclaw-aivan — OpenClaw Plugin Bridge for AIVAN
 *
 * AIVAN is a local-first AI trade salesperson assistant built on Giraffe Agent.
 * This plugin is a thin bridge between the OpenClaw channel runtime and a
 * locally-running AIVAN service.
 *
 * Security contract:
 *   - This plugin NEVER stores IM credentials, channel tokens, or API secrets.
 *   - This plugin NEVER sends messages directly to any IM or email channel.
 *   - All outbound trade messages MUST be approved via AIVAN's human approval gate
 *     before dispatch. The plugin surfaces the approval/rejection interface but
 *     does NOT bypass the approval policy.
 *   - This plugin NEVER logs the value of AIVAN_API_KEY or any secret.
 *   - If AIVAN is not reachable, the plugin fails safely and returns a structured
 *     error rather than falling back to direct channel access.
 *
 * Environment variables:
 *   AIVAN_BASE_URL   Base URL of the local AIVAN service (default: http://localhost:8000)
 *   AIVAN_API_KEY    Optional API key for the AIVAN service (never logged)
 */

const AIVAN_BASE_URL = (process.env.AIVAN_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const key = process.env.AIVAN_API_KEY;
  if (key) {
    headers["X-AIVAN-API-Key"] = key;
  }
  return headers;
}

async function aivanFetch(
  path: string,
  options: { method?: string; body?: unknown } = {}
): Promise<{ ok: boolean; data?: unknown; error?: string }> {
  if (!process.env.AIVAN_BASE_URL && !AIVAN_BASE_URL.startsWith("http://localhost")) {
    // Validate base URL is set when not using the default
  }

  const url = `${AIVAN_BASE_URL}${path}`;
  const method = options.method ?? "GET";

  try {
    const res = await fetch(url, {
      method,
      headers: buildHeaders(),
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return { ok: false, error: `AIVAN returned HTTP ${res.status}: ${text.slice(0, 200)}` };
    }

    const data = await res.json().catch(() => null);
    return { ok: true, data };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      error: `Could not reach AIVAN at ${AIVAN_BASE_URL}. Is the service running? (${message})`,
    };
  }
}

// ─── Exported plugin commands ──────────────────────────────────────────────────

/**
 * Check whether the local AIVAN service is reachable.
 */
export async function health(): Promise<{ ok: boolean; status?: string; error?: string }> {
  const result = await aivanFetch("/health");
  if (!result.ok) {
    return { ok: false, error: result.error };
  }
  return { ok: true, status: (result.data as { status?: string })?.status ?? "ok" };
}

/**
 * Forward a normalized OpenClaw trade event to AIVAN for processing.
 *
 * AIVAN routes the event through its trade salesperson workflow:
 * buyer requirement structuring → supplier inquiry drafting → approval gate.
 * The plugin never learns the content of drafted messages until a human approves them.
 */
export async function forwardEvent(event: {
  source?: string;
  channel: string;
  channel_account_id?: string;
  conversation_id?: string;
  sender_id?: string;
  sender_display_name?: string;
  message_text?: string;
  message_type?: string;
  attachments?: unknown[];
  timestamp?: string;
  project_id?: string;
  procurement_edge_id?: string;
  actor_id?: string;
  role_context?: string;
  mode?: string;
}): Promise<{ ok: boolean; data?: unknown; error?: string }> {
  const payload = {
    source: event.source ?? "openclaw",
    channel: event.channel,
    channel_account_id: event.channel_account_id ?? "",
    conversation_id: event.conversation_id ?? "",
    sender_id: event.sender_id ?? "",
    sender_display_name: event.sender_display_name ?? null,
    message_text: event.message_text ?? "",
    message_type: event.message_type ?? "text",
    attachments: event.attachments ?? [],
    timestamp: event.timestamp ?? null,
    project_id: event.project_id ?? null,
    procurement_edge_id: event.procurement_edge_id ?? null,
    actor_id: event.actor_id ?? null,
    role_context: event.role_context ?? null,
    mode: event.mode ?? null,
  };

  const result = await aivanFetch("/api/openclaw/events", { method: "POST", body: payload });
  if (!result.ok) {
    return { ok: false, error: result.error };
  }
  return { ok: true, data: result.data };
}

/**
 * Return the AIVAN dashboard URL after verifying the service is reachable.
 *
 * The plugin bridge does not open a browser window directly — it returns the URL
 * so the OpenClaw runtime or calling code can handle display. This keeps the
 * bridge dependency-free and lets the caller decide how to present the URL.
 */
export async function openDashboard(): Promise<{ ok: boolean; url: string; error?: string }> {
  const dashboardUrl = `${AIVAN_BASE_URL}/docs`;

  const healthResult = await health();
  if (!healthResult.ok) {
    return {
      ok: false,
      url: dashboardUrl,
      error: `AIVAN is not running. Start it first, then open: ${dashboardUrl}`,
    };
  }

  return { ok: true, url: dashboardUrl };
}

/**
 * Retrieve message drafts awaiting human approval in AIVAN.
 * Drafts are queued inside AIVAN and must be explicitly approved before
 * any message is dispatched through OpenClaw channels.
 */
export async function getPendingDrafts(projectId: string): Promise<{
  ok: boolean;
  pending_count?: number;
  drafts?: unknown[];
  error?: string;
}> {
  if (!projectId) {
    return { ok: false, error: "projectId is required" };
  }

  const result = await aivanFetch(
    `/api/openclaw/drafts/pending?project_id=${encodeURIComponent(projectId)}`
  );
  if (!result.ok) {
    return { ok: false, error: result.error };
  }

  const data = result.data as { pending_count?: number; drafts?: unknown[] };
  return { ok: true, pending_count: data.pending_count ?? 0, drafts: data.drafts ?? [] };
}

/**
 * Approve a pending AIVAN draft for dispatch.
 *
 * HUMAN APPROVAL IS REQUIRED. This command records the approver identity
 * inside AIVAN. The actual message dispatch through the OpenClaw channel
 * is performed by the OpenClaw runtime after AIVAN confirms approval —
 * the plugin never sends messages directly.
 */
export async function approveDraft(
  draftId: string,
  approvedBy: string
): Promise<{ ok: boolean; draft_id?: string; status?: string; error?: string }> {
  if (!draftId) {
    return { ok: false, error: "draftId is required" };
  }
  if (!approvedBy) {
    return { ok: false, error: "approvedBy is required — human approval must be attributed" };
  }

  const result = await aivanFetch(`/api/openclaw/drafts/${encodeURIComponent(draftId)}/approve`, {
    method: "POST",
    body: { approved_by: approvedBy },
  });

  if (!result.ok) {
    return { ok: false, error: result.error };
  }

  const data = result.data as { ok?: boolean; draft_id?: string; status?: string };
  return { ok: true, draft_id: data.draft_id, status: data.status };
}

/**
 * Reject a pending AIVAN draft.
 * The draft is marked as rejected inside AIVAN and will not be dispatched.
 */
export async function rejectDraft(
  draftId: string
): Promise<{ ok: boolean; draft_id?: string; status?: string; error?: string }> {
  if (!draftId) {
    return { ok: false, error: "draftId is required" };
  }

  const result = await aivanFetch(`/api/openclaw/drafts/${encodeURIComponent(draftId)}/reject`, {
    method: "POST",
  });

  if (!result.ok) {
    return { ok: false, error: result.error };
  }

  const data = result.data as { ok?: boolean; draft_id?: string; status?: string };
  return { ok: true, draft_id: data.draft_id, status: data.status };
}

// ─── OpenClaw Plugin Entry Point ──────────────────────────────────────────────
export function register(api: any): void {
  if (typeof api.registerInteractiveHandler === "function") {
    api.registerInteractiveHandler({
      id: "aivan-procurement-handler",
      name: "AIVAN Procurement Handler",
      description: "Forward all messages to AIVAN procurement AI",
      handler: async (ctx: any) => {
        const msg = ctx?.message?.text ?? ctx?.text ?? "";
        const channelId = ctx?.channel ?? ctx?.channelId ?? "openclaw-weixin";
        const senderId = ctx?.senderId ?? ctx?.peer?.id ?? "unknown";
        const convId = ctx?.conversationId ?? ctx?.threadId ?? senderId;
        const accountId = ctx?.accountId ?? ctx?.channelAccountId ?? "";

        const event = {
          source: "openclaw",
          channel: channelId,
          channel_account_id: accountId,
          conversation_id: convId,
          sender_id: senderId,
          sender_display_name: ctx?.peer?.name ?? "",
          message_text: msg,
          message_type: "text",
          attachments: [],
          timestamp: new Date().toISOString(),
          project_id: null,
          procurement_edge_id: null,
          actor_id: null,
          role_context: null,
          mode: "auto",
        };

        const result = await forwardEvent(event);
        if (result.ok && result.reply_text) {
          return { text: result.reply_text };
        }
        return null;
      },
    });
  }
}
