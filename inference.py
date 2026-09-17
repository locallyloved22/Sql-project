#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.config import Config
from src.generator import Text2SQLPipeline
from src.llm_client import LLMError


def main() -> None:
    parser = argparse.ArgumentParser(description="Сгенерировать PostgreSQL для одного вопроса")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--question-id", type=int)
    parser.add_argument("--config")
    parser.add_argument("--provider", choices=["mock", "openai", "ollama"])
    parser.add_argument("--model")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        config = Config.from_file(args.config, provider=args.provider, model=args.model)
        if config.provider == "mock":
            print("WARNING: mock provider does not use an LLM and returns test fixtures.", file=sys.stderr)
        root = Path(__file__).resolve().parents[1]
        result = Text2SQLPipeline(str(root), config).generate(args.question, args.domain, args.question_id, args.execute)
    except (LLMError, ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        raise SystemExit(2)
    if args.as_json:
        print(json.dumps({"predicted_sql": result.sql, "valid_sql": result.validation.valid, "validation_messages": result.validation.errors, "latency_seconds": result.latency_seconds, "selected_tables": result.selected_tables, "attempts": result.attempts, "execution_available": result.execution.available if result.execution else False, "execution_error": result.execution.error if result.execution else None}, ensure_ascii=False, indent=2))
    else:
        print(result.sql)


if __name__ == "__main__":
    main()
