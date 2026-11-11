"""Score a fixed question set against PodSeek.

Offline (default): score built-in fixture answers. No API key and no index.

    python -m scripts.evaluate

Live: POST each question to a running API (or run in-process if localhost:8000 is not up).

    python -m scripts.evaluate --live --mode balanced

Optional LLM-as-judge (live only, no Ragas):

    python -m scripts.evaluate --live --llm-judge
"""

import argparse
import json
import logging
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Literal, cast

import httpx
from dotenv import load_dotenv
from langchain_core.tracers.langchain import wait_for_all_tracers

from app.evaluation import offline_fixture, score_example
from app.observability import configure_tracing

# Suppress noisy google-genai SDK warning when LangChain uses tool-calling for structured output
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*automatic function calling.*")

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "evals" / "questions.json"


def load_questions() -> list[dict]:
    return json.loads(QUESTIONS_PATH.read_text())


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = (pct / 100.0) * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return round(sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo]), 1)


def ask_live(api_url: str, question: str, mode: str = "balanced") -> dict:
    try:
        response = httpx.post(
            f"{api_url.rstrip('/')}/ask",
            json={"question": question, "mode": mode},
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        from app.agent.graph import corrective_rag_agent
        from app.api.routes import _build_citations, _initial_state
        from app.observability import trace_config
        from app.schemas import AskResponse

        mode_val = cast(
            Literal["turbo", "balanced", "rigorous"],
            mode if mode in {"turbo", "balanced", "rigorous"} else "balanced",
        )
        start_time = time.perf_counter()
        final_state = corrective_rag_agent.invoke(
            _initial_state(question, mode=mode_val),
            config=trace_config("/ask", mode=mode_val),
        )
        relevant_docs = final_state.get("relevant_documents", [])
        citations = _build_citations(relevant_docs)
        answer = final_state.get("generation", "")
        rewrites = final_state.get("rewrite_count", 0)
        top_dist = final_state.get("top_distance")
        latency = round((time.perf_counter() - start_time) * 1000, 1)
        return AskResponse(
            question=question,
            answer=answer,
            citations=citations,
            rewrites_attempted=rewrites,
            relevant_chunks_used=len(relevant_docs),
            mode=mode_val,
            top_distance=top_dist,
            latency_ms=latency,
        ).model_dump()


def llm_relevance(question: str, answer: str) -> int:
    """Ask the configured chat model for a 1–5 relevance score."""
    from langchain_core.prompts import ChatPromptTemplate
    from pydantic import BaseModel, Field

    from app.factory import get_chat_model

    class RelevanceJudgement(BaseModel):
        score: int = Field(
            ge=1, le=5, description="1 means irrelevant, 5 means the answer fully addresses the question."
        )

    llm = get_chat_model(temperature=0.0)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Score how well the answer addresses the question. "
                "Use only the answer text. Return a score from 1 (irrelevant) to 5 (fully answers).",
            ),
            ("human", "Question:\n{question}\n\nAnswer:\n{answer}"),
        ]
    )
    result = (prompt | llm.with_structured_output(RelevanceJudgement)).invoke({"question": question, "answer": answer})
    if isinstance(result, RelevanceJudgement):
        return result.score
    if isinstance(result, dict):
        return int(result["score"])
    return int(getattr(result, "score", 1))


def _print_header() -> None:
    header = (
        f"{'id':<26} {'keyword':>8} {'citations':>10} {'rewrites':>9} {'latency_ms':>11} {'judge':>6} {'status':>8}"
    )
    print(header)
    print("-" * len(header), flush=True)


def _print_row(row: dict) -> None:
    judge = "-" if row["judge"] is None else f"{row['judge']}/5"
    citations = "yes" if row["citations_valid"] else "no"
    latency = "-" if row["latency_ms"] is None else f"{row['latency_ms']:.1f}"
    status = "PASS" if row["passed"] else "FAIL"
    print(
        f"{row['id']:<26} {row['keyword_score']:>8.2f} {citations:>10} {row['rewrites']:>9} {latency:>11} {judge:>6} {status:>8}",
        flush=True,
    )


