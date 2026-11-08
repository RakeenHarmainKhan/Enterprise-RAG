import { create } from "zustand";

import type { Collection, DocumentMeta } from "../services/api";

export type UiTab =
  | "chat"
  | "documents"
  | "collections"
  | "analytics"
  | "evaluation"
  | "settings";

type QueryState = {
  lastAnswer: string;
  lastSources: { index?: number; preview?: string; chunk_id?: string; document_id?: string }[];
  lastCached: boolean;
  streaming: boolean;
  error: string | null;
};

type EvaluationState = {
  results: Record<string, unknown>[];
  lastRun: Record<string, unknown> | null;
};

type UiSlice = {
  tab: UiTab;
  setTab: (t: UiTab) => void;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
};

type DocumentsSlice = {
  documents: DocumentMeta[];
  setDocuments: (d: DocumentMeta[]) => void;
};

type CollectionsSlice = {
  collections: Collection[];
  setCollections: (c: Collection[]) => void;
};

type QuerySlice = {
  query: QueryState;
  setQueryPartial: (p: Partial<QueryState>) => void;
  resetQuery: () => void;
};

type EvaluationSlice = {
  evaluation: EvaluationState;
  setEvalResults: (r: Record<string, unknown>[]) => void;
  setLastEval: (r: Record<string, unknown> | null) => void;
};

type GuardrailsSlice = {
  strictClientPreview: boolean;
  setStrictClientPreview: (v: boolean) => void;
};

export type RootState = UiSlice &
  DocumentsSlice &
  CollectionsSlice &
  QuerySlice &
  EvaluationSlice &
  GuardrailsSlice;

const initialQuery: QueryState = {
  lastAnswer: "",
  lastSources: [],
  lastCached: false,
  streaming: false,
  error: null,
};

export const useStore = create<RootState>((set) => ({
  tab: "chat",
  setTab: (t) => set({ tab: t }),
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  documents: [],
  setDocuments: (documents) => set({ documents }),

  collections: [],
  setCollections: (collections) => set({ collections }),

  query: initialQuery,
  setQueryPartial: (p) => set((s) => ({ query: { ...s.query, ...p } })),
  resetQuery: () => set({ query: initialQuery }),

  evaluation: { results: [], lastRun: null },
  setEvalResults: (results) => set((s) => ({ evaluation: { ...s.evaluation, results } })),
  setLastEval: (lastRun) => set((s) => ({ evaluation: { ...s.evaluation, lastRun } })),

  strictClientPreview: true,
  setStrictClientPreview: (strictClientPreview) => set({ strictClientPreview }),
}));
