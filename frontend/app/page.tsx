"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api";

type Doc = { document_id: string; filename: string; pages: number; chunks: number };
type Citation = { marker: string; filename: string; page: number; excerpt: string; document_id: string };
type Msg = {
  role: "me" | "ai";
  text: string;
  citations?: Citation[];
  insufficient?: boolean;
  steps?: string[];
  warnings?: string[];
};
type Ctx = { map: Record<string, number>; pick: (n: number) => void };

const SUGGESTIONS = [
  "What are the main points of my documents?",
  "What risks or limitations are mentioned?",
  "Compare the key ideas across my documents",
];
const PHASES = ["Planning sub-questions", "Retrieving passages", "Analysing sources", "Fact-checking claims", "Writing the report"];

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return typeof body.detail === "string" ? body.detail : "Request failed.";
  } catch {
    return "Request failed.";
  }
}

/* ---------- citations: [S3] markers become 1, 2, 3 in order of appearance ---------- */
function buildSources(text: string, citations: Citation[]) {
  const byMarker = new Map(citations.map((c) => [c.marker, c]));
  const order: string[] = [];
  for (const m of text.matchAll(/\[(S\d+)\]/g)) if (byMarker.has(m[1]) && !order.includes(m[1])) order.push(m[1]);
  citations.forEach((c) => { if (!order.includes(c.marker)) order.push(c.marker); });
  const map: Record<string, number> = {};
  order.forEach((mk, i) => (map[mk] = i + 1));
  return { map, sources: order.map((mk) => byMarker.get(mk)!) };
}

/* ---------- tiny markdown renderer (bold, code, headings, lists) ---------- */
function inline(text: string, ctx: Ctx): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[S\d+\])/g).filter(Boolean);
  const out: ReactNode[] = [];
  let last = "";
  parts.forEach((p, i) => {
    const mk = p.match(/^\[(S\d+)\]$/);
    if (mk) {
      const n = ctx.map[mk[1]];
      if (!n || last === `c${n}`) return; // hide unknown or repeated-in-a-row badges
      last = `c${n}`;
      out.push(<button key={i} className="cite" onClick={() => ctx.pick(n)} aria-label={`Source ${n}`}>{n}</button>);
      return;
    }
    if (p.trim()) last = "t";
    if (p.startsWith("**") && p.endsWith("**") && p.length > 4) out.push(<strong key={i}>{p.slice(2, -2)}</strong>);
    else if (p.startsWith("`") && p.endsWith("`") && p.length > 2) out.push(<code key={i}>{p.slice(1, -1)}</code>);
    else out.push(p);
  });
  return out;
}

function Markdown({ text, ctx }: { text: string; ctx: Ctx }) {
  const out: ReactNode[] = [];
  let para: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  const flushPara = () => {
    if (para.length) out.push(<p key={out.length}>{inline(para.join(" "), ctx)}</p>);
    para = [];
  };
  const flushList = () => {
    if (list) {
      const Tag = list.ordered ? "ol" : "ul";
      out.push(<Tag key={out.length}>{list.items.map((it, i) => <li key={i}>{inline(it, ctx)}</li>)}</Tag>);
    }
    list = null;
  };
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) { flushPara(); flushList(); continue; }
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      flushPara(); flushList();
      const Tag = (`h${Math.min(h[1].length + 1, 4)}`) as "h2" | "h3" | "h4";
      out.push(<Tag key={out.length}>{inline(h[2], ctx)}</Tag>);
      continue;
    }
    const b = line.match(/^\s*[*-]\s+(.*)$/);
    const n = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (b || n) {
      flushPara();
      const ordered = !!n;
      if (list && list.ordered !== ordered) flushList();
      if (!list) list = { ordered, items: [] };
      list.items.push((b || n)![1]);
      continue;
    }
    flushList();
    para.push(line.trim());
  }
  flushPara(); flushList();
  return <>{out}</>;
}

