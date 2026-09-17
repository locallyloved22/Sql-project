#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


AGGREGATES = ("COUNT", "SUM", "AVG", "MIN", "MAX")


def words(text: str) -> list[str]:
    return re.findall(r"[\wА-Яа-яЁё]+", text, flags=re.UNICODE)


def sql_tokens(sql: str) -> list[str]:
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|<>|!=|<=|>=|\S", sql)


def count_subqueries(sql: str) -> int:
    # SELECT at depth > 0 is a useful, deterministic approximation for this report.
    depth = 0
    count = 0
    for token in re.findall(r"\(|\)|\bSELECT\b", sql.upper()):
        if token == "(":
            depth += 1
        elif token == ")":
            depth = max(0, depth - 1)
        elif depth > 0:
            count += 1
    return count


def classify(sql: str) -> tuple[str, dict[str, int | bool]]:
    upper = sql.upper()
    joins = len(re.findall(r"\bJOIN\b", upper))
    subqueries = count_subqueries(sql)
    cte = bool(re.match(r"^\s*WITH\b", upper))
    windows = len(re.findall(r"\bOVER\s*\(", upper))
    group = "GROUP BY" in upper
    having = "HAVING" in upper
    union = bool(re.search(r"\b(?:UNION|INTERSECT|EXCEPT)\b", upper))
    aggregates = sum(bool(re.search(rf"\b{name}\s*\(", upper)) for name in AGGREGATES)
    score = joins + 2 * subqueries + 2 * int(cte) + 2 * windows + int(group) + int(having) + 2 * int(union)
    if score <= 1 and joins <= 1 and subqueries == 0:
        level = "simple"
    elif score <= 4 and joins <= 2 and subqueries <= 1 and not windows:
        level = "medium"
    else:
        level = "hard"
    return level, {
        "joins": joins,
        "subqueries": subqueries,
        "cte": cte,
        "window_functions": windows,
        "group_by": group,
        "having": having,
        "set_operation": union,
        "aggregate_function_types": aggregates,
        "complexity_score": score,
    }


def table_count(schema: str) -> int:
    return len(re.findall(r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\w.\"]+", schema, re.I))


def summarize(root: Path) -> dict[str, Any]:
    domain_rows: dict[str, dict[str, Any]] = {}
    all_questions: list[str] = []
    all_sql: list[str] = []
    complexity = Counter()
    feature_counts = Counter()

    for domain_dir in sorted((root / "databases").iterdir()):
        if not domain_dir.is_dir() or not (domain_dir / "questions.json").exists():
            continue
        rows = json.loads((domain_dir / "questions.json").read_text(encoding="utf-8"))
        questions = [str(row["question"]) for row in rows]
        sqls = [str(row["gold_sql"]) for row in rows]
        levels = Counter()
        local_features = Counter()
        for sql in sqls:
            level, features = classify(sql)
            levels[level] += 1
            complexity[level] += 1
            local_features["join"] += int(features["joins"] > 0)
            local_features["multiple_joins"] += int(features["joins"] > 1)
            local_features["subquery"] += int(features["subqueries"] > 0)
            local_features["cte"] += int(features["cte"])
            local_features["window_function"] += int(features["window_functions"] > 0)
            upper = sql.upper()
            for name in AGGREGATES:
                local_features[name.lower()] += len(re.findall(rf"\b{name}\s*\(", upper))
            for label, phrase in (("group_by", "GROUP BY"), ("order_by", "ORDER BY"), ("limit", "LIMIT")):
                local_features[label] += int(phrase in upper)
        feature_counts.update(local_features)
        q_lengths = [len(words(q)) for q in questions]
        s_lengths = [len(sql_tokens(s)) for s in sqls]
        domain_rows[domain_dir.name] = {
            "tables": table_count((domain_dir / "schema.sql").read_text(encoding="utf-8")),
            "questions": len(rows),
            "question_length_words": {"mean": round(statistics.mean(q_lengths), 2), "median": statistics.median(q_lengths)},
            "sql_length_tokens": {"mean": round(statistics.mean(s_lengths), 2), "median": statistics.median(s_lengths)},
            "features": dict(sorted(local_features.items())),
            "complexity": {level: levels[level] for level in ("simple", "medium", "hard")},
        }
        all_questions.extend(questions)
        all_sql.extend(sqls)

    q_lengths = [len(words(q)) for q in all_questions]
    s_lengths = [len(sql_tokens(s)) for s in all_sql]
    return {
        "source": "databases/*/questions.json (all 500 original examples; private files are not read)",
        "classification": {
            "simple": "score <= 1; no subquery; at most one JOIN",
            "medium": "score <= 4; at most two JOINs and one subquery; no window function",
            "hard": "all remaining queries",
            "score": "JOIN + 2*subquery + 2*CTE + 2*window + GROUP BY + HAVING + 2*set operation",
        },
        "totals": {
            "domains": len(domain_rows),
            "tables": sum(x["tables"] for x in domain_rows.values()),
            "questions": len(all_questions),
            "question_length_words": {"mean": round(statistics.mean(q_lengths), 2), "median": statistics.median(q_lengths)},
            "sql_length_tokens": {"mean": round(statistics.mean(s_lengths), 2), "median": statistics.median(s_lengths)},
            "features": dict(sorted(feature_counts.items())),
            "complexity": {level: complexity[level] for level in ("simple", "medium", "hard")},
        },
        "domains": domain_rows,
    }


