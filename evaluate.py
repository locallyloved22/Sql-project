#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_dataset import classify
from src.config import Config
from src.dataset_loader import DatasetLoader
from src.error_analysis import classify_error
from src.generator import Text2SQLPipeline
from src.metrics import compare_results, exact_match, has_order_by, jaccard_similarity
from src.sql_executor import dsn_for_domain, execute_readonly


FIELDS = ["experiment_id", "model", "domain", "question_id", "question", "gold_sql", "predicted_sql", "exact_match", "normalized_exact_match", "ast_valid", "valid_sql", "execution_correct", "jaccard_similarity", "latency_seconds", "correction_count", "complexity", "sql_type", "error_type", "failure_reason"]


def sql_type(sql: str) -> str:
    upper = sql.upper()
    if " JOIN " in f" {upper} ": return "join"
    if any(f"{name}(" in upper.replace(" ", "") for name in ("COUNT", "SUM", "AVG", "MIN", "MAX")): return "aggregation"
    if " WHERE " in f" {upper} ": return "filter"
    return "select"


def _normalized_latency(value: float, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 0.0
    return max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))


def _metrics(
    rows: list[dict[str, object]],
    latency_min: float | None = None,
    latency_max: float | None = None,
) -> dict[str, object]:
    if not rows:
        return {"count": 0}
    executed = [x for x in rows if x["execution_correct"] is not None]
    latencies = [float(x["latency_seconds"]) for x in rows]
    minimum = min(latencies) if latency_min is None else latency_min
    maximum = max(latencies) if latency_max is None else latency_max
    result = {
        "count": len(rows),
        "exact_match": sum(bool(x["exact_match"]) for x in rows) / len(rows),
        "normalized_exact_match": sum(bool(x["normalized_exact_match"]) for x in rows) / len(rows),
        "valid_sql_rate": sum(bool(x["valid_sql"]) for x in rows) / len(rows),
        "execution_accuracy": (sum(bool(x["execution_correct"]) for x in executed) / len(rows)) if executed else None,
        "execution_evaluated": len(executed),
        "jaccard_similarity": statistics.mean(float(x["jaccard_similarity"]) for x in rows),
        "latency_mean_seconds": statistics.mean(float(x["latency_seconds"]) for x in rows),
        "latency_median_seconds": statistics.median(float(x["latency_seconds"]) for x in rows),
        "corrections": sum(int(x["correction_count"]) for x in rows),
    }
    normalized_latency = statistics.mean(_normalized_latency(value, minimum, maximum) for value in latencies)
    result["normalized_latency"] = normalized_latency
    if result["execution_accuracy"] is not None:
        result["score"] = (
            0.50 * float(result["execution_accuracy"])
            + 0.20 * float(result["jaccard_similarity"])
            + 0.15 * float(result["valid_sql_rate"])
            + 0.10 * float(result["exact_match"])
            - 0.05 * normalized_latency
        )
    else:
        result["score"] = None
    return result


def evaluate(config: Config, output: Path, experiment_id: str = "custom", limit: int | None = None, execute: bool = True, split: str = "public") -> list[dict[str, object]]:
    if split != "public":
        raise ValueError("Оценка с gold SQL разрешена только на public split")
    root = Path(__file__).resolve().parents[1]
    examples = DatasetLoader(root).load("public")[:limit]
    pipeline = Text2SQLPipeline(str(root), config)
    rows: list[dict[str, object]] = []
    for index, example in enumerate(examples, 1):
        result = pipeline.generate(
            example.question,
            example.domain,
            example.id,
            execute=execute,
            execution_max_rows=None,
        )
        gold = example.gold_sql or ""
        raw_em = bool(result.sql.strip()) and result.sql.strip() == gold.strip()
        normalized_em = exact_match(result.sql, gold)
        execution_correct = False if execute else None
        failure = result.error or ""
        predicted_executed = bool(
            result.validation.valid
            and result.execution
            and result.execution.available
            and result.execution.success
        )
        if execute and predicted_executed:
            gold_result = execute_readonly(
                gold,
                dsn_for_domain(example.domain),
                config.statement_timeout_ms,
                max_rows=None,
            )
            if gold_result.success:
                execution_correct = compare_results(result.execution.rows or [], gold_result.rows or [], has_order_by(gold))
            else:
                failure = f"gold_execution_error: {gold_result.error}"
        elif execute and result.execution:
            failure = result.execution.error or failure
        complexity, _ = classify(gold)
        kind = "" if normalized_em else classify_error(result.sql, gold, result.validation.valid, execution_correct, failure)
        valid_sql = result.validation.valid and (predicted_executed if execute else True)
        rows.append({"experiment_id": experiment_id, "model": config.model or config.provider, "domain": example.domain, "question_id": example.id, "question": example.question, "gold_sql": gold, "predicted_sql": result.sql, "exact_match": raw_em, "normalized_exact_match": normalized_em, "ast_valid": result.validation.valid, "valid_sql": valid_sql, "execution_correct": execution_correct, "jaccard_similarity": round(jaccard_similarity(result.sql, gold), 6), "latency_seconds": round(result.latency_seconds, 6), "correction_count": max(0, result.attempts - 1), "complexity": complexity, "sql_type": sql_type(gold), "error_type": kind, "failure_reason": failure})
        print(f"[{index}/{len(examples)}] {example.domain}:{example.id}", file=sys.stderr)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
    return rows


