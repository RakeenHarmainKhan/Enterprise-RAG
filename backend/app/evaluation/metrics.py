"""RAGAS-inspired metrics using the configured LLM."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.config import EvaluationConfig, YamlAppConfig
from app.core.exceptions import EvaluationError
from app.core.llm import LLMProvider


class EvaluationEngine:
    def __init__(self, yaml_cfg: YamlAppConfig, llm: LLMProvider) -> None:
        self._cfg: EvaluationConfig = yaml_cfg.evaluation
        self._llm = llm
        self._results: list[dict[str, Any]] = []

    async def _llm_score(self, system: str, user: str) -> float:
        raw = await self._llm.acomplete(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=16,
        )
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+", raw)
        if not m:
            raise EvaluationError(f"Could not parse score from: {raw!r}")
        return max(0.0, min(1.0, float(m.group(0))))

    async def faithfulness(self, answer: str, contexts: list[str]) -> float:
        ctx = "\n".join(f"- {c[:600]}" for c in contexts)
        system = "Rate faithfulness 0-1: does every claim in the answer follow from the context? Reply with one number only."
        user = f"Context:\n{ctx}\n\nAnswer:\n{answer[:1200]}"
        return await self._llm_score(system, user)

    async def answer_relevance(self, question: str, answer: str) -> float:
        system = "Rate 0-1: does the answer address the question? Reply with one number only."
        user = f"Q: {question}\nA: {answer[:1200]}"
        return await self._llm_score(system, user)

    async def context_precision(self, question: str, contexts: list[str]) -> float:
        if not contexts:
            return 0.0
        scores = []
        for c in contexts[:5]:
            system = "Rate 0-1: is this excerpt useful to answer the question? Reply with one number only."
            user = f"Q: {question}\nExcerpt: {c[:800]}"
            scores.append(await self._llm_score(system, user))
        return sum(scores) / len(scores)

    async def context_recall(self, question: str, answer: str, contexts: list[str]) -> float:
        ctx = "\n".join(f"- {c[:400]}" for c in contexts[:6])
        system = "Rate 0-1: could the answer be fully derived from the context? Reply with one number only."
        user = f"Q: {question}\nContext:\n{ctx}\nAnswer:\n{answer[:800]}"
        return await self._llm_score(system, user)

    async def run_suite(
        self,
        *,
        question: str,
        answer: str,
        contexts: list[str],
    ) -> dict[str, Any]:
        metrics = list(self._cfg.metrics)
        row: dict[str, Any] = {"id": str(uuid.uuid4()), "ts": datetime.now(timezone.utc).isoformat()}
        try:
            if "faithfulness" in metrics:
                row["faithfulness"] = await self.faithfulness(answer, contexts)
            if "answer_relevance" in metrics:
                row["answer_relevance"] = await self.answer_relevance(question, answer)
            if "context_precision" in metrics:
                row["context_precision"] = await self.context_precision(question, contexts)
            if "context_recall" in metrics:
                row["context_recall"] = await self.context_recall(question, answer, contexts)
        except Exception as e:
            raise EvaluationError(str(e)) from e
        self._results.append(row)
        return row

    def list_results(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(self._results[-limit:]))
