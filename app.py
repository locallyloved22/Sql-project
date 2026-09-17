#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.answer_formatter import format_answer, safe_rows
from src.config import Config
from src.dataset_loader import DatasetLoader
from src.generator import Text2SQLPipeline
from src.llm_client import LLMError
from src.schema_parser import parse_schema


ROOT = Path(__file__).resolve().parents[1]
DOMAINS = DatasetLoader(ROOT).domains("public")


def run_question(pipeline: Text2SQLPipeline, config: Config, domain: str, question: str) -> dict:
    started = time.perf_counter()
    result = pipeline.generate(question, domain, execute=True)
    execution = result.execution
    columns = execution.columns if execution and execution.success else []
    rows = safe_rows(execution.rows if execution and execution.success else [])
    if not result.validation.valid:
        status = "validation_error"
    elif not execution or not execution.available:
        status = "unavailable"
    elif not execution.success:
        status = "execution_error"
    else:
        status = "success"
    error = result.error or (execution.error if execution and not execution.success else None)
    if status == "unavailable" and execution:
        error = execution.error
    answer = format_answer(columns or [], rows) if status == "success" else "Результат не получен."
    return {
        "domain": domain,
        "question": question,
        "model": "mock-test-fixtures" if config.provider == "mock" else (config.model or "not-configured"),
        "provider": config.provider,
        "generated_sql": result.sql,
        "initial_sql": result.initial_sql,
        "valid_sql": result.validation.valid,
        "validation_errors": result.validation.errors,
        "execution_status": status,
        "columns": columns or [],
        "rows": rows,
        "row_count": len(rows),
        "answer": answer,
        "latency_seconds": round(time.perf_counter() - started, 4),
        "correction_attempts": max(0, result.attempts - 1),
        "execution_error": result.initial_execution_error,
        "corrected_sql": result.corrected_sql,
        "final_status": status,
        "error": error,
    }


def print_human(data: dict) -> None:
    print(f"\nDomain: {data['domain']}")
    print(f"Model: {data['model']} ({data['provider']})")
    if data.get("correction_attempts"):
        print("\nInitial SQL:\n" + str(data["initial_sql"]))
        print("\nExecution error:\n" + str(data.get("execution_error") or data.get("error")))
        print("\nCorrected SQL:\n" + str(data.get("corrected_sql")))
    else:
        print("\nGenerated SQL:\n" + str(data["generated_sql"]))
    print(f"\nValid SQL: {str(data['valid_sql']).lower()}")
    print(f"Execution status: {data['execution_status']}")
    print(f"Latency: {data['latency_seconds']} sec")
    if data["error"]:
        print(f"Error: {data['error']}")
    print("\nResult:\n" + data["answer"])


def choose_domain() -> str:
    print("Доступные домены:")
    for index, domain in enumerate(DOMAINS, 1):
        print(f"  {index}. {domain}")
    while True:
        value = input("Выберите номер или введите имя домена: ").strip()
        if value.isdigit() and 1 <= int(value) <= len(DOMAINS):
            return DOMAINS[int(value) - 1]
        if value in DOMAINS:
            return value
        print("Неизвестный домен.")


def interactive(pipeline: Text2SQLPipeline, config: Config) -> None:
    domain = choose_domain()
    print("Введите вопрос. Команды: /domains, /schema, /quit")
    while True:
        try:
            question = input(f"\n[{domain}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            return
        if not question:
            continue
        if question == "/quit":
            return
        if question == "/domains":
            domain = choose_domain()
            continue
        if question == "/schema":
            schema = parse_schema(DatasetLoader(ROOT).schema_path(domain))
            for table in schema.tables.values():
                print(f"{table.name}: {', '.join(table.columns)}")
            continue
        try:
            print_human(run_question(pipeline, config, domain, question))
        except Exception as exc:
            print(f"Ошибка: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end Text2SQL MVP")
    parser.add_argument("--domain", choices=DOMAINS)
    parser.add_argument("--question")
    parser.add_argument("--provider", choices=["openai", "ollama", "mock"])
    parser.add_argument("--model")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    if bool(args.domain) != bool(args.question):
        parser.error("--domain и --question нужно передавать вместе")
    try:
        config = Config.from_file(None, provider=args.provider, model=args.model)
        if config.provider == "mock":
            print("WARNING: mock provider does not use an LLM and returns test fixtures.", file=sys.stderr)
        pipeline = Text2SQLPipeline(str(ROOT), config)
        if not args.question:
            interactive(pipeline, config)
            return
        data = run_question(pipeline, config, args.domain, args.question)
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.as_json else "", end="" if args.as_json else "")
        if not args.as_json:
            print_human(data)
    except (LLMError, ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