def markdown(data: dict[str, Any]) -> str:
    totals = data["totals"]
    lines = [
        "# Анализ датасета Text2SQL", "",
        "> Источник анализа: только исходные `databases/*/questions.json`. Private-файлы не используются для генерации предсказаний.", "",
        "## Итоги", "",
        f"- Доменов: **{totals['domains']}**.",
        f"- Таблиц: **{totals['tables']}**.",
        f"- Вопросов: **{totals['questions']}**.",
        f"- Длина вопроса: mean {totals['question_length_words']['mean']}, median {totals['question_length_words']['median']} слов.",
        f"- Длина SQL: mean {totals['sql_length_tokens']['mean']}, median {totals['sql_length_tokens']['median']} токенов.", "",
        "## По доменам", "",
        "| Домен | Таблиц | Вопросов | Mean/median вопроса | Mean/median SQL | Simple | Medium | Hard |", "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in data["domains"].items():
        lines.append(f"| `{name}` | {row['tables']} | {row['questions']} | {row['question_length_words']['mean']} / {row['question_length_words']['median']} | {row['sql_length_tokens']['mean']} / {row['sql_length_tokens']['median']} | {row['complexity']['simple']} | {row['complexity']['medium']} | {row['complexity']['hard']} |")
    lines += ["", "## Конструкции SQL", "", "| Признак | Частота |", "|---|---:|"]
    labels = {"join": "SQL с JOIN", "multiple_joins": "SQL с несколькими JOIN", "count": "COUNT", "sum": "SUM", "avg": "AVG", "min": "MIN", "max": "MAX", "group_by": "GROUP BY", "order_by": "ORDER BY", "limit": "LIMIT", "subquery": "SQL с подзапросом", "cte": "SQL с CTE", "window_function": "SQL с оконной функцией"}
    for key in labels:
        lines.append(f"| {labels[key]} | {totals['features'].get(key, 0)} |")
    lines += ["", "## Сложность", "", f"- Simple: **{totals['complexity']['simple']}**.", f"- Medium: **{totals['complexity']['medium']}**.", f"- Hard: **{totals['complexity']['hard']}**.", "", "Классификация эвристическая и предназначена для воспроизводимых срезов экспериментов, а не как абсолютная оценка семантической сложности.", "", "## Правило классификации", "", f"`{data['classification']['score']}`", "", "Simple не содержит подзапросов и имеет не более одного JOIN при score ≤ 1. Medium имеет score ≤ 4, не более двух JOIN, не более одного подзапроса и не содержит оконных функций. Остальные запросы считаются hard.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", type=Path, default=Path("dataset_analysis.json"))
    parser.add_argument("--markdown", type=Path, default=Path("DATASET_ANALYSIS.md"))
    args = parser.parse_args()
    data = summarize(args.root)
    args.json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(data), encoding="utf-8")
    print(f"Created {args.json} and {args.markdown}: {data['totals']['questions']} questions")


if __name__ == "__main__":
    main()
