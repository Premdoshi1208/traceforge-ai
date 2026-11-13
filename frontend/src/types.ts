export type Config = {
  groq_configured: boolean;
  verification_mode: string;
  verification_notice?: string;
  capacity?: {
    daily_remaining: number;
    session_remaining: number;
    active: number;
  };
  models: string[];
  limits: Record<string, number | string>;
  github_url?: string;
  storage?: string;
  version?: string;
};
export type Scenario = {
  id: string;
  title: string;
  description: string;
  service: string;
  severity: string;
  expected_failure?: string;
};
export type EventRecord = {
  id: string;
  type: string;
  agent?: string;
  message: string;
  data?: unknown;
  created_at: string;
};
export type Evidence = {
  id: string;
  kind: string;
  title: string;
  data: unknown;
};
export type TestResult = {
  exit_code: number;
  output: string;
  command?: string;
  duration_ms?: number;
  passed?: number;
  failed?: number;
};
export type Hypothesis = {
  id?: string;
  title?: string;
  description?: string;
  hypothesis?: string;
  evidence_ids?: string[];
  evidence?: string[];
  assessment?: string;
  status?: string;
  confidence?: string | number;
  supporting_evidence?: string[];
  contradicting_evidence?: string[];
  [key: string]: unknown;
};
export type Run = {
  id: string;
  scenario_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  model?: string;
  events: EventRecord[];
  evidence: Evidence[];
  hypotheses: Hypothesis[];
  patch: null | { path: string; before: string; after: string; diff: string };
  verification: null | {
    before?: TestResult;
    after?: TestResult;
    regression?: TestResult;
    verified: boolean;
    mode: string;
    job_url?: string;
    [key: string]: unknown;
  };
  review: null | { approved: boolean; risks: string[]; summary: string };
  report?: string;
  usage?: { requests: number; tokens: number };
  error?: string;
  approval?: { status?: string; pr_url?: string };
  [key: string]: unknown;
};
export type EvaluationCase = {
  id?: string;
  name?: string;
  title?: string;
  description?: string;
  status?: string;
  passed?: boolean;
  result?: unknown;
  [key: string]: unknown;
};
export type Evaluation = {
  cases: EvaluationCase[];
  summary: Record<string, unknown>;
};