def _print_legend(rows: list[dict], mode: str) -> None:
    total_count = len(rows)
    passed_count = sum(1 for r in rows if r["passed"])
    in_scope_rows = [r for r in rows if r["expect_citations"]]
    avg_keyword = sum(r["keyword_score"] for r in in_scope_rows) / len(in_scope_rows) if in_scope_rows else 0.0
    latencies = sorted(float(r["latency_ms"]) for r in rows if r["latency_ms"] is not None)
    p50 = _percentile(latencies, 50.0)
    p95 = _percentile(latencies, 95.0)

    print()
    print(
        f"Summary ({mode}): {passed_count}/{total_count} citation checks passed ({(passed_count / total_count) * 100:.1f}%) "
        f"| In-scope keyword hit rate: {avg_keyword * 100:.1f}% "
        f"| Latency p50: {p50:.1f}ms, p95: {p95:.1f}ms"
    )
    print("Legend:")
    print("  keyword    : Fraction of expected domain keywords present in answer (0.00 - 1.00)")
    print("  citations  : 'yes' if all returned citations have valid HH:MM:SS + YouTube ?t= deep links")
    print("  rewrites   : Number of Corrective RAG query rewrites triggered (0 - 2)")
    print("  latency_ms : End-to-end AskResponse.latency_ms (or '-' in offline mode)")
    print("  judge      : Optional LLM-as-judge relevance score (1 - 5, or '-' if skipped)")
    print("  status     : PASS if citation behavior matches expectation (in-scope='yes', off-topic='no')")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Evaluate PodSeek on a fixed question set.")
    parser.add_argument("--live", action="store_true", help="Call POST /ask instead of offline fixtures.")
    parser.add_argument(
        "--mode",
        choices=["turbo", "balanced", "rigorous"],
        default="balanced",
        help="Execution mode for live evaluation (default: balanced).",
    )
    parser.add_argument("--llm-judge", action="store_true", help="Add a 1-5 LLM relevance score. Requires --live.")
    parser.add_argument(
        "--api-url",
        default=os.getenv("PODSEEK_API_URL") or os.getenv("ASKPODCAST_API_URL", "http://localhost:8000"),
        help="Base URL of a running PodSeek API.",
    )
    args = parser.parse_args(argv)

    if args.llm_judge and not args.live:
        print("LLM judge skipped: it only runs with --live.")

    if args.live:
        configure_tracing()
        print(f"Live evaluation (mode={args.mode}) against {args.api_url}\n")
    else:
        print("Offline evaluation (fixture answers, no API call).\n")

    questions = load_questions()
    rows: list[dict] = []
    failed = False

    _print_header()

    try:
        for item in questions:
            judge: int | None = None
            try:
                if args.live:
                    payload = ask_live(args.api_url, item["question"], mode=args.mode)
                else:
                    payload = offline_fixture(item)
            except Exception as exc:
                print(f"{item['id']:<26} request failed: {exc}", flush=True)
                failed = True
                continue

            scored = score_example(
                str(payload.get("answer", "")),
                list(payload.get("citations", [])),
                list(item.get("keywords", [])),
            )
            if args.live and args.llm_judge:
                judge = llm_relevance(item["question"], str(payload.get("answer", "")))

            expect_citations = bool(item.get("expect_citations", True))
            passed = bool(scored["citations_valid"]) == expect_citations
            if not passed:
                failed = True

            raw_lat = payload.get("latency_ms")
            row = {
                "id": item["id"],
                "keyword_score": scored["keyword_score"],
                "citations_valid": scored["citations_valid"],
                "rewrites": int(payload.get("rewrites_attempted", 0)),
                "latency_ms": float(raw_lat) if raw_lat is not None else None,
                "judge": judge,
                "expect_citations": expect_citations,
                "passed": passed,
            }
            rows.append(row)
            _print_row(row)

        if rows:
            _print_legend(rows, mode=args.mode if args.live else "offline")

        return 1 if failed else 0
    finally:
        wait_for_all_tracers()


if __name__ == "__main__":
    sys.exit(main())
