import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import {
  Activity,
  ArrowDown,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Boxes,
  Braces,
  Check,
  CheckCheck,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Code2,
  Command,
  Copy,
  Database,
  ExternalLink,
  FileCode2,
  FileText,
  FlaskConical,
  GitBranch,
  GitPullRequest,
  Globe,
  Layers,
  LayoutDashboard,
  LoaderCircle,
  LockKeyhole,
  Menu,
  Network,
  Play,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  TriangleAlert,
  X,
  XCircle,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type {
  Config,
  Evaluation,
  Evidence,
  Run,
  Scenario,
  TestResult,
} from "./types";
import {
  api,
  formatDuration,
  formatNumber,
  isVerified,
  terminalStatuses,
} from "./api";

const roles = [
  {
    key: "commander",
    name: "Incident commander",
    short: "Commander",
    icon: Command,
    detail:
      "Plans the investigation, selects the next tool, and enforces the run budget.",
  },
  {
    key: "telemetry",
    name: "Telemetry investigator",
    short: "Telemetry",
    icon: Activity,
    detail:
      "Collects observed request failures, service spans, and correlated logs.",
  },
  {
    key: "reasoner",
    name: "Root-cause reasoner",
    short: "Reasoner",
    icon: Search,
    detail:
      "Compares competing explanations against concrete evidence references.",
  },
  {
    key: "reproducer",
    name: "Reproduction engineer",
    short: "Reproduce",
    icon: FlaskConical,
    detail:
      "Runs the failure against the original controlled fixture and records the result.",
  },
  {
    key: "patcher",
    name: "Patch engineer",
    short: "Patch",
    icon: Code2,
    detail:
      "Proposes a minimal change restricted to the affected fixture source.",
  },
  {
    key: "reviewer",
    name: "Adversarial reviewer",
    short: "Review",
    icon: ShieldCheck,
    detail:
      "Challenges the diagnosis, verification evidence, and regression risks.",
  },
  {
    key: "reporter",
    name: "Incident reporter",
    short: "Report",
    icon: FileText,
    detail:
      "Builds a reviewable postmortem from the recorded execution evidence.",
  },
];
const stageOrder = [
  "queued",
  "observing",
  "investigating",
  "reproducing",
  "patching",
  "verifying",
  "reviewing",
  "verified",
];
type DataContext = {
  config: Config | null;
  scenarios: Scenario[];
  runs: Run[];
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
};
const Data = createContext<DataContext>({
  config: null,
  scenarios: [],
  runs: [],
  loading: true,
  error: "",
  refresh: async () => {},
});
function DataProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<Config | null>(null),
    [scenarios, setScenarios] = useState<Scenario[]>([]),
    [runs, setRuns] = useState<Run[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  async function refresh() {
    const results = await Promise.allSettled([
      api<Config>("/api/config"),
      api<Scenario[]>("/api/scenarios"),
      api<Run[]>("/api/runs"),
    ]);
    if (results[0].status === "fulfilled") setConfig(results[0].value);
    if (results[1].status === "fulfilled")
      setScenarios(Array.isArray(results[1].value) ? results[1].value : []);
    if (results[2].status === "fulfilled")
      setRuns(Array.isArray(results[2].value) ? results[2].value : []);
    setError(
      results.every((r) => r.status === "rejected")
        ? "The backend is not reachable yet. Your evidence will appear when the connection is restored."
        : "",
    );
    setLoading(false);
  }
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 15000);
    return () => clearInterval(timer);
  }, []);
  return (
    <Data.Provider value={{ config, scenarios, runs, loading, error, refresh }}>
      {children}
    </Data.Provider>
  );
}
function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="logo">
      <span className="logo-mark">
        <i />
        <i />
        <i />
      </span>
      {!compact && (
        <>
          <span>TRACEFORGE</span>
          <span className="logo-ai">AI</span>
        </>
      )}
    </span>
  );
}
function Badge({
  status,
  children,
}: {
  status?: string;
  children?: ReactNode;
}) {
  return (
    <span className={`badge ${status || ""}`}>
      <span className="status-dot" />
      {children || status?.replaceAll("_", " ") || "standby"}
    </span>
  );
}
function Status({ run }: { run: Run }) {
  return (
    <Badge
      status={
        isVerified(run)
          ? "verified"
          : run.status === "verified"
            ? "unverified"
            : run.status
      }
    />
  );
}
function Button({
  children,
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className={`button ${className}`} {...props}>
      {children}
    </button>
  );
}
function Empty({
  icon: Icon = Activity,
  title,
  children,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon size={24} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
function ErrorMessage({ message }: { message: string }) {
  return message ? (
    <div className="error-banner" role="alert">
      <TriangleAlert size={16} />
      <span>{message}</span>
    </div>
  ) : null;
}
function Label({ children }: { children: ReactNode }) {
  return <div className="eyebrow">{children}</div>;
}
function date(value: string) {
  return value
    ? new Date(value).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
}
function time(value: string) {
  return value
    ? new Date(value).toLocaleTimeString(undefined, { hour12: false })
    : "—";
}
function textData(value: unknown) {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}
function PageHeading({
  label,
  title,
  description,
  action,
}: {
  label: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <Label>{label}</Label>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
function App() {
  return (
    <DataProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route element={<Shell />}>
          <Route path="/control" element={<Control />} />
          <Route path="/runs/:id" element={<RunPage />} />
          <Route path="/runs/:id/:tab" element={<RunPage />} />
          <Route path="/intelligence" element={<Intelligence />} />
          <Route path="/evaluations" element={<Evaluations />} />
          <Route path="/architecture" element={<Architecture />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </DataProvider>
  );
}
export default App;
import { Outlet } from "react-router-dom";
function Shell() {
  const [menu, setMenu] = useState(false);
  const { config, loading, error } = useContext(Data);
  const location = useLocation();
  useEffect(() => setMenu(false), [location.pathname]);
  const links = [
    { path: "/control", label: "Mission control", icon: LayoutDashboard },
    { path: "/intelligence", label: "Incident intelligence", icon: Layers },
    { path: "/evaluations", label: "Evaluation arena", icon: FlaskConical },
    { path: "/architecture", label: "Architecture", icon: Network },
  ];
  return (
    <div className="app-shell">
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <Link to="/" className="brand-link" aria-label="TraceForge home">
          <Logo />
        </Link>
        <div className="workspace">
          <span className="workspace-icon">
            <Boxes size={17} />
          </span>
          <span>
            Incident workspace<small>PUBLIC ENGINEERING LAB</small>
          </span>
          <ChevronDown size={14} />
        </div>
        <div className="sidebar-section-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {links.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `nav-item ${isActive ? "active" : ""}`
              }
            >
              <Icon size={17} />
              <span>{label}</span>
              {path === "/control" && <span className="nav-key">⌘ 1</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="mini-icon">
            <ShieldCheck size={17} />
          </span>
          <strong>Evidence over intuition.</strong>
          <p>Every verdict is backed by an actual execution record.</p>
          <Link to="/architecture">
            Explore the system <ArrowUpRight size={13} />
          </Link>
        </div>
        <div className="sidebar-bottom">
          <div>
            <span
              className={`connection-dot ${config?.groq_configured ? "connected" : ""}`}
            />
            <span>
              {loading
                ? "Connecting…"
                : config?.groq_configured
                  ? "Inference connected"
                  : "Inference not configured"}
            </span>
          </div>
          <span className="sidebar-version">
            TRACEFORGE / ENGINEERING PREVIEW
          </span>
        </div>
      </aside>
      {menu && (
        <button
          className="menu-overlay"
          aria-label="Close navigation"
          onClick={() => setMenu(false)}
        />
      )}
      <div className="app-main">
        <header className="app-topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="Toggle navigation"
              onClick={() => setMenu(!menu)}
            >
              <Menu size={20} />
            </button>
            <span className="breadcrumb-home">Workspace</span>
            <ChevronRight size={13} />
            <span>
              {location.pathname.includes("/runs/")
                ? "Investigation"
                : links.find((l) => l.path === location.pathname)?.label ||
                  "TraceForge"}
            </span>
          </div>
          <div className="topbar-right">
            <span className="controlled-label">
              <span className="status-dot" />
              Controlled environment
            </span>
            {config?.github_url && (
              <a
                className="topbar-github"
                href={config.github_url}
                target="_blank"
                rel="noreferrer"
              >
                Source <ArrowUpRight size={13} />
              </a>
            )}
            <span className="avatar">TF</span>
          </div>
        </header>
        <main className="page-content">
          <ErrorMessage message={error} />
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>
            <Logo compact /> Find the failure. Prove the fix.
          </span>
          <span>Controlled scenarios · Actual execution · Human approval</span>
        </footer>
      </div>
    </div>
  );
}
function Landing() {
  const { config, runs } = useContext(Data);
  const last = runs.find(isVerified);
  const [selected, setSelected] = useState(0);
  return (
    <div className="landing">
      <header className="landing-nav">
        <Link to="/" aria-label="TraceForge home">
          <Logo />
        </Link>
        <nav>
          <Link to="/architecture">Architecture</Link>
          <Link to="/evaluations">Evaluations</Link>
          {config?.github_url && (
            <a href={config.github_url} target="_blank" rel="noreferrer">
              GitHub <ArrowUpRight size={13} />
            </a>
          )}
        </nav>
        <Link className="button nav-launch" to="/control">
          Open workspace <ArrowUpRight size={15} />
        </Link>
      </header>
      <main>
        <section className="hero">
          <div className="hero-grid" />
          <div className="hero-copy">
            <div className="hero-eyebrow">
              <span className="status-dot" /> AUTONOMOUS INCIDENT RESPONSE{" "}
              <span className="hero-version">v1.0</span>
            </div>
            <h1>
              Production broke.
              <br />
              <span>
                Your AI engineer is
                <br className="desktop-break" /> already investigating.
              </span>
            </h1>
            <p>
              An autonomous system that traces failures, investigates code,
              generates repairs, and verifies fixes with executable evidence.
            </p>
            <div className="hero-actions">
              <Link className="button primary large" to="/control">
                <Play size={16} fill="currentColor" />
                Launch Incident Lab <ArrowRight size={17} />
              </Link>
              <Link className="button ghost large" to="/architecture">
                Explore architecture <ArrowUpRight size={16} />
              </Link>
            </div>
            <div className="hero-proof">
              <span>
                <ShieldCheck size={15} /> Evidence-backed verdicts
              </span>
              <span>
                <Braces size={15} /> Real code. Real tests.
              </span>
              <span>
                <LockKeyhole size={14} /> Human approval
              </span>
            </div>
          </div>
          <div className="hero-console">
            <div className="console-titlebar">
              <div className="window-dots">
                <i />
                <i />
                <i />
              </div>
              <span>traceforge / incident pipeline</span>
              <span className="console-mode">SYSTEM OVERVIEW</span>
            </div>
            <div className="console-body">
              <div className="console-intro">
                <span className="tiny-label">INVESTIGATION LIFECYCLE</span>
                <span className="mono muted">01 — 07</span>
              </div>
              <div className="hero-pipeline">
                {roles.map((role, i) => {
                  const Icon = role.icon;
                  return (
                    <button
                      key={role.key}
                      className={`hero-pipeline-step ${selected === i ? "selected" : ""}`}
                      onClick={() => setSelected(i)}
                      aria-pressed={selected === i}
                    >
                      <span className="step-number">0{i + 1}</span>
                      <span className="step-icon">
                        <Icon size={17} />
                      </span>
                      <span>{role.name}</span>
                      <ChevronRight size={14} />
                    </button>
                  );
                })}
              </div>
              <div className="pipeline-explanation">
                <span className="prompt-symbol">›</span>
                <div>
                  <strong>{roles[selected].name}</strong>
                  <p>{roles[selected].detail}</p>
                </div>
              </div>
            </div>
            <div className="console-footer">
              <span>
                <span className="status-dot" />
                Interactive system map
              </span>
              <span>Click a responsibility to inspect</span>
            </div>
          </div>
          <div className="hero-bottom-line">
            <span>BUILT FOR THE MOMENT THINGS BREAK</span>
            <span>
              OBSERVE <ArrowRight size={12} /> INVESTIGATE{" "}
              <ArrowRight size={12} /> REPAIR <ArrowRight size={12} /> PROVE
            </span>
          </div>
        </section>
        <section className="landing-section promise-section">
          <div>
            <Label>THE DIFFERENCE IS THE EVIDENCE</Label>
            <h2>
              A diagnosis is a theory.
              <br />
              <span>A passing test is proof.</span>
            </h2>
          </div>
          <p>
            Follow the complete chain from a failing request to a reviewable
            patch. Every log, hypothesis, code change, and test result stays
            attached to the incident that produced it.
          </p>
        </section>
        <section className="feature-grid landing-section">
          {[
            {
              n: "01",
              icon: Activity,
              title: "Follow the failure",
              text: "Launch a controlled fault in real executable software. Inspect request traces, service errors, and the source behind them.",
              tag: "CORRELATED TELEMETRY",
            },
            {
              n: "02",
              icon: GitBranch,
              title: "Watch the investigation",
              text: "Seven focused responsibilities collect evidence, compare hypotheses, reproduce the fault, and propose a bounded correction.",
              tag: "OBSERVABLE ORCHESTRATION",
            },
            {
              n: "03",
              icon: ShieldCheck,
              title: "Inspect the proof",
              text: "Compare the original failing test with the patched result. Review regression checks and the adversarial assessment.",
              tag: "TEST-DRIVEN VERIFICATION",
            },
          ].map(({ n, icon: Icon, title, text, tag }) => (
            <article className="feature-card" key={n}>
              <div className="feature-top">
                <Icon size={24} />
                <span>{n}</span>
              </div>
              <h3>{title}</h3>
              <p>{text}</p>
              <div className="feature-tag">
                {tag}
                <ArrowUpRight size={13} />
              </div>
            </article>
          ))}
        </section>
        <section className="landing-section recorded-section">
          <div>
            <Label>INSPECT, THEN EXECUTE</Label>
            <h2>
              No black box.
              <br />
              <span>The whole investigation.</span>
            </h2>
            <p>
              {last
                ? "Explore a completed investigation recorded from a verified execution, then launch a fresh controlled incident of your own."
                : "Start a controlled incident and follow the evidence as it arrives. Completed runs remain available for review without another model request."}
            </p>
            <Link
              className="button primary"
              to={last ? `/runs/${last.id}` : "/control"}
            >
              {last ? "Inspect a verified execution" : "Enter the incident lab"}
              <ArrowRight size={16} />
            </Link>
          </div>
          <div className="evidence-stack">
            <div>
              <FileCode2 size={20} />
              <span>
                <strong>Source & generated diff</strong>
                <small>Every changed line, available to inspect</small>
              </span>
              <span className="stack-label">PATCH</span>
            </div>
            <div>
              <Terminal size={20} />
              <span>
                <strong>Before & after test results</strong>
                <small>Actual output with exit codes and duration</small>
              </span>
              <span className="stack-label">PROOF</span>
            </div>
            <div>
              <FileText size={20} />
              <span>
                <strong>Technical postmortem</strong>
                <small>A reviewable account of what happened</small>
              </span>
              <span className="stack-label">REPORT</span>
            </div>
            {last && (
              <Link className="recorded-link" to={`/runs/${last.id}`}>
                <Badge status="verified" />
                Recorded from verified execution <ArrowUpRight size={14} />
              </Link>
            )}
          </div>
        </section>
        <section className="landing-cta">
          <div className="cta-cross">+</div>
          <Label>READY WHEN YOU ARE</Label>
          <h2>
            Find the failure. <span>Prove the fix.</span>
          </h2>
          <p>Break something safely. See what the evidence says.</p>
          <Link className="button primary large" to="/control">
            Launch Incident Lab <ArrowRight size={17} />
          </Link>
        </section>
      </main>
      <footer className="landing-footer">
        <Link to="/">
          <Logo />
        </Link>
        <p>Autonomous investigation. Accountable engineering.</p>
        <Link to="/architecture">
          System architecture <ArrowUpRight size={13} />
        </Link>
      </footer>
    </div>
  );
}

function Stats({ runs }: { runs: Run[] }) {
  const verified = runs.filter(isVerified).length;
  const active = runs.filter((r) => !terminalStatuses.has(r.status)).length;
  const requests = runs.reduce((n, r) => n + (r.usage?.requests || 0), 0);
  const cards = [
    {
      label: "Investigations",
      value: runs.length,
      detail: "Recorded execution runs",
      icon: Activity,
    },
    {
      label: "Verified repairs",
      value: verified,
      detail: "Failure → passing verification",
      icon: ShieldCheck,
    },
    {
      label: "Active investigations",
      value: active,
      detail: active ? "Work is in progress" : "Ready for a new incident",
      icon: Radio,
    },
    {
      label: "Model requests",
      value: requests,
      detail: "Actual provider calls",
      icon: Zap,
    },
  ];
  return (
    <div className="stats-grid">
      {cards.map(({ label, value, detail, icon: Icon }) => (
        <div className="stat-card" key={label}>
          <div>
            {label}
            <Icon size={16} />
          </div>
          <strong>
            {formatNumber(value)}
            <span>
              {label === "Verified repairs" && verified > 0 ? (
                <CheckCheck size={18} />
              ) : null}
            </span>
          </strong>
          <small>{detail}</small>
        </div>
      ))}
    </div>
  );
}
function Control() {
  const { config, scenarios, runs, loading, refresh } = useContext(Data);
  const [selected, setSelected] = useState(""),
    [launching, setLaunching] = useState(false),
    [launchError, setLaunchError] = useState("");
  const navigate = useNavigate();
  useEffect(() => {
    if (scenarios.length && !selected) setSelected(scenarios[0].id);
  }, [scenarios, selected]);
  const active = runs.find((r) => !terminalStatuses.has(r.status));
  const latest = runs[0];
  async function launch() {
    if (!selected || launching) return;
    setLaunching(true);
    setLaunchError("");
    try {
      const run = await api<Run>("/api/runs", {
        method: "POST",
        body: JSON.stringify({ scenario_id: selected }),
        headers: { "Idempotency-Key": crypto.randomUUID() },
      });
      await refresh();
      navigate(`/runs/${run.id}`);
    } catch (error) {
      setLaunchError((error as Error).message);
    } finally {
      setLaunching(false);
    }
  }
  return (
    <>
      <PageHeading
        label="OPERATIONS / OVERVIEW"
        title="Mission control"
        description="Your next incident. A complete chain of evidence."
        action={
          <Button className="secondary" onClick={() => void refresh()}>
            <RefreshCw size={14} />
            Refresh
          </Button>
        }
      />
      <Stats runs={runs} />
      <div className="control-grid">
        <section className="panel scenario-panel">
          <div className="panel-heading">
            <div>
              <span className="panel-icon">
                <FlaskConical size={17} />
              </span>
              <h2>Launch an incident</h2>
            </div>
            <span className="tiny-label">CONTROLLED SCENARIOS</span>
          </div>
          <div className="panel-description">
            Introduce a real fault. Let the investigation follow the evidence.
          </div>
          <div className="scenario-options">
            {loading ? (
              <div className="loading-inline">
                <LoaderCircle className="spin" size={18} />
                Loading incident scenarios…
              </div>
            ) : scenarios.length ? (
              scenarios.map((scenario, index) => (
                <button
                  className={`scenario-card ${selected === scenario.id ? "selected" : ""}`}
                  key={scenario.id}
                  onClick={() => setSelected(scenario.id)}
                  aria-pressed={selected === scenario.id}
                >
                  <div className="scenario-number">0{index + 1}</div>
                  <div className="scenario-body">
                    <div>
                      <strong>{scenario.title}</strong>
                      <span className="scenario-service">
                        {scenario.service}
                      </span>
                    </div>
                    <p>{scenario.description}</p>
                    <span className="scenario-meta">
                      <span className="severity-dot" />
                      {scenario.severity || "Controlled fault"}
                      <span>Seeded incident</span>
                    </span>
                  </div>
                  <span className="radio-select">
                    {selected === scenario.id && <Check size={10} />}
                  </span>
                </button>
              ))
            ) : (
              <Empty title="Scenarios are not available yet">
                The incident catalog will appear when the backend is ready.
              </Empty>
            )}
          </div>
          <ErrorMessage message={launchError} />
          <div className="launch-footer">
            <span>
              <LockKeyhole size={14} />
              Curated fixtures. Bounded execution.
            </span>
            <Button
              className="primary"
              disabled={
                !config?.groq_configured || !selected || launching || !!active
              }
              onClick={() => void launch()}
            >
              {launching ? (
                <LoaderCircle className="spin" size={15} />
              ) : (
                <Play size={13} fill="currentColor" />
              )}
              {launching
                ? "Launching…"
                : active
                  ? "Investigation active"
                  : "Launch investigation"}
              <ArrowRight size={15} />
            </Button>
          </div>
          {config?.verification_notice && (
            <div className="capacity-note">
              <ShieldCheck size={14} />
              {config.verification_notice}
            </div>
          )}
          {!config?.groq_configured && (
            <div className="capacity-note">
              <TriangleAlert size={14} />
              Live inference is unavailable until the backend is securely
              configured. Stored runs remain inspectable.
            </div>
          )}
          {active && (
            <Link className="active-run-link" to={`/runs/${active.id}`}>
              <Radio size={14} />
              Follow the active investigation <ArrowRight size={14} />
            </Link>
          )}
        </section>
        <section className="panel topology-panel">
          <div className="panel-heading">
            <div>
              <span className="panel-icon">
                <Network size={17} />
              </span>
              <h2>Incident environment</h2>
            </div>
            <span className="live-mini">LAB</span>
          </div>
          <ServiceGraph run={active || latest} />
          <div className="topology-legend">
            <span>
              <i className="legend-dot" />
              Instrumented module
            </span>
            <span>Same process · service boundaries</span>
          </div>
          <div className="environment-details">
            <div>
              <span>Model provider</span>
              <strong>
                Groq{" "}
                <span
                  className={`connection-dot ${config?.groq_configured ? "connected" : ""}`}
                />
              </strong>
            </div>
            <div>
              <span>Verification</span>
              <strong>
                {config?.verification_mode?.replaceAll("_", " ") ||
                  "Checking configuration"}
              </strong>
            </div>
            <div>
              <span>State persistence</span>
              <strong>{config?.storage || "Checking configuration"}</strong>
            </div>
          </div>
        </section>
      </div>
      <section className="panel recent-panel">
        <div className="panel-heading">
          <div>
            <span className="panel-icon">
              <Clock size={17} />
            </span>
            <h2>Recent investigations</h2>
            <span className="count-tag">{runs.length}</span>
          </div>
          <Link className="text-link" to="/intelligence">
            View all <ArrowUpRight size={14} />
          </Link>
        </div>
        <RunTable runs={runs.slice(0, 5)} scenarios={scenarios} />
      </section>
      <div className="control-bottom">
        <ShieldCheck size={17} />
        <span>
          <strong>A verdict must be earned.</strong> VERIFIED requires a failing
          baseline, a passing patched test, and passing regression checks.
        </span>
        <Link to="/architecture">
          How it works <ArrowUpRight size={13} />
        </Link>
      </div>
    </>
  );
}
function ServiceGraph({ run }: { run?: Run }) {
  const [service, setService] = useState("gateway");
  const services = [
    { id: "gateway", label: "API gateway", icon: Globe, x: 155, y: 20 },
    { id: "orders", label: "Orders", icon: Boxes, x: 155, y: 114 },
    { id: "payments", label: "Payments", icon: Zap, x: 48, y: 211 },
    { id: "inventory", label: "Inventory", icon: Database, x: 262, y: 211 },
  ];
  return (
    <div className="service-graph">
      <svg viewBox="0 0 390 285" aria-hidden="true">
        <path
          d="M195 69V114M195 163V187H88V211M195 187H302V211"
          fill="none"
          stroke="#294047"
          strokeWidth="1.5"
        />
        <circle cx="195" cy="187" r="3" fill="#69daca" />
      </svg>
      {services.map(({ id, label, icon: Icon, x, y }) => (
        <button
          className={`service-node ${service === id ? "selected" : ""}`}
          style={{ left: `${(x / 390) * 100}%`, top: `${(y / 285) * 100}%` }}
          key={id}
          onClick={() => setService(id)}
          aria-pressed={service === id}
        >
          <Icon size={17} />
          <strong>{label}</strong>
          <span className="service-node-status">
            {run?.status && !terminalStatuses.has(run.status)
              ? "OBSERVING"
              : "LAB MODULE"}
          </span>
        </button>
      ))}
      <div className="service-caption">
        <span className="mono">{service}</span> · Actual requests, correlated
        telemetry
      </div>
    </div>
  );
}
function RunTable({ runs, scenarios }: { runs: Run[]; scenarios: Scenario[] }) {
  if (!runs.length)
    return (
      <Empty title="No investigations yet" icon={Radio}>
        Launch your first controlled incident. Its timeline, evidence, and
        results will appear here.
      </Empty>
    );
  return (
    <div className="table-scroll">
      <table className="run-table">
        <thead>
          <tr>
            <th>INCIDENT</th>
            <th>STATUS</th>
            <th>MODEL CALLS</th>
            <th>STARTED</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>
                <Link to={`/runs/${run.id}`} className="run-title">
                  <span className={`run-glyph ${isVerified(run) ? "ok" : ""}`}>
                    {isVerified(run) ? (
                      <CheckCheck size={16} />
                    ) : (
                      <Activity size={16} />
                    )}
                  </span>
                  <span>
                    <strong>
                      {scenarios.find((s) => s.id === run.scenario_id)?.title ||
                        run.scenario_id}
                    </strong>
                    <small>{run.id.slice(0, 12)}</small>
                  </span>
                </Link>
              </td>
              <td>
                <Status run={run} />
              </td>
              <td className="mono">{run.usage?.requests || 0}</td>
              <td className="table-date">{date(run.created_at)}</td>
              <td>
                <Link
                  to={`/runs/${run.id}`}
                  className="icon-link"
                  aria-label={`Open investigation ${run.id}`}
                >
                  <ArrowUpRight size={16} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function useRun(id: string) {
  const [run, setRun] = useState<Run | null>(null),
    [error, setError] = useState(""),
    [connected, setConnected] = useState(false);
  const refreshRef = useRef<() => void>(() => {});
  useEffect(() => {
    let alive = true;
    let refreshing = false;
    const refresh = async () => {
      if (refreshing) return;
      refreshing = true;
      try {
        const next = await api<Run>(`/api/runs/${encodeURIComponent(id)}`);
        if (alive) {
          setRun(next);
          setError("");
        }
      } catch (e) {
        if (alive) setError((e as Error).message);
      } finally {
        refreshing = false;
      }
    };
    refreshRef.current = () => void refresh();
    void refresh();
    const events = new EventSource(
      `/api/runs/${encodeURIComponent(id)}/events`,
    );
    events.onopen = () => setConnected(true);
    events.onmessage = () => {
      if (alive) setConnected(true);
    };
    events.addEventListener("snapshot", (event) => {
      if (!alive) return;
      try {
        const snapshot = JSON.parse((event as MessageEvent).data) as Run;
        setRun(snapshot);
        if (terminalStatuses.has(snapshot.status)) {
          events.close();
          setConnected(false);
        }
      } catch {
        void refresh();
      }
    });
    events.addEventListener("complete", () => {
      events.close();
      setConnected(false);
      void refresh();
    });
    events.addEventListener("execution", () => void refresh());
    events.addEventListener("update", () => void refresh());
    events.onerror = () => setConnected(false);
    const timer = setInterval(() => void refresh(), 3000);
    return () => {
      alive = false;
      clearInterval(timer);
      events.close();
    };
  }, [id]);
  return { run, error, connected, refresh: () => refreshRef.current() };
}
function RunPage() {
  const { id = "", tab = "investigation" } = useParams();
  const { run, error, connected, refresh } = useRun(id);
  const { scenarios } = useContext(Data);
  if (!run)
    return (
      <>
        <Link to="/control" className="back-link">
          <ArrowLeft size={14} />
          Mission control
        </Link>
        <ErrorMessage message={error} />
        {!error && (
          <div className="loading-inline">
            <LoaderCircle className="spin" size={18} />
            Loading investigation…
          </div>
        )}
      </>
    );
  const scenario = scenarios.find((s) => s.id === run.scenario_id);
  const finished = terminalStatuses.has(run.status);
  return (
    <>
      <Link to="/control" className="back-link">
        <ArrowLeft size={14} />
        Mission control
      </Link>
      <div className="run-heading">
        <div>
          <div className="run-kicker">
            <Label>CONTROLLED INCIDENT / {run.scenario_id}</Label>
            <Status run={run} />
          </div>
          <h1>{scenario?.title || "Incident investigation"}</h1>
          <p>
            <span className="mono">{run.id}</span>
            <span>Started {date(run.created_at)}</span>
          </p>
        </div>
        <div className="run-heading-actions">
          <span
            className={`stream-status ${!finished && connected ? "online" : ""}`}
          >
            <span className="status-dot" />
            {finished
              ? isVerified(run)
                ? "Recorded from verified execution"
                : "Recorded execution"
              : connected
                ? "Live event stream"
                : "Reconnecting · polling active"}
          </span>
          <Button
            className="secondary"
            onClick={refresh}
            aria-label="Refresh investigation"
          >
            <RefreshCw size={14} />
          </Button>
        </div>
      </div>
      <div className="run-info-bar">
        <span>
          <Clock size={14} />
          {formatDuration(run.created_at, run.updated_at)}
        </span>
        <span>
          <Sparkles size={14} />
          {run.model || "Model pending"}
        </span>
        <span>
          <Zap size={14} />
          {run.usage?.requests || 0} model requests
        </span>
        <span>
          <Braces size={14} />
          {formatNumber(run.usage?.tokens || 0)} tokens
        </span>
        <span>
          <LockKeyhole size={14} />
          Allowlisted fixture
        </span>
      </div>
      <ErrorMessage message={run.error || ""} />
      <nav className="tabs" aria-label="Investigation sections">
        {[
          { id: "investigation", label: "Investigation", icon: Activity },
          { id: "repair", label: "Repair studio", icon: Code2 },
          { id: "report", label: "Incident report", icon: FileText },
        ].map(({ id: page, label, icon: Icon }) => (
          <Link
            key={page}
            className={tab === page ? "active" : ""}
            to={`/runs/${run.id}/${page}`}
          >
            <Icon size={15} />
            {label}
            {page === "investigation" && (
              <span>{run.evidence?.length || 0}</span>
            )}
          </Link>
        ))}
      </nav>
      {tab === "repair" ? (
        <Repair run={run} />
      ) : tab === "report" ? (
        <Report run={run} />
      ) : (
        <Investigation run={run} />
      )}
    </>
  );
}
function Investigation({ run }: { run: Run }) {
  const [chosen, setChosen] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const events = run.events || [];
  const evidence = run.evidence || [];
  const currentAgent = events[events.length - 1]?.agent || "";
  const activeIndex = stageOrder.indexOf(run.status);
  const selectedEvidence = evidence.find((e) => e.id === chosen);
  return (
    <>
      <section className="panel orchestration-panel">
        <div className="panel-heading">
          <div>
            <span className="panel-icon">
              <GitBranch size={17} />
            </span>
            <h2>Agent orchestration</h2>
          </div>
          <span className="tiny-label">BOUNDED, EVIDENCE-DRIVEN WORKFLOW</span>
        </div>
        <div className="agent-flow">
          {roles.map((role, i) => {
            const Icon = role.icon;
            const related = events.filter((e) =>
              (e.agent || "").toLowerCase().includes(role.key),
            );
            const isActive =
              !terminalStatuses.has(run.status) &&
              currentAgent.toLowerCase().includes(role.key);
            return (
              <div
                className={`agent-node ${related.length ? "contributed" : ""} ${isActive ? "running" : ""}`}
                key={role.key}
              >
                <span className="agent-node-icon">
                  <Icon size={18} />
                  {related.length > 0 && !isActive && (
                    <i>
                      <Check size={8} />
                    </i>
                  )}
                </span>
                <strong>{role.short}</strong>
                <span>
                  {isActive
                    ? "RUNNING"
                    : related.length
                      ? `${related.length} EVENTS`
                      : "PENDING"}
                </span>
                {i < roles.length - 1 && (
                  <ChevronRight className="agent-arrow" size={16} />
                )}
              </div>
            );
          })}
        </div>
        <div className="progress-line">
          <div
            style={{
              width: `${isVerified(run) ? 100 : Math.max(3, activeIndex * 13)}%`,
            }}
          />
        </div>
        <div className="orchestration-footer">
          <span>
            <span
              className={`status-dot ${!terminalStatuses.has(run.status) ? "pulse" : ""}`}
            />
            {run.status.replaceAll("_", " ")}
          </span>
          <span>Each contribution is persisted with its evidence</span>
        </div>
      </section>
      <div className="investigation-grid">
        <section className="panel timeline-panel">
          <div className="panel-heading">
            <div>
              <span className="panel-icon">
                <Terminal size={17} />
              </span>
              <h2>Execution timeline</h2>
              <span className="count-tag">{events.length}</span>
            </div>
            <select
              aria-label="Filter execution events"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="all">All events</option>
              {[...new Set(events.map((e) => e.agent).filter(Boolean))].map(
                (agent) => (
                  <option key={agent} value={agent}>
                    {agent}
                  </option>
                ),
              )}
            </select>
          </div>
          <div className="timeline">
            {events
              .filter((e) => filter === "all" || e.agent === filter)
              .map((event, i) => (
                <details className="timeline-event" key={event.id || i}>
                  <summary>
                    <span
                      className={`timeline-dot ${event.type?.includes("error") ? "error" : event.type?.includes("verif") ? "success" : ""}`}
                    />
                    <span className="timeline-time">
                      {time(event.created_at)}
                    </span>
                    <span className="timeline-text">
                      <strong>
                        {event.agent?.replaceAll("_", " ") || "System"}
                        <span>{event.type?.replaceAll("_", " ")}</span>
                      </strong>
                      <span>{event.message}</span>
                    </span>
                    <ChevronDown size={13} />
                  </summary>
                  {event.data != null && (
                    <pre className="event-data">{textData(event.data)}</pre>
                  )}
                </details>
              ))}
            {!events.length && (
              <Empty title="Waiting for the first event" icon={Radio}>
                The live execution stream will record each contribution as it
                happens.
              </Empty>
            )}
          </div>
        </section>
        <div className="investigation-right">
          <section className="panel evidence-panel">
            <div className="panel-heading">
              <div>
                <span className="panel-icon">
                  <Layers size={17} />
                </span>
                <h2>Evidence collected</h2>
                <span className="count-tag">{evidence.length}</span>
              </div>
            </div>
            <div className="evidence-list">
              {evidence.map((item) => (
                <button
                  className="evidence-item"
                  key={item.id}
                  onClick={() => setChosen(item.id)}
                >
                  <span className="evidence-kind-icon">
                    {item.kind?.includes("source") ? (
                      <FileCode2 size={16} />
                    ) : item.kind?.includes("test") ? (
                      <FlaskConical size={16} />
                    ) : (
                      <Activity size={16} />
                    )}
                  </span>
                  <span>
                    <strong>{item.title || item.kind}</strong>
                    <small>
                      {item.id} · {item.kind?.replaceAll("_", " ")}
                    </small>
                  </span>
                  <ArrowUpRight size={14} />
                </button>
              ))}
              {!evidence.length && (
                <Empty title="Evidence is on its way" icon={Layers}>
                  Logs, traces, source files, and test output will appear here.
                </Empty>
              )}
            </div>
          </section>
          <section className="panel hypothesis-panel">
            <div className="panel-heading">
              <div>
                <span className="panel-icon">
                  <Search size={17} />
                </span>
                <h2>Root-cause hypotheses</h2>
              </div>
            </div>
            {run.hypotheses?.length ? (
              <div className="hypotheses">
                {run.hypotheses.map((hypothesis, i) => (
                  <div className="hypothesis" key={hypothesis.id || i}>
                    <span className="hypothesis-index">
                      H{String(i + 1).padStart(2, "0")}
                    </span>
                    <div>
                      <strong>
                        {hypothesis.title ||
                          hypothesis.hypothesis ||
                          hypothesis.description ||
                          "Candidate explanation"}
                      </strong>
                      {hypothesis.title &&
                        !!(
                          hypothesis.description || hypothesis.explanation
                        ) && (
                          <p>
                            {String(
                              hypothesis.description || hypothesis.explanation,
                            )}
                          </p>
                        )}
                      <span className="hypothesis-assessment">
                        {hypothesis.assessment ||
                          hypothesis.status ||
                          "Model judgment · not a verified result"}
                      </span>
                      <div className="evidence-chips">
                        {(
                          hypothesis.evidence_ids ||
                          hypothesis.evidence ||
                          hypothesis.supporting_evidence ||
                          []
                        ).map((ref) => (
                          <button key={ref} onClick={() => setChosen(ref)}>
                            {ref}
                            <ArrowUpRight size={10} />
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <Empty title="No diagnosis without evidence" icon={Search}>
                Candidate explanations will appear after the source and
                telemetry are examined.
              </Empty>
            )}
          </section>
        </div>
      </div>
      <TraceWaterfall evidence={evidence} />
      <section className="panel" style={{ marginTop: 24 }}>
        <div className="panel-heading">
          <div>
            <Terminal size={17} />
            <h2>Tool invocation inspector</h2>
          </div>
          <span className="tiny-label">INPUTS · OUTPUTS · EXECUTION IDS</span>
        </div>
        {((run.tool_invocations || []) as Array<Record<string, unknown>>).map(
          (tool, index) => (
            <details className="timeline-event" key={String(tool.id || index)}>
              <summary>
                <span className="timeline-text">
                  <strong>
                    {String(tool.name)}
                    <span>{String(tool.agent)}</span>
                  </strong>
                  <span>
                    {String(tool.status)} ·{" "}
                    {Number(tool.duration_ms || 0).toFixed(1)} ms ·{" "}
                    {String(tool.id)}
                  </span>
                </span>
                <ChevronDown size={13} />
              </summary>
              <pre className="event-data">{textData(tool)}</pre>
            </details>
          ),
        )}
      </section>
      {selectedEvidence && (
        <EvidenceDialog
          item={selectedEvidence}
          onClose={() => setChosen(null)}
        />
      )}
    </>
  );
}
function EvidenceDialog({
  item,
  onClose,
}: {
  item: Evidence;
  onClose: () => void;
}) {
  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", listener);
    return () => document.removeEventListener("keydown", listener);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        className="evidence-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="panel-heading">
          <div>
            <Layers size={18} />
            <h2 id="evidence-title">{item.title || item.kind}</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close evidence"
            onClick={onClose}
            autoFocus
          >
            <X size={18} />
          </button>
        </div>
        <div className="evidence-dialog-meta">
          <span>{item.id}</span>
          <Badge>{item.kind}</Badge>
        </div>
        <pre className="evidence-json">{textData(item.data)}</pre>
        <div className="dialog-footer">
          <CopyButton value={textData(item.data)} />
          <Button className="secondary" onClick={onClose}>
            Close inspector
          </Button>
        </div>
      </section>
    </div>
  );
}
function TraceWaterfall({ evidence }: { evidence: Evidence[] }) {
  const traceEvidence = evidence.filter(
    (e) =>
      e.kind === "telemetry" && !!(e.data as Record<string, unknown>)?.traces,
  );
  const spans = traceEvidence
    .flatMap((e) => {
      const d = e.data as Record<string, unknown> | unknown[];
      if (Array.isArray(d)) return d;
      if (d && typeof d === "object" && Array.isArray(d.spans)) return d.spans;
      if (d && typeof d === "object" && Array.isArray(d.traces))
        return d.traces;
      return d ? [d] : [];
    })
    .filter((s): s is Record<string, unknown> => !!s && typeof s === "object");
  if (!spans.length) return null;
  const max = Math.max(
    1,
    ...spans.map((s) => Number(s.duration_ms || s.latency_ms || 1)),
  );
  return (
    <section className="panel trace-panel">
      <div className="panel-heading">
        <div>
          <span className="panel-icon">
            <Activity size={17} />
          </span>
          <h2>Service trace waterfall</h2>
        </div>
        <span className="tiny-label">OBSERVED REQUEST SPANS</span>
      </div>
      <div className="waterfall">
        {spans.slice(0, 20).map((span, i) => (
          <div className="waterfall-row" key={i}>
            <span>
              {String(
                span.service || span.name || span.operation || `Span ${i + 1}`,
              )}
            </span>
            <div>
              <i
                className={
                  Number(span.status_code || span.status || 0) >= 400 ||
                  span.error
                    ? "error"
                    : ""
                }
                style={{
                  width: `${Math.max(2, (Number(span.duration_ms || span.latency_ms || 1) / max) * 100)}%`,
                }}
              />
            </div>
            <span>
              {Number(span.duration_ms || span.latency_ms || 0).toFixed(2)} ms
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      className="secondary small"
      onClick={() =>
        void navigator.clipboard.writeText(value).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        })
      }
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}
function Repair({ run }: { run: Run }) {
  const [codeView, setCodeView] = useState<"diff" | "split">("diff");
  const verified = isVerified(run);
  return (
    <>
      <div className={`verification-banner ${verified ? "passed" : ""}`}>
        <span className="verification-symbol">
          {verified ? <ShieldCheck size={25} /> : <FlaskConical size={25} />}
        </span>
        <div>
          <strong>
            {verified
              ? "The repair passed recorded verification."
              : run.status === "awaiting_verification"
                ? "Patch ready. Remote verification is unavailable."
                : "Verification has not been established."}
          </strong>
          <p>
            {verified
              ? "The original failure was reproduced, the patched test passed, and the regression suite passed. Review the evidence below."
              : "A generated patch is a proposal. The interface will show VERIFIED only when the required execution results are recorded."}
          </p>
        </div>
        <Badge status={verified ? "verified" : "unverified"}>
          {verified ? "VERIFIED" : "NOT VERIFIED"}
        </Badge>
      </div>
      <div className="repair-grid">
        <aside className="panel repair-files">
          <div className="panel-heading">
            <div>
              <FileCode2 size={16} />
              <h2>Changed files</h2>
            </div>
          </div>
          {run.patch ? (
            <>
              <div className="file-tree">
                <span>
                  <ChevronDown size={13} />
                  <span>incident_lab</span>
                </span>
                <div>
                  <FileCode2 size={14} />
                  <strong>{run.patch.path}</strong>
                  <span>M</span>
                </div>
              </div>
              <div className="patch-scope">
                <ShieldCheck size={15} />
                <strong>Restricted patch scope</strong>
                <p>
                  Only the selected scenario fixture may be changed.
                  Infrastructure and security configuration remain outside the
                  patch boundary.
                </p>
              </div>
            </>
          ) : (
            <Empty icon={FileCode2} title="No patch yet">
              Source changes appear after reproduction.
            </Empty>
          )}
        </aside>
        <section className="panel diff-panel">
          <div className="panel-heading">
            <div>
              <GitBranch size={16} />
              <h2>{run.patch?.path || "Proposed source change"}</h2>
            </div>
            <div className="diff-toolbar">
              <div className="segmented">
                <button
                  className={codeView === "diff" ? "active" : ""}
                  onClick={() => setCodeView("diff")}
                >
                  Unified
                </button>
                <button
                  className={codeView === "split" ? "active" : ""}
                  onClick={() => setCodeView("split")}
                >
                  Split
                </button>
              </div>
              {run.patch && (
                <a
                  className="icon-link"
                  href={`/api/runs/${run.id}/patch`}
                  download={`traceforge-${run.id}.patch`}
                  aria-label="Download patch"
                >
                  <ArrowDownToLine size={15} />
                </a>
              )}
            </div>
          </div>
          {run.patch ? (
            codeView === "diff" ? (
              <div
                className="code-diff"
                role="region"
                aria-label="Unified code diff"
                tabIndex={0}
              >
                {run.patch.diff.split("\n").map((line, i) => (
                  <div
                    key={i}
                    className={`diff-line ${line.startsWith("+") && !line.startsWith("+++") ? "addition" : line.startsWith("-") && !line.startsWith("---") ? "deletion" : line.startsWith("@@") ? "hunk" : ""}`}
                  >
                    <span>{i + 1}</span>
                    <code>{line || " "}</code>
                  </div>
                ))}
              </div>
            ) : (
              <div className="split-diff">
                <div>
                  <div className="code-label">
                    <span className="red-dot" />
                    ORIGINAL SOURCE
                  </div>
                  <pre>{run.patch.before}</pre>
                </div>
                <div>
                  <div className="code-label">
                    <span className="green-dot" />
                    PROPOSED SOURCE
                  </div>
                  <pre>{run.patch.after}</pre>
                </div>
              </div>
            )
          ) : (
            <Empty icon={Code2} title="Waiting for a candidate patch">
              The patch engineer will propose a minimal source change after the
              failing test has been recorded.
            </Empty>
          )}
        </section>
      </div>
      <div className="test-results">
        <TestPanel
          title="Before · reproduction"
          result={
            run.verification?.before ||
            (run.reproduction as TestResult | undefined)
          }
          expectedFailure
        />
        <TestPanel
          title="After · patched test"
          result={run.verification?.after}
        />
        <TestPanel
          title="Regression suite"
          result={run.verification?.regression}
        />
      </div>
      <div className="review-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <ShieldCheck size={17} />
              <h2>Adversarial review</h2>
            </div>
            {run.review && (
              <Badge status={run.review.approved ? "verified" : "unverified"}>
                {run.review.approved ? "Review accepted" : "Changes requested"}
              </Badge>
            )}
          </div>
          {run.review ? (
            <div className="review-body">
              <p>{run.review.summary}</p>
              <Label>REMAINING RISKS</Label>
              {run.review.risks?.length ? (
                <ul>
                  {run.review.risks.map((risk, i) => (
                    <li key={i}>
                      <TriangleAlert size={13} />
                      {risk}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted">
                  No additional risks were recorded by the reviewer. This is a
                  model judgment, not a guarantee.
                </p>
              )}
            </div>
          ) : (
            <Empty icon={ShieldCheck} title="Review pending">
              The reviewer examines the patch alongside its reproduction and
              regression results.
            </Empty>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <GitPullRequest size={17} />
              <h2>Reviewable artifact</h2>
            </div>
            <LockKeyhole size={15} />
          </div>
          <div className="artifact-body">
            <span className="artifact-icon">
              <GitPullRequest size={23} />
            </span>
            <h3>
              {run.approval?.pr_url
                ? "Pull request available"
                : "Human approval is the final gate."}
            </h3>
            <p>
              Generated repairs are never automatically deployed. Inspect and
              download the patch and report before any owner-authorized remote
              action.
            </p>
            <div className="artifact-actions">
              {run.patch && (
                <a
                  className="button secondary"
                  href={`/api/runs/${run.id}/patch`}
                  download
                >
                  <ArrowDownToLine size={14} />
                  Download patch
                </a>
              )}
              {run.approval?.pr_url && (
                <a
                  href={run.approval.pr_url}
                  className="button primary"
                  target="_blank"
                  rel="noreferrer"
                >
                  Open pull request
                  <ExternalLink size={14} />
                </a>
              )}
              <Link className="button ghost" to={`/runs/${run.id}/report`}>
                Read report
                <ArrowRight size={14} />
              </Link>
            </div>
            <span className="artifact-note">
              Public visitors cannot approve external writes.
            </span>
            {run.verification?.job_url && (
              <a
                className="text-link"
                href={run.verification.job_url}
                target="_blank"
                rel="noreferrer"
              >
                Inspect verification job
                <ExternalLink size={13} />
              </a>
            )}
          </div>
        </section>
      </div>
    </>
  );
}
function TestPanel({
  title,
  result,
  expectedFailure = false,
}: {
  title: string;
  result?: TestResult;
  expectedFailure?: boolean;
}) {
  const success = result
    ? expectedFailure
      ? result.exit_code !== 0
      : result.exit_code === 0
    : false;
  return (
    <section className="panel test-panel">
      <div className="panel-heading">
        <div>
          <Terminal size={15} />
          <h2>{title}</h2>
        </div>
        {result ? (
          <span className={`test-exit ${success ? "expected" : "bad"}`}>
            {success ? <CheckCircle2 size={13} /> : <XCircle size={13} />}exit{" "}
            {result.exit_code}
          </span>
        ) : (
          <span className="tiny-label">PENDING</span>
        )}
      </div>
      {result ? (
        <>
          <div className="test-command">
            $ {result.command || "Recorded test execution"}
          </div>
          <pre className="test-output">
            {result.output || "No stdout was recorded."}
          </pre>
          <div className="test-footer">
            <span>
              {expectedFailure
                ? "Expected: reproduces failure"
                : "Expected: all checks pass"}
            </span>
            <span>
              {result.duration_ms != null
                ? `${Math.round(result.duration_ms)} ms`
                : "Duration not recorded"}
            </span>
          </div>
        </>
      ) : (
        <div className="test-pending">
          <Clock size={19} />
          <p>No execution result recorded.</p>
        </div>
      )}
    </section>
  );
}
function Report({ run }: { run: Run }) {
  const [report, setReport] = useState(run.report || "");
  useEffect(() => {
    if (run.report) setReport(run.report);
    else if (terminalStatuses.has(run.status))
      fetch(`/api/runs/${run.id}/report`)
        .then((r) => (r.ok ? r.text() : ""))
        .then(setReport)
        .catch(() => {});
  }, [run.report, run.id, run.status]);
  return (
    <section className="panel report-panel">
      <div className="panel-heading">
        <div>
          <FileText size={17} />
          <h2>Technical incident report</h2>
        </div>
        {report && (
          <div className="report-actions">
            <CopyButton value={report} />
            <a
              className="button secondary small"
              href={`/api/runs/${run.id}/report`}
              download={`traceforge-${run.id}.md`}
            >
              <ArrowDownToLine size={14} />
              Download
            </a>
          </div>
        )}
      </div>
      {report ? (
        <>
          <div className="report-metadata">
            <span>
              RUN <strong>{run.id.slice(0, 12)}</strong>
            </span>
            <span>
              RECORDED <strong>{date(run.updated_at)}</strong>
            </span>
            <Status run={run} />
          </div>
          <article className="markdown-report">
            {report.split("\n").map((line, i) =>
              line.startsWith("### ") ? (
                <h3 key={i}>{line.slice(4)}</h3>
              ) : line.startsWith("## ") ? (
                <h2 key={i}>{line.slice(3)}</h2>
              ) : line.startsWith("# ") ? (
                <h1 key={i}>{line.slice(2)}</h1>
              ) : line.startsWith("- ") ? (
                <p className="markdown-list" key={i}>
                  • {line.slice(2)}
                </p>
              ) : line.startsWith("```") ? (
                <hr key={i} />
              ) : line.trim() ? (
                <p key={i}>{line}</p>
              ) : (
                <div className="markdown-spacer" key={i} />
              ),
            )}
          </article>
        </>
      ) : (
        <Empty icon={FileText} title="The report follows the evidence">
          The incident reporter will assemble the diagnosis, repair,
          verification results, and residual risks when the investigation
          concludes.
        </Empty>
      )}
    </section>
  );
}

function Intelligence() {
  const { runs, scenarios } = useContext(Data);
  const [search, setSearch] = useState(""),
    [status, setStatus] = useState("all");
  const filtered = runs.filter(
    (run) =>
      (status === "all" ||
        (status === "verified" ? isVerified(run) : run.status === status)) &&
      `${run.id} ${run.scenario_id} ${run.report || ""} ${scenarios.find((s) => s.id === run.scenario_id)?.title || ""}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const groups = useMemo(
    () =>
      scenarios
        .map((s) => ({
          scenario: s,
          runs: runs.filter((r) => r.scenario_id === s.id),
        }))
        .filter((g) => g.runs.length),
    [runs, scenarios],
  );
  return (
    <>
      <PageHeading
        label="KNOWLEDGE / EXECUTION HISTORY"
        title="Incident intelligence"
        description="Past investigations. Searchable evidence. No rerun required."
      />
      <div className="history-summary">
        <div>
          <strong>{runs.length}</strong>
          <span>recorded investigations</span>
        </div>
        <div>
          <strong>{runs.filter(isVerified).length}</strong>
          <span>verified resolutions</span>
        </div>
        <div>
          <strong>{groups.length}</strong>
          <span>scenario families observed</span>
        </div>
        <div className="history-note">
          <Database size={20} />
          <span>
            Historical evidence informs the next investigation.
            <br />
            It never substitutes for a fresh verification.
          </span>
        </div>
      </div>
      <section className="panel">
        <div className="history-toolbar">
          <div className="search-field">
            <Search size={16} />
            <input
              aria-label="Search incident history"
              placeholder="Search incidents, run IDs, or reports…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {search && (
              <button
                className="icon-button"
                aria-label="Clear search"
                onClick={() => setSearch("")}
              >
                <X size={14} />
              </button>
            )}
          </div>
          <select
            aria-label="Filter by incident status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="all">All statuses</option>
            <option value="verified">Verified</option>
            <option value="failed">Failed</option>
            <option value="unverified">Unverified</option>
            <option value="interrupted">Interrupted</option>
            <option value="awaiting_verification">Awaiting verification</option>
          </select>
        </div>
        {filtered.length ? (
          <RunTable runs={filtered} scenarios={scenarios} />
        ) : (
          <Empty
            icon={Search}
            title={
              runs.length
                ? "No matching investigations"
                : "Your evidence library starts here"
            }
          >
            {runs.length
              ? "Try another search term or remove the status filter."
              : "Launch an incident to build a searchable history of real executions."}
          </Empty>
        )}
      </section>
      {groups.length > 0 && (
        <>
          <div className="section-heading">
            <h2>Recurring scenario families</h2>
            <span>Grouped by the controlled incident fixture</span>
          </div>
          <div className="scenario-family-grid">
            {groups.map(({ scenario, runs: family }) => (
              <article className="panel family-card" key={scenario.id}>
                <span className="family-icon">
                  <GitBranch size={19} />
                </span>
                <span className="tiny-label">{scenario.service}</span>
                <h3>{scenario.title}</h3>
                <p>{scenario.description}</p>
                <div>
                  <span>{family.length} runs</span>
                  <span>{family.filter(isVerified).length} verified</span>
                </div>
                <Link to={`/runs/${family[0].id}`}>
                  Inspect latest execution
                  <ArrowUpRight size={14} />
                </Link>
              </article>
            ))}
          </div>
        </>
      )}
    </>
  );
}
function Evaluations() {
  const [data, setData] = useState<Evaluation | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  async function load() {
    setLoading(true);
    try {
      setData(await api<Evaluation>("/api/evaluations"));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  const cases = data?.cases || [];
  return (
    <>
      <PageHeading
        label="QUALITY / EXECUTED EVIDENCE"
        title="Evaluation arena"
        description="Measure the behavior. Inspect the failures. Earn the verdict."
        action={
          <Button className="secondary" onClick={() => void load()}>
            <RefreshCw size={14} />
            Refresh results
          </Button>
        }
      />
      <ErrorMessage message={error} />
      <div className="evaluation-notice">
        <FlaskConical size={21} />
        <div>
          <strong>Execution results, with their limits.</strong>
          <p>
            Agent performance and deterministic safety tests are different
            measurements. Scores are shown only when an executed result exists.
          </p>
        </div>
      </div>
      {data && Object.keys(data.summary || {}).length > 0 && (
        <div className="evaluation-metrics">
          {Object.entries(data.summary)
            .filter(
              ([, v]) =>
                typeof v === "number" ||
                typeof v === "string" ||
                typeof v === "boolean",
            )
            .map(([key, value]) => (
              <div className="stat-card" key={key}>
                <div>{key.replaceAll("_", " ")}</div>
                <strong>
                  {typeof value === "number"
                    ? formatNumber(value)
                    : String(value)}
                </strong>
                <small>From recorded evaluation results</small>
              </div>
            ))}
        </div>
      )}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="panel-icon">
              <FlaskConical size={17} />
            </span>
            <h2>Evaluation cases</h2>
            <span className="count-tag">{cases.length}</span>
          </div>
          <span className="tiny-label">NO SYNTHETIC SUCCESS METRICS</span>
        </div>
        {loading ? (
          <div className="loading-inline">
            <LoaderCircle size={18} className="spin" />
            Loading evaluation records…
          </div>
        ) : cases.length ? (
          <div className="evaluation-cases">
            {cases.map((item, i) => (
              <details className="evaluation-case" key={item.id || i}>
                <summary>
                  <span className="case-number">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="case-title">
                    <strong>
                      {item.name || item.title || item.id || `Case ${i + 1}`}
                    </strong>
                    <span>
                      {item.description ||
                        "Inspect the recorded result and evaluation context."}
                    </span>
                  </span>
                  <Badge
                    status={
                      item.passed === true
                        ? "verified"
                        : item.passed === false
                          ? "failed"
                          : item.status || "pending"
                    }
                  >
                    {item.passed === true
                      ? "Passed"
                      : item.passed === false
                        ? "Failed"
                        : item.status || "Not executed"}
                  </Badge>
                  <ChevronDown size={14} />
                </summary>
                <pre className="event-data">
                  {textData(item.result ?? item)}
                </pre>
              </details>
            ))}
          </div>
        ) : (
          <Empty icon={FlaskConical} title="No evaluation results recorded">
            Executed evaluation results will appear here. Empty coverage is
            never reported as a passing score.
          </Empty>
        )}
      </section>
      <div className="evaluation-principles">
        <div>
          <ShieldCheck size={20} />
          <h3>False verification is a failure.</h3>
          <p>
            An incorrect patch must never receive a verified verdict.
            Verification gates are tested separately from model judgments.
          </p>
        </div>
        <div>
          <LockKeyhole size={20} />
          <h3>Untrusted input stays untrusted.</h3>
          <p>
            Log content and model output cannot grant new tool permissions,
            choose arbitrary commands, or expand patch scope.
          </p>
        </div>
        <div>
          <RefreshCw size={20} />
          <h3>Recovery preserves the record.</h3>
          <p>
            Interrupted work retains its evidence. Completed external actions
            must not be replayed without an idempotency check.
          </p>
        </div>
      </div>
    </>
  );
}
const architectureNodes = [
  {
    id: "interface",
    label: "Product interface",
    sub: "React · TypeScript · SSE",
    icon: LayoutDashboard,
    description:
      "One same-origin interface serves the scenario launcher, live evidence stream, source diff, verification output, and incident history. Provider credentials never enter the browser.",
    facts: [
      "Anonymous visitors can inspect recorded runs.",
      "Live launches use curated scenario IDs.",
      "Owner-only actions require authentication.",
    ],
  },
  {
    id: "control",
    label: "Control plane",
    sub: "FastAPI · typed contracts",
    icon: Boxes,
    description:
      "The backend owns run admission, API validation, quota enforcement, execution state, and event delivery. The incident fixture environment is distinct from the control plane.",
    facts: [
      "Input schemas reject arbitrary commands and repositories.",
      "Per-session and global limits bound live inference.",
      "Failures are recorded without inventing a successful result.",
    ],
  },
  {
    id: "agents",
    label: "Investigation graph",
    sub: "LangGraph · seven responsibilities",
    icon: GitBranch,
    description:
      "A bounded state graph coordinates telemetry collection, hypothesis formation, reproduction, constrained patch generation, review, and reporting. Contributions are persisted with evidence references.",
    facts: [
      "Model outputs are proposals, never permission grants.",
      "Failure evidence can drive a bounded patch retry.",
      "Tool records expose inputs, outputs, and timing.",
    ],
  },
  {
    id: "model",
    label: "Model inference",
    sub: "Groq · server-side credentials",
    icon: Sparkles,
    description:
      "Selected evidence and source snippets are passed to configured Groq models. Structured responses and tool calling are separated where provider support requires it.",
    facts: [
      "Only the backend reads GROQ_API_KEY.",
      "Request and token budgets cap each investigation.",
      "Rate limits remain visible; no fabricated fallback runs.",
    ],
  },
  {
    id: "lab",
    label: "Controlled incident lab",
    sub: "Gateway → orders → dependencies",
    icon: FlaskConical,
    description:
      "Executable seeded defects produce real failures in orders, payments, and inventory behavior. The hosted lab uses service boundaries inside a resource-conscious process, not separately deployed microservices.",
    facts: [
      "Each scenario has healthy and faulty fixture code.",
      "Traffic produces actual request and error records.",
      "Every launch uses a clean controlled fixture.",
    ],
  },
  {
    id: "verification",
    label: "Verification boundary",
    sub: "Allowlisted patches · trusted tests",
    icon: ShieldCheck,
    description:
      "A proposed change is validated against a narrow source allowlist and tested against the original reproduction and regression suite. Local and remote results are explicitly labeled.",
    facts: [
      "Generated code cannot modify secrets or CI definitions.",
      "A missing remote runner is shown as unavailable.",
      "A successful verification never deploys the patch automatically.",
    ],
  },
  {
    id: "state",
    label: "Durable evidence",
    sub: "Runs · events · tests · reports",
    icon: Database,
    description:
      "Run state, tool outputs, code changes, test results, and reports stay attached to a unique execution ID. Prior incidents aid investigation but do not prove that a new repair works.",
    facts: [
      "Unique run IDs connect every artifact.",
      "Incomplete runs are recovered or marked interrupted.",
      "Searchable history avoids unnecessary repeated inference.",
    ],
  },
];
function Architecture() {
  const [selected, setSelected] = useState("agents");
  const { config } = useContext(Data);
  const node = architectureNodes.find((n) => n.id === selected)!;
  const Icon = node.icon;
  return (
    <>
      <PageHeading
        label="SYSTEM / DESIGN & BOUNDARIES"
        title="Built to show its work."
        description="A small, inspectable system with a strict boundary between proposals and proof."
      />
      <div className="architecture-layout">
        <section className="panel architecture-map">
          <div className="panel-heading">
            <div>
              <Network size={17} />
              <h2>System topology</h2>
            </div>
            <span className="tiny-label">SELECT A COMPONENT</span>
          </div>
          <div className="architecture-canvas">
            <div className="arch-row">
              <ArchNode
                node={architectureNodes[0]}
                selected={selected}
                onSelect={setSelected}
              />
            </div>
            <div className="arch-connector">
              <ArrowDown size={16} />
              <span>HTTPS / streamed events</span>
            </div>
            <div className="arch-row">
              <ArchNode
                node={architectureNodes[1]}
                selected={selected}
                onSelect={setSelected}
              />
            </div>
            <div className="arch-connector">
              <ArrowDown size={16} />
              <span>Validated execution state</span>
            </div>
            <div className="arch-row">
              <ArchNode
                node={architectureNodes[2]}
                selected={selected}
                onSelect={setSelected}
              />
              <span className="arch-horizontal">↔</span>
              <ArchNode
                node={architectureNodes[3]}
                selected={selected}
                onSelect={setSelected}
              />
            </div>
            <div className="arch-branch">
              <span />
              <ArrowDown size={16} />
              <span />
            </div>
            <div className="arch-row bottom">
              {architectureNodes.slice(4).map((n) => (
                <ArchNode
                  key={n.id}
                  node={n}
                  selected={selected}
                  onSelect={setSelected}
                />
              ))}
            </div>
          </div>
          <div className="architecture-map-footer">
            <span className="status-dot" />
            Same-origin application · Resource-conscious hosted runtime
          </div>
        </section>
        <aside className="panel architecture-detail">
          <span className="architecture-detail-icon">
            <Icon size={28} />
          </span>
          <Label>COMPONENT DETAIL</Label>
          <h2>{node.label}</h2>
          <span className="architecture-sub">{node.sub}</span>
          <p>{node.description}</p>
          <div className="architecture-facts">
            {node.facts.map((fact) => (
              <div key={fact}>
                <Check size={15} />
                <span>{fact}</span>
              </div>
            ))}
          </div>
        </aside>
      </div>
      <div className="section-heading">
        <h2>Engineering boundaries</h2>
        <span>Deliberate constraints, explicit tradeoffs</span>
      </div>
      <div className="boundary-grid">
        {[
          {
            icon: LockKeyhole,
            title: "Credentials stay on the server",
            body: "The frontend receives configuration status and execution artifacts. Provider keys and database credentials are loaded only by the backend.",
          },
          {
            icon: Code2,
            title: "The model cannot run a shell",
            body: "Fixed tools expose narrowly scoped operations. Source proposals are untrusted data and are validated before entering the verification boundary.",
          },
          {
            icon: GitPullRequest,
            title: "The owner controls external writes",
            body: "Reviewable patches are downloadable. Remote pull-request creation requires owner approval, and generated repairs are never deployed automatically.",
          },
          {
            icon: Globe,
            title: "Free hosting has real constraints",
            body: "A free web service can sleep or restart. Live work may be interrupted, and execution history requires durable external storage to survive restarts.",
          },
        ].map(({ icon: ItemIcon, title, body }) => (
          <article className="panel boundary-card" key={title}>
            <ItemIcon size={21} />
            <h3>{title}</h3>
            <p>{body}</p>
          </article>
        ))}
      </div>
      <section className="panel deployment-facts">
        <div className="panel-heading">
          <div>
            <Database size={17} />
            <h2>Current runtime configuration</h2>
          </div>
        </div>
        <dl>
          <div>
            <dt>Inference</dt>
            <dd>
              {config?.groq_configured ? "Groq configured" : "Not configured"}
            </dd>
          </div>
          <div>
            <dt>Verification mode</dt>
            <dd>
              {config?.verification_mode?.replaceAll("_", " ") || "Unavailable"}
            </dd>
          </div>
          <div>
            <dt>Storage</dt>
            <dd>{config?.storage || "Unavailable"}</dd>
          </div>
          <div>
            <dt>Configured models</dt>
            <dd>{config?.models?.join(", ") || "Unavailable"}</dd>
          </div>
          {Object.entries(config?.limits || {}).map(([key, value]) => (
            <div key={key}>
              <dt>{key.replaceAll("_", " ")}</dt>
              <dd>{String(value)}</dd>
            </div>
          ))}
        </dl>
        {config?.github_url && (
          <a
            href={config.github_url}
            target="_blank"
            rel="noreferrer"
            className="text-link"
          >
            Inspect the source repository
            <ExternalLink size={14} />
          </a>
        )}
      </section>
    </>
  );
}
function ArchNode({
  node,
  selected,
  onSelect,
}: {
  node: (typeof architectureNodes)[number];
  selected: string;
  onSelect: (id: string) => void;
}) {
  const Icon = node.icon;
  return (
    <button
      className={`arch-node ${selected === node.id ? "selected" : ""}`}
      onClick={() => onSelect(node.id)}
      aria-pressed={selected === node.id}
    >
      <Icon size={20} />
      <strong>{node.label}</strong>
      <span>{node.sub}</span>
    </button>
  );
}
function NotFound() {
  return (
    <Empty
      icon={Search}
      title="This route is not part of the investigation."
      action={
        <Link className="button primary" to="/control">
          Return to mission control
          <ArrowRight size={15} />
        </Link>
      }
    >
      The page may have moved. Your recorded runs are available in incident
      intelligence.
    </Empty>
  );
}
