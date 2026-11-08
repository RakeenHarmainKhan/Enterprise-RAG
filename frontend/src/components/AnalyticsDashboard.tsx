import {
  ArrowTrendingUpIcon,
  CircleStackIcon,
  ServerStackIcon,
} from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { adminStats } from "../services/api";

const demoLatency = [
  { t: "T-4", ms: 420 },
  { t: "T-3", ms: 390 },
  { t: "T-2", ms: 360 },
  { t: "T-1", ms: 340 },
  { t: "now", ms: 330 },
];

export function AnalyticsDashboard() {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setStats(await adminStats());
      } catch {
        setStats(null);
      }
    })();
  }, []);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <CircleStackIcon className="h-5 w-5 text-accent" />
            Index chunks (approx)
          </div>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {String(stats?.chunk_documents_approx ?? "—")}
          </p>
          <p className="text-xs text-slate-500">OpenSearch document count</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <ServerStackIcon className="h-5 w-5 text-accent" />
            Registered docs
          </div>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {String(stats?.registered_documents ?? "—")}
          </p>
          <p className="text-xs text-slate-500">Upload registry</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <ArrowTrendingUpIcon className="h-5 w-5 text-accent" />
            Reindex
          </div>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {stats?.reindex_requested ? "Yes" : "Idle"}
          </p>
          <p className="text-xs text-slate-500">Admin job flag</p>
        </div>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-2 text-sm font-semibold text-slate-800">Query latency (illustrative)</div>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={demoLatency}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="t" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip />
              <Line type="monotone" dataKey="ms" stroke="#2563eb" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Wire to Langfuse or OpenTelemetry for live latency; sample series shown for layout.
        </p>
      </div>
    </div>
  );
}
