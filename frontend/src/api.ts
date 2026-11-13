import type { Run } from "./types";
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
    credentials: "same-origin",
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message =
        typeof body.detail === "string" ? body.detail : body.error || message;
    } catch {
      /* bounded generic error */
    }
    throw new Error(message);
  }
  return response.json();
}
export const terminalStatuses = new Set([
  "verified",
  "unverified",
  "failed",
  "interrupted",
  "awaiting_verification",
  "cancelled",
]);
export function isVerified(run: Pick<Run, "status" | "verification">) {
  return (
    run.status === "verified" &&
    run.verification?.verified === true &&
    run.verification?.before?.exit_code !== undefined &&
    run.verification.before.exit_code === 1 &&
    run.verification.after?.exit_code === 0 &&
    run.verification.regression?.exit_code === 0
  );
}
export function formatDuration(start: string, end: string) {
  const sec = Math.max(
    0,
    Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000),
  );
  return Number.isFinite(sec)
    ? sec < 60
      ? `${sec}s`
      : `${Math.floor(sec / 60)}m ${sec % 60}s`
    : "—";
}
export function formatNumber(value: unknown) {
  return typeof value === "number"
    ? new Intl.NumberFormat("en-US").format(value)
    : "—";
}
