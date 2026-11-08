import { PaperAirplaneIcon, BookOpenIcon } from "@heroicons/react/24/outline";
import { motion } from "framer-motion";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

import { runQuery, runQueryStream } from "../services/api";
import { useStore } from "../store";

export function ChatInterface() {
  const [text, setText] = useState("");
  const [collectionId, setCollectionId] = useState<string | "">("");
  const [stream, setStream] = useState(true);
  const query = useStore((s) => s.query);
  const setQueryPartial = useStore((s) => s.setQueryPartial);
  const collections = useStore((s) => s.collections);

  async function onSend() {
    const q = text.trim();
    if (!q) return;
    setQueryPartial({
      error: null,
      streaming: stream,
      lastCached: false,
      lastAnswer: stream ? "" : query.lastAnswer,
    });
    try {
      if (stream) {
        let acc = "";
        await runQueryStream(
          {
            query: q,
            collection_id: collectionId || null,
            use_cache: true,
          },
          (tok) => {
            acc += tok;
            setQueryPartial({ lastAnswer: acc });
          },
          (evt) => {
            if (evt.done) {
              setQueryPartial({ streaming: false });
            }
            if (Array.isArray((evt as { warnings?: unknown }).warnings)) {
              /* optional: surface warnings */
            }
          },
        );
        setQueryPartial({ streaming: false, lastAnswer: acc });
      } else {
        const data = await runQuery({
          query: q,
          collection_id: collectionId || null,
          stream: false,
          use_cache: true,
        });
        setQueryPartial({
          lastAnswer: String(data.answer ?? ""),
          lastSources: (data.sources as typeof query.lastSources) ?? [],
          lastCached: data.cached === true,
          streaming: false,
        });
      }
      setText("");
    } catch (e) {
      setQueryPartial({
        error: e instanceof Error ? e.message : "Request failed",
        streaming: false,
      });
    }
  }

  return (
    <div className="grid h-full min-h-[560px] grid-cols-1 gap-4 lg:grid-cols-3">
      <motion.section
        layout
        className="lg:col-span-2 flex flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
      >
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <select
            className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-sm"
            value={collectionId}
            onChange={(e) => setCollectionId(e.target.value)}
          >
            <option value="">All collections</option>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={stream} onChange={(e) => setStream(e.target.checked)} />
            Stream (SSE)
          </label>
        </div>
        <div className="min-h-[320px] flex-1 overflow-y-auto rounded-xl bg-slate-50 p-4 text-sm leading-relaxed text-slate-800">
          {query.error && <p className="text-red-600">{query.error}</p>}
          {!query.lastAnswer && !query.error && (
            <p className="text-slate-500">Ask a question grounded in your ingested documents.</p>
          )}
          {query.lastAnswer && query.lastCached && (
            <p className="mb-2 inline-block rounded-md border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900">
              <span aria-hidden="true">⚡ </span>Cached answer
            </p>
          )}
          {query.lastAnswer && (
            <ReactMarkdown className="max-w-none text-slate-800">{query.lastAnswer}</ReactMarkdown>
          )}
        </div>
        <div className="mt-3 flex gap-2">
          <input
            className="flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none ring-accent focus:ring-2"
            placeholder="Ask something…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), void onSend())}
          />
          <button
            type="button"
            onClick={() => void onSend()}
            disabled={query.streaming}
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            <PaperAirplaneIcon className="h-5 w-5" />
            Send
          </button>
        </div>
      </motion.section>
      <aside className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800">
          <BookOpenIcon className="h-5 w-5 text-accent" />
          Sources
        </div>
        <div className="max-h-[480px] space-y-3 overflow-y-auto text-xs text-slate-600">
          {query.lastSources.length === 0 && <p className="text-slate-400">No structured sources yet.</p>}
          {query.lastSources.map((s, i) => (
            <div key={`${s.chunk_id}-${i}`} className="rounded-lg border border-slate-100 bg-slate-50 p-2">
              <div className="mb-1 font-medium text-slate-700">
                [{s.index ?? i + 1}] {s.document_id}
              </div>
              <div className="line-clamp-6 whitespace-pre-wrap">{s.preview}</div>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
