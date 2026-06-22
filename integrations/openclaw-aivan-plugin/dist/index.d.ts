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
/**
 * Check whether the local AIVAN service is reachable.
 */
export declare function health(): Promise<{
    ok: boolean;
    status?: string;
    error?: string;
}>;
/**
 * Forward a normalized OpenClaw trade event to AIVAN for processing.
 *
 * AIVAN routes the event through its trade salesperson workflow:
 * buyer requirement structuring → supplier inquiry drafting → approval gate.
 * The plugin never learns the content of drafted messages until a human approves them.
 */
export declare function forwardEvent(event: {
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
}): Promise<{
    ok: boolean;
    data?: unknown;
    error?: string;
}>;
/**
 * Return the AIVAN dashboard URL after verifying the service is reachable.
 *
 * The plugin bridge does not open a browser window directly — it returns the URL
 * so the OpenClaw runtime or calling code can handle display. This keeps the
 * bridge dependency-free and lets the caller decide how to present the URL.
 */
export declare function openDashboard(): Promise<{
    ok: boolean;
    url: string;
    error?: string;
}>;
/**
 * Retrieve message drafts awaiting human approval in AIVAN.
 * Drafts are queued inside AIVAN and must be explicitly approved before
 * any message is dispatched through OpenClaw channels.
 */
export declare function getPendingDrafts(projectId: string): Promise<{
    ok: boolean;
    pending_count?: number;
    drafts?: unknown[];
    error?: string;
}>;
/**
 * Approve a pending AIVAN draft for dispatch.
 *
 * HUMAN APPROVAL IS REQUIRED. This command records the approver identity
 * inside AIVAN. The actual message dispatch through the OpenClaw channel
 * is performed by the OpenClaw runtime after AIVAN confirms approval —
 * the plugin never sends messages directly.
 */
export declare function approveDraft(draftId: string, approvedBy: string): Promise<{
    ok: boolean;
    draft_id?: string;
    status?: string;
    error?: string;
}>;
/**
 * Reject a pending AIVAN draft.
 * The draft is marked as rejected inside AIVAN and will not be dispatched.
 */
export declare function rejectDraft(draftId: string): Promise<{
    ok: boolean;
    draft_id?: string;
    status?: string;
    error?: string;
}>;
declare const _default: {
    name: string;
    version: string;
    commands: {
        "aivan.health": typeof health;
        "aivan.forwardEvent": typeof forwardEvent;
        "aivan.openDashboard": typeof openDashboard;
        "aivan.getPendingDrafts": typeof getPendingDrafts;
        "aivan.approveDraft": typeof approveDraft;
        "aivan.rejectDraft": typeof rejectDraft;
    };
};
export default _default;
export declare function register(api: any): void;