/* ---------- icons ---------- */
const Icon = ({ d, size = 18 }: { d: string; size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
);
const I = {
  file: "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h4",
  trash: "M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3",
  upload: "M12 16V4M7 9l5-5 5 5M5 20h14",
  send: "M5 12h14M13 6l6 6-6 6",
  alert: "M12 9v4M12 17h.01M10.3 3.9 2.4 17.6A2 2 0 0 0 4.1 20.6h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
  spark: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z",
};

export default function Home() {
  const [workspace, setWorkspace] = useState("");
  const [docs, setDocs] = useState<Doc[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [question, setQuestion] = useState("");
  const [log, setLog] = useState<Msg[]>([]);
  const [status, setStatus] = useState("");
  const [isError, setIsError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deep, setDeep] = useState(false);
  const [mode, setMode] = useState("hybrid");
  const [phase, setPhase] = useState(0);
  const [active, setActive] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const streamRef = useRef<HTMLDivElement>(null);

  const note = (text: string, error = false) => { setStatus(text); setIsError(error); };

  const loadDocs = useCallback(async () => {
    if (!workspace) return;
    try {
      const res = await fetch(`${API}/documents?workspace_id=${encodeURIComponent(workspace)}`);
      if (res.ok) setDocs(await res.json());
    } catch {
      note("Cannot reach the API. Is the backend running on port 8000?", true);
    }
  }, [workspace]);

  useEffect(() => {
    // Each browser gets its own private workspace id, kept in localStorage.
    const rand = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID().replace(/-/g, "") : Math.random().toString(36).slice(2) + Date.now().toString(36));
    try {
      let id = localStorage.getItem("nexus_ws");
      if (!id) { id = "u" + rand(); localStorage.setItem("nexus_ws", id); }
      setWorkspace(id);
    } catch {
      setWorkspace("u" + rand());
    }
  }, []);
  useEffect(() => { loadDocs(); }, [loadDocs]);
  useEffect(() => { streamRef.current?.scrollTo({ top: streamRef.current.scrollHeight, behavior: "smooth" }); }, [log, busy]);
  useEffect(() => {
    if (!(busy && deep)) { setPhase(0); return; }
    const t = setInterval(() => setPhase((p) => Math.min(p + 1, PHASES.length - 1)), 6000);
    return () => clearInterval(t);
  }, [busy, deep]);

  async function upload() {
    if (!file) return note("Choose a PDF first.", true);
    setUploading(true);
    note("Indexing your PDF. The first upload can take a minute.");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API}/documents/upload?workspace_id=${encodeURIComponent(workspace)}`, { method: "POST", body: form });
      if (!res.ok) return note(await readError(res), true);
      const data: Doc = await res.json();
      note(`Indexed ${data.chunks} chunks from ${data.filename}.`);
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      loadDocs();
    } catch {
      note("Upload failed. Check that the backend is running.", true);
    } finally { setUploading(false); }
  }

  async function remove(id: string) {
    const res = await fetch(`${API}/documents/${id}`, { method: "DELETE" });
    if (!res.ok) return note(await readError(res), true);
    note("Document deleted.");
    loadDocs();
  }

  async function ask(text?: string) {
    const q = (text ?? question).trim();
    if (q.length < 3 || busy || !workspace) return;
    setLog((l) => [...l, { role: "me", text: q }]);
    setQuestion(""); setBusy(true); note("");
    try {
      const res = await fetch(`${API}/${deep ? "research" : "ask"}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(deep ? { question: q, workspace_id: workspace } : { question: q, workspace_id: workspace, top_k: 5, mode }),
      });
      if (!res.ok) return note(await readError(res), true);
      const data = await res.json();
      setLog((l) => [...l, deep
        ? { role: "ai", text: data.report, citations: data.citations, steps: data.trace, warnings: data.warnings, insufficient: !data.verified && data.citations.length === 0 }
        : { role: "ai", text: data.answer, citations: data.citations, insufficient: data.insufficient_evidence }]);
      setActive(null);
    } catch {
      note("Request failed. Check that the backend is running.", true);
    } finally { setBusy(false); }
  }

  function pick(i: number, n: number) {
    setActive(`${i}-${n}`);
    document.getElementById(`src-${i}-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderAi(m: Msg, i: number) {
    const body = m.text.replace(/\n##\s*Sources[\s\S]*$/, "").trim();
    const { map, sources } = buildSources(body, m.citations || []);
    const ctx: Ctx = { map, pick: (n) => pick(i, n) };
    return (
      <div className={`ai-body ${m.insufficient ? "warn" : ""}`}>
        {m.insufficient && <div className="warn-tag"><Icon d={I.alert} size={16} /> Not enough evidence</div>}
        <div className="prose"><Markdown text={body} ctx={ctx} /></div>
        {m.warnings && m.warnings.length > 0 && !m.insufficient && (
          <div className="note-box"><b>Could not fully verify:</b> {m.warnings.join(" · ")}</div>
        )}
        {sources.length > 0 && (
          <div className="sources">
            <div className="sources-title">Sources</div>
            {sources.map((s, k) => (
              <div key={s.marker} id={`src-${i}-${k + 1}`} className={`source ${active === `${i}-${k + 1}` ? "on" : ""}`}>
                <span className="num">{k + 1}</span>
                <div className="s-main">
                  <div className="s-head"><span className="s-file">{s.filename}</span><span className="pg">Page {s.page}</span></div>
                  <p>{s.excerpt}…</p>
                </div>
              </div>
            ))}
          </div>
        )}
        {m.steps && m.steps.length > 0 && (
          <details className="steps"><summary>How this was researched</summary><ol>{m.steps.map((s, k) => <li key={k}>{s}</li>)}</ol></details>
        )}
      </div>
    );
  }

  const totalChunks = docs.reduce((a, d) => a + d.chunks, 0);

  return (
    <div className="shell">
      <aside className="panel side">
        <div className="brand">
          <div className="logo" aria-hidden="true"><Icon d={I.spark} size={20} /></div>
          <div><div className="brand-name">NEXUS AI</div><div className="brand-sub">Research intelligence</div></div>
        </div>

        <section>
          <div className="label">Workspace</div>
          <div className="ws-tag"><span className="dot" />Private to this browser<span className="ws-id">{workspace.slice(1, 7)}</span></div>
        </section>

        <section>
          <div className="label">Add a source</div>
          <div
            className={`drop ${dragging ? "drag" : ""}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files?.[0]; if (f) setFile(f); }}
            role="button" tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter") fileRef.current?.click(); }}
          >
            <Icon d={I.upload} size={22} />
            <div className="drop-main">{file ? file.name : "Drop a PDF here or click to browse"}</div>
            <div className="drop-sub">Text-based PDFs only</div>
          </div>
          <input ref={fileRef} type="file" accept="application/pdf" hidden onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button className="btn-primary full" disabled={uploading || !file} onClick={upload}>{uploading ? "Indexing…" : "Upload and index"}</button>
        </section>

        <section className="grow">
          <div className="label">Library <span className="count">{docs.length} · {totalChunks} chunks</span></div>
          <div className="docs">
            {docs.length === 0 && <div className="empty-docs">No documents yet.</div>}
            {docs.map((d) => (
              <div className="doc" key={d.document_id}>
                <div className="doc-icon"><Icon d={I.file} /></div>
                <div className="doc-info">
                  <div className="doc-name" title={d.filename}>{d.filename}</div>
                  <div className="doc-meta">{d.pages} pages · {d.chunks} chunks</div>
                </div>
                <button className="icon-btn" onClick={() => remove(d.document_id)} aria-label={`Delete ${d.filename}`} title="Delete"><Icon d={I.trash} size={16} /></button>
              </div>
            ))}
          </div>
        </section>
        <p className="privacy">Demo: files are stored temporarily and may be cleared at any time. Please don&apos;t upload confidential documents. Answers are generated with Google Gemini.</p>
      </aside>

      <main className="panel main">
        <header className="topbar">
          <div><h1>Research chat</h1><div className="top-sub">Answers come only from your documents.</div></div>
          {log.length > 0 && <button className="btn-ghost" onClick={() => setLog([])}>Clear chat</button>}
        </header>

        <div className="stream" ref={streamRef}>
          {log.length === 0 && (
            <div className="hero">
              <div className="hero-logo"><Icon d={I.spark} size={28} /></div>
              <h2>Ask your documents</h2>
              <p>{docs.length === 0 ? "Add a PDF on the left to get started." : "Every answer is linked back to the exact page it came from."}</p>
              {docs.length > 0 && <div className="suggest">{SUGGESTIONS.map((s) => <button key={s} onClick={() => ask(s)}>{s}</button>)}</div>}
            </div>
          )}
          {log.map((m, i) => m.role === "me"
            ? <div className="msg-me" key={i}>{m.text}</div>
            : <div className="msg-ai" key={i}><div className="avatar"><Icon d={I.spark} size={16} /></div>{renderAi(m, i)}</div>)}
          {busy && (
            <div className="msg-ai"><div className="avatar"><Icon d={I.spark} size={16} /></div>
              <div className="thinking">{deep ? PHASES[phase] : "Searching your documents"}<span className="dots"><i /><i /><i /></span></div>
            </div>
          )}
        </div>

        <div className="composer">
          <div className="options">
            <button type="button" role="switch" aria-checked={deep} className={`switch ${deep ? "on" : ""}`} onClick={() => setDeep(!deep)}>
              <span className="knob" /><span className="switch-label">Deep research</span>
            </button>
            <div className={`seg ${deep ? "disabled" : ""}`} role="group" aria-label="Retrieval mode">
              {[["semantic", "Semantic"], ["hybrid", "Hybrid"], ["hybrid_rerank", "Rerank"]].map(([v, l]) => (
                <button key={v} type="button" disabled={deep} aria-pressed={mode === v} className={mode === v ? "on" : ""} onClick={() => setMode(v)}>{l}</button>
              ))}
            </div>
          </div>
          <div className="input-row">
            <textarea rows={2} value={question} aria-label="Question" placeholder="Ask a specific question about your documents…"
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); } }} />
            <button className="send" disabled={busy || question.trim().length < 3} onClick={() => ask()} aria-label="Send"><Icon d={I.send} size={20} /></button>
          </div>
        </div>
      </main>

      {status && (
        <div className={`toast ${isError ? "err" : ""}`} role="status">
          <span>{status}</span><button onClick={() => setStatus("")} aria-label="Dismiss">×</button>
        </div>
      )}
    </div>
  );
}
