import { describe, it, expect } from "vitest";
import { isVerified, formatDuration } from "./api";
describe("evidence-based verdicts", () => {
  const proof = {
    verified: true,
    mode: "github_actions",
    before: { exit_code: 1, output: "TypeError" },
    after: { exit_code: 0, output: "OK" },
    regression: { exit_code: 0, output: "OK" },
  };
  it("accepts only an actually verified result", () => {
    expect(isVerified({ status: "verified", verification: proof })).toBe(true);
  });
  it("rejects a success label without test evidence", () => {
    expect(isVerified({ status: "verified", verification: null })).toBe(false);
  });
  it("rejects a baseline that never failed", () => {
    expect(
      isVerified({
        status: "verified",
        verification: { ...proof, before: { exit_code: 0, output: "OK" } },
      }),
    ).toBe(false);
  });
  it("rejects a regression failure", () => {
    expect(
      isVerified({
        status: "verified",
        verification: {
          ...proof,
          regression: { exit_code: 1, output: "FAIL" },
        },
      }),
    ).toBe(false);
  });
  it("rejects a pending review even when tests passed", () => {
    expect(isVerified({ status: "reviewing", verification: proof })).toBe(
      false,
    );
  });
  it("formats measured elapsed time", () => {
    expect(formatDuration("2026-11-13T10:00:00Z", "2026-11-13T10:01:05Z")).toBe(
      "1m 5s",
    );
  });
});
