"""RAG-style evaluation runs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import EvaluationDep
from app.core.exceptions import EvaluationError

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvalRunBody(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    contexts: list[str] = Field(default_factory=list, max_length=32)


@router.post("/run")
async def run_eval(body: EvalRunBody, engine: EvaluationDep) -> dict[str, Any]:
    try:
        row = await engine.run_suite(question=body.question, answer=body.answer, contexts=body.contexts)
        return row
    except EvaluationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/results")
async def eval_results(engine: EvaluationDep, limit: int = 50) -> dict[str, Any]:
    return {"results": engine.list_results(limit=limit)}
