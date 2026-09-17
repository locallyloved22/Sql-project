#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.config import Config
from src.dataset_loader import DatasetLoader, write_submission
from src.generator import Text2SQLPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate submission without using private gold SQL")
    parser.add_argument("--split", choices=["public", "private"], default="public")
    parser.add_argument("--output", type=Path, default=Path("submission.csv"))
    parser.add_argument("--provider", choices=["openai", "ollama", "mock"])
    parser.add_argument("--model")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    examples = DatasetLoader(root).load_test_questions(args.split)
    if args.limit: examples = examples[:args.limit]
    config = Config.from_file(None, provider=args.provider, model=args.model)
    if config.provider == "benchmark":
        parser.error("benchmark provider запрещён для создания submission")
    if config.provider == "mock":
        print("WARNING: mock provider does not use an LLM and returns test fixtures.", file=sys.stderr)
    pipeline = Text2SQLPipeline(str(root), config)
    predictions = {}
    for index, example in enumerate(examples, 1):
        predictions[(example.domain, example.id)] = pipeline.generate(example.question, example.domain, example.id, execute=False).sql
        print(f"[{index}/{len(examples)}] {example.domain}:{example.id}", file=sys.stderr)
    write_submission(examples, predictions, args.output)
    print(f"Saved {len(examples)} predictions to {args.output}")


if __name__ == "__main__":
    main()