def write_metrics(
    rows: list[dict[str, object]],
    path: Path,
    latency_min: float | None = None,
    latency_max: float | None = None,
) -> dict:
    by_domain, by_complexity, by_type = defaultdict(list), defaultdict(list), defaultdict(list)
    errors = Counter()
    for row in rows:
        by_domain[str(row["domain"])].append(row); by_complexity[str(row["complexity"])].append(row); by_type[str(row["sql_type"])].append(row)
        if row["error_type"]: errors[str(row["error_type"])] += 1
    observed = [float(row["latency_seconds"]) for row in rows]
    effective_min = latency_min if latency_min is not None else (min(observed) if observed else 0.0)
    effective_max = latency_max if latency_max is not None else (max(observed) if observed else 0.0)
    domain_metrics = {
        key: _metrics(value, effective_min, effective_max)
        for key, value in sorted(by_domain.items())
    }
    scores = [float(value["score"]) for value in domain_metrics.values() if value.get("score") is not None]
    report = {
        "overall": _metrics(rows, effective_min, effective_max),
        "by_domain": domain_metrics,
        "by_complexity": {k: _metrics(v, effective_min, effective_max) for k, v in sorted(by_complexity.items())},
        "by_sql_type": {k: _metrics(v, effective_min, effective_max) for k, v in sorted(by_type.items())},
        "final_score": statistics.mean(scores) if scores else None,
        "score_formula": "0.50*EX + 0.20*Jaccard + 0.15*VSR + 0.10*EM - 0.05*normLatency",
        "latency_normalization": {
            "method": "min-max",
            "minimum_seconds": effective_min,
            "maximum_seconds": effective_max,
            "scope": "explicit leaderboard bounds" if latency_min is not None else "current evaluation run",
        },
        "most_common_errors": [{"error": k, "count": v} for k, v in errors.most_common()],
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Execution-based public evaluation")
    parser.add_argument("--split", choices=["public"], default="public")
    parser.add_argument("--provider", choices=["benchmark", "mock", "openai", "ollama"])
    parser.add_argument("--model")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "outputs/public_results.csv")
    parser.add_argument("--metrics-output", type=Path, default=Path(__file__).parent / "outputs/public_metrics.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--no-execute", action="store_true")
    parser.add_argument("--latency-min-seconds", type=float, help="Leaderboard minimum for exact latency normalization")
    parser.add_argument("--latency-max-seconds", type=float, help="Leaderboard maximum for exact latency normalization")
    args = parser.parse_args()
    config = Config.from_file(None, provider=args.provider, model=args.model)
    rows = evaluate(config, args.output, limit=args.limit, execute=not args.no_execute, split=args.split)
    if (args.latency_min_seconds is None) != (args.latency_max_seconds is None):
        parser.error("--latency-min-seconds and --latency-max-seconds must be provided together")
    report = write_metrics(rows, args.metrics_output, args.latency_min_seconds, args.latency_max_seconds)
    print(f"Saved {len(rows)} rows to {args.output}")
    print(f"Saved metrics to {args.metrics_output}")
    if report["overall"].get("execution_accuracy") is None:
        print("Execution Accuracy unavailable: PostgreSQL execution did not complete.")
    else:
        print(f"FinalScore: {report['final_score']:.6f}")


if __name__ == "__main__":
    main()
