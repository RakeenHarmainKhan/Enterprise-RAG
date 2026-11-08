import { BeakerIcon } from "@heroicons/react/24/outline";
import { useEffect, useMemo, useState } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { listEvalResults, runEvaluation } from "../services/api";
import { useStore } from "../store";

export function EvaluationPanel() {
  const [question, setQuestion] = useState("What does the document say about pricing?");
  const [answer, setAnswer] = useState("The document does not specify pricing details.");
  const [contexts, setContexts] = useState("Excerpt one\n---\nExcerpt two");
  const [busy, setBusy] = useState(false);
  const evaluation = useStore((s) => s.evaluation);
  const setEvalResults = useStore((s) => s.setEvalResults);
  const setLastEval = useStore((s) => s.setLastEval);

  useEffect(() => {
    void (async () => {
      try {
        const rows = await listEvalResults(50);
        setEvalResults(rows);
      } catch {
        setEvalResults([]);
      }
    })();
  }, [setEvalResults]);

  const radarData = useMemo(() => {
    const src = evaluation.lastRun as Record<string, unknown> | null;
    if (!src) return [];
    const keys = ["faithfulness", "answer_relevance", "context_precision", "context_recall"];
    return keys
      .filter((k) => typeof src[k] === "number")
      .map((k) => ({ metric: k.replace("_", " "), score: Number(src[k]) }));
  }, [evaluation.lastRun]);

  async function onRun() {
    setBusy(true);
    try {
      const ctx = contexts
        .split(/\n---\n/)
        .map((c) => c.trim())
        .filter(Boolean);
      const row = await runEvaluation({ question, answer, contexts: ctx });
      setLastEval(row);
      const history = await listEvalResults(50);
      setEvalResults(history);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
          <BeakerIcon className="h-5 w-5 text-accent" />
          Run RAGAS-style metrics
        </div>
        <label className="block text-xs font-medium text-slate-600">
          Question
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm"
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
        </label>
        <label className="block text-xs font-medium text-slate-600">
          Answer
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm"
            rows={3}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
        </label>
        <label className="block text-xs font-medium text-slate-600">
          Contexts (separate with a line containing only <code>---</code>)
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-200 p-2 text-sm"
            rows={4}
            value={contexts}
            onChange={(e) => setContexts(e.target.value)}
          />
        </label>
        <button
          type="button"
          disabled={busy}
          onClick={() => void onRun()}
          className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {busy ? "Running…" : "Run evaluation"}
        </button>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-2 text-sm font-semibold text-slate-800">Radar (last run)</div>
        <div className="h-72 w-full">
          {radarData.length === 0 ? (
            <p className="text-sm text-slate-500">Run an evaluation to populate the chart.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: "#64748b" }} />
                <Radar
                  name="score"
                  dataKey="score"
                  stroke="#2563eb"
                  fill="#3b82f6"
                  fillOpacity={0.35}
                />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="mt-4 max-h-48 overflow-y-auto text-xs text-slate-600">
          <div className="font-semibold text-slate-700">Recent rows</div>
          <ul className="mt-2 space-y-2">
            {evaluation.results.map((r) => (
              <li key={String(r.id ?? r.ts)} className="rounded border border-slate-100 bg-slate-50 p-2">
                <div className="font-mono text-[10px] text-slate-400">{String(r.ts)}</div>
                <pre className="whitespace-pre-wrap">{JSON.stringify(r, null, 2)}</pre>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
