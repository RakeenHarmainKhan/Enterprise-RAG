import { CloudArrowUpIcon, TrashIcon } from "@heroicons/react/24/outline";
import { motion } from "framer-motion";
import { useCallback, useState } from "react";

import { deleteDocument, listDocuments, uploadDocument } from "../services/api";
import { useStore } from "../store";

export function DocumentManager() {
  const documents = useStore((s) => s.documents);
  const setDocuments = useStore((s) => s.setDocuments);
  const collections = useStore((s) => s.collections);
  const [collectionId, setCollectionId] = useState<string | "">("");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);

  const refresh = useCallback(async () => {
    const rows = await listDocuments();
    setDocuments(rows);
  }, [setDocuments]);

  async function onFiles(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    try {
      for (const f of Array.from(files)) {
        await uploadDocument(f, collectionId || undefined);
      }
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select
          className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-sm"
          value={collectionId}
          onChange={(e) => setCollectionId(e.target.value)}
        >
          <option value="">Default collection</option>
          {collections.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => void refresh()}
          className="rounded-lg border border-slate-200 px-3 py-1 text-sm hover:bg-slate-50"
        >
          Refresh
        </button>
      </div>
      <motion.div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          void onFiles(e.dataTransfer.files);
        }}
        className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center transition ${
          drag ? "border-accent bg-accent-soft" : "border-slate-200 bg-white"
        }`}
      >
        <CloudArrowUpIcon className="mb-2 h-10 w-10 text-slate-400" />
        <p className="text-sm font-medium text-slate-700">Drag & drop files here</p>
        <p className="text-xs text-slate-500">PDF, DOCX, HTML, Markdown</p>
        <label className="mt-4 inline-flex cursor-pointer rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
          Browse
          <input
            type="file"
            className="hidden"
            multiple
            disabled={busy}
            onChange={(e) => void onFiles(e.target.files)}
          />
        </label>
      </motion.div>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">File</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Chunks</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id} className="border-t border-slate-100">
                <td className="px-4 py-2 font-medium text-slate-800">{d.filename}</td>
                <td className="px-4 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      d.status === "ready"
                        ? "bg-emerald-50 text-emerald-700"
                        : d.status === "failed"
                          ? "bg-red-50 text-red-700"
                          : "bg-amber-50 text-amber-800"
                    }`}
                  >
                    {d.status}
                  </span>
                </td>
                <td className="px-4 py-2 text-slate-600">{d.chunks ?? "—"}</td>
                <td className="px-4 py-2 text-right">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50"
                    onClick={async () => {
                      await deleteDocument(d.id);
                      await refresh();
                    }}
                  >
                    <TrashIcon className="h-4 w-4" />
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-500" colSpan={4}>
                  No documents yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
