import { ShieldCheckIcon } from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";

import { adminConfig } from "../services/api";
import { useStore } from "../store";

export function GuardrailsConfig() {
  const [cfg, setCfg] = useState<Record<string, unknown> | null>(null);
  const strict = useStore((s) => s.strictClientPreview);
  const setStrict = useStore((s) => s.setStrictClientPreview);

  useEffect(() => {
    void (async () => {
      try {
        setCfg(await adminConfig());
      } catch {
        setCfg(null);
      }
    })();
  }, []);

  const g = (cfg?.guardrails ?? {}) as {
    input_chain?: { plugin: string; params: Record<string, unknown> }[];
    output_chain?: { plugin: string; params: Record<string, unknown> }[];
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800">
          <ShieldCheckIcon className="h-5 w-5 text-accent" />
          Active policy (from <code className="text-xs">config.yaml</code>)
        </div>
        <p className="text-xs text-slate-500">
          Backend applies these chains on every request. Changing them requires updating YAML and
          restarting the API.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Input</h3>
            <ul className="mt-2 space-y-2 text-sm text-slate-700">
              {(g.input_chain ?? []).map((s) => (
                <li key={s.plugin} className="rounded-lg border border-slate-100 bg-slate-50 p-2">
                  <div className="font-medium">{s.plugin}</div>
                  <pre className="mt-1 overflow-x-auto text-xs text-slate-600">
                    {JSON.stringify(s.params, null, 2)}
                  </pre>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Output</h3>
            <ul className="mt-2 space-y-2 text-sm text-slate-700">
              {(g.output_chain ?? []).map((s) => (
                <li key={s.plugin} className="rounded-lg border border-slate-100 bg-slate-50 p-2">
                  <div className="font-medium">{s.plugin}</div>
                  <pre className="mt-1 overflow-x-auto text-xs text-slate-600">
                    {JSON.stringify(s.params, null, 2)}
                  </pre>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800">UI preview mode</h3>
        <label className="mt-2 flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={strict} onChange={(e) => setStrict(e.target.checked)} />
          Highlight strict safety copy in tooltips (client-only; does not change server behavior).
        </label>
      </div>
    </div>
  );
}
