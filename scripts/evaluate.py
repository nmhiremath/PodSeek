"""Score a fixed question set against PodSeek.

Offline (default): score built-in fixture answers. No API key and no index.

    python -m scripts.evaluate

Live: POST each question to a running API. Needs an indexed episode.

    python -m scripts.evaluate --live

Optional LLM-as-judge (live only, no Ragas):

    python -m scripts.evaluate --live --llm-judge
"""

import argparse
import json
import logging
import os
import sys
import warnings
from pathlib import Path

import httpx
from dotenv import load_dotenv

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


def ask_live(api_url: str, question: str) -> dict:
    response = httpx.post(
        f"{api_url.rstrip('/')}/ask",
        json={"question": question},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


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
    header = f"{'id':<20} {'keyword':>8} {'citations':>10} {'rewrites':>9} {'judge':>6} {'status':>8}"
    print(header)
    print("-" * len(header), flush=True)


def _print_row(row: dict) -> None:
    judge = "-" if row["judge"] is None else f"{row['judge']}/5"
    citations = "yes" if row["citations_valid"] else "no"
    status = "PASS" if row["passed"] else "FAIL"
    print(
        f"{row['id']:<20} {row['keyword_score']:>8.2f} {citations:>10} {row['rewrites']:>9} {judge:>6} {status:>8}",
        flush=True,
    )


def _print_legend(passed_count: int, total_count: int) -> None:
    print()
    print(f"Summary: {passed_count}/{total_count} test cases passed.")
    print("Legend:")
    print("  keyword   : Fraction of expected domain keywords present in answer (0.00 - 1.00)")
    print("  citations : 'yes' if all returned citations have valid HH:MM:SS + YouTube ?t= deep links")
    print("  rewrites  : Number of Corrective RAG query rewrites triggered (0 - 2)")
    print("  judge     : Optional LLM-as-judge relevance score (1 - 5, or '-' if skipped)")
    print("  status    : PASS if citation behavior matches expectation (in-scope='yes', off-topic='no')")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Evaluate PodSeek on a fixed question set.")
    parser.add_argument("--live", action="store_true", help="Call POST /ask instead of offline fixtures.")
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
        print(f"Live evaluation against {args.api_url}\n")
    else:
        print("Offline evaluation (fixture answers, no API call).\n")

    questions = load_questions()
    rows: list[dict] = []
    failed = False

    _print_header()

    for item in questions:
        judge: int | None = None
        try:
            if args.live:
                payload = ask_live(args.api_url, item["question"])
            else:
                payload = offline_fixture(item)
        except Exception as exc:
            print(f"{item['id']:<20} request failed: {exc}", flush=True)
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

        row = {
            "id": item["id"],
            "keyword_score": scored["keyword_score"],
            "citations_valid": scored["citations_valid"],
            "rewrites": int(payload.get("rewrites_attempted", 0)),
            "judge": judge,
            "passed": passed,
        }
        rows.append(row)
        _print_row(row)

    if rows:
        passed_count = sum(1 for r in rows if r["passed"])
        _print_legend(passed_count, len(rows))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
