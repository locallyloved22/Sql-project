import hashlib
import json
import random
import shutil
import csv
from pathlib import Path
from typing import List, Dict, Any, Tuple

SEED = 42
PUBLIC_RATIO = 0.5  # fraction of questions that go to public


def _domain_seed(domain_name: str) -> int:
    """Derive a deterministic per-domain seed from the global SEED and domain name."""
    raw = f"{SEED}:{domain_name}".encode()
    return int(hashlib.sha256(raw).hexdigest(), 16) % (2**32)


def split_questions(
    questions: List[Dict[str, Any]],
    domain_name: str,
    public_ratio: float = PUBLIC_RATIO,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split questions into public and private subsets deterministically.

    Uses a per-domain seed so the result for each domain is independent of
    the number of domains, their processing order, or prior RNG consumption.
    """
    rng = random.Random(_domain_seed(domain_name))

    n = len(questions)
    indices = list(range(n))
    rng.shuffle(indices)

    split_at = int(n * public_ratio)
    public_idx = set(indices[:split_at])

    public_q = [q for i, q in enumerate(questions) if i in public_idx]
    private_q = [q for i, q in enumerate(questions) if i not in public_idx]

    return public_q, private_q


def copy_core_files(src_dir: Path, dst_dir: Path) -> None:
    """
    Copy core non-question files from src_dir to dst_dir.

    We intentionally copy only:
      - schema.sql
      - generate_data.py
      - generate_data_en.py
    to avoid propagating junk or generated artifacts (like data.sql).
    """
    dst_dir.mkdir(parents=True, exist_ok=True)

    for name in ("schema.sql", "generate_data.py", "generate_data_en.py"):
        src_file = src_dir / name
        if src_file.exists():
            shutil.copy2(src_file, dst_dir / name)


def process_domain(domain_dir: Path, public_root: Path, private_root: Path) -> None:
    """
    Process a single domain directory under databases/, splitting questions.json
    into public/private and copying schema & generator scripts.
    """
    domain_name = domain_dir.name  # e.g. "01_trading_company"

    # Output dirs
    public_dir = public_root / "databases" / domain_name
    private_dir = private_root / "databases" / domain_name

    # Copy core files to both splits
    copy_core_files(domain_dir, public_dir)
    copy_core_files(domain_dir, private_dir)

    # Split questions.json if present
    questions_path = domain_dir / "questions.json"
    if questions_path.exists():
        with questions_path.open("r", encoding="utf-8") as f:
            questions = json.load(f)

        public_q, private_q = split_questions(questions, domain_name)

        # Write split questions
        with (public_dir / "questions.json").open("w", encoding="utf-8") as f:
            json.dump(public_q, f, ensure_ascii=False, indent=2)

        with (private_dir / "questions.json").open("w", encoding="utf-8") as f:
            json.dump(private_q, f, ensure_ascii=False, indent=2)


def create_sample_submission(public_root: Path, private_root: Path) -> None:
    """
    Create public/sample_submission.csv with the expected columns:
    domain, id, predicted_sql

    Rows correspond to PRIVATE (test-set) questions — the same IDs that
    appear in answers.csv — so that grading the sample produces a valid
    (zero) score.  predicted_sql is filled with a placeholder to keep
    the column as string dtype when read by pandas.
    """
    db_root = private_root / "databases"
    rows: List[Tuple[str, int, str]] = []

    for q_path in sorted(db_root.glob("*/questions.json")):
        domain = q_path.parent.name
        with q_path.open("r", encoding="utf-8") as f:
            questions = json.load(f)
        for q in questions:
            qid = int(q["id"])
            rows.append((domain, qid, "SELECT 1"))

    out_path = public_root / "sample_submission.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "id", "predicted_sql"])
        writer.writerows(rows)


def create_answers(private_root: Path) -> None:
    """
    Create private/answers.csv with columns:
    domain, id, gold_sql

    Rows are generated for all questions contained in
    private/databases/*/questions.json.
    """
    db_root = private_root / "databases"
    rows: List[Tuple[str, int, str]] = []

    for q_path in sorted(db_root.glob("*/questions.json")):
        domain = q_path.parent.name
        with q_path.open("r", encoding="utf-8") as f:
            questions = json.load(f)
        for q in questions:
            qid = int(q["id"])
            gold_sql = q["gold_sql"]
            rows.append((domain, qid, gold_sql))

    out_path = private_root / "answers.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "id", "gold_sql"])
        writer.writerows(rows)


def prepare(dataset_dir: str, public_dir: str, private_dir: str) -> None:
    """
    Splits raw data under <dataset_dir>/databases into <public_dir> and <private_dir>.

    - <public_dir>/databases/<domain>/ contains schema + generators + a subset of questions.
    - <private_dir>/databases/<domain>/ contains schema + generators + complementary subset of questions.

    The split is deterministic: each domain uses an isolated random.Random
    instance seeded with a per-domain key derived from SEED + domain name.
    """

    root = Path(dataset_dir).resolve()
    databases_root = root / "databases"

    if not databases_root.exists():
        raise FileNotFoundError(f"'databases' directory not found at {databases_root}")

    public_root = Path(public_dir).resolve()
    private_root = Path(private_dir).resolve()

    # Clean existing outputs (optional; comment out if you prefer incremental)
    if public_root.exists():
        shutil.rmtree(public_root)
    if private_root.exists():
        shutil.rmtree(private_root)

    # Iterate over domain directories under databases/
    for domain_dir in sorted(databases_root.iterdir()):
        if domain_dir.is_dir():
            process_domain(domain_dir, public_root, private_root)

    # Create sample_submission.csv in the public root for grade validation
    create_sample_submission(public_root, private_root)
    # Create answers.csv in the private root for grading
    create_answers(private_root)


if __name__ == "__main__":
    # Default CLI behavior: use current directory as dataset root
    prepare(".", "public", "private")