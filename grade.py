import sys

import pandas as pd


def normalize_sql(s: str) -> str:
    """Lowercase and normalize whitespace for exact-match comparison."""
    return " ".join(str(s).strip().lower().split())


def grade(submission: pd.DataFrame, answers: pd.DataFrame) -> float:
    """
    Compute a single float score in [0, 1] as the average Exact Match (EM)
    over all questions in answers.

    Parameters
    ----------
    submission : pd.DataFrame
        Columns: domain, id, predicted_sql
    answers : pd.DataFrame
        Columns: domain, id, gold_sql

    Returns
    -------
    float
        Fraction of questions where normalised predicted_sql == normalised gold_sql.
        Missing or empty predictions count as incorrect.
    """
    # Defensive: always return a float no matter what
    try:
        submission = submission.copy()
        answers = answers.copy()

        submission["domain"] = submission["domain"].astype(str)
        answers["domain"] = answers["domain"].astype(str)
        submission["id"] = submission["id"].astype(int)
        answers["id"] = answers["id"].astype(int)
        submission["predicted_sql"] = submission["predicted_sql"].fillna("").astype(str)
        answers["gold_sql"] = answers["gold_sql"].fillna("").astype(str)

        merged = answers.merge(
            submission[["domain", "id", "predicted_sql"]],
            how="left",
            on=["domain", "id"],
        )
        merged["predicted_sql"] = merged["predicted_sql"].fillna("")

        total = len(merged)
        if total == 0:
            return 1e-10

        correct = sum(
            1
            for _, row in merged.iterrows()
            if row["predicted_sql"].strip() != ""
            and normalize_sql(row["predicted_sql"]) == normalize_sql(row["gold_sql"])
        )

        score = float(correct) / float(total)
        return score if score > 0 else 1e-10
    except Exception:
        return 1e-10


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sub_path, ans_path = sys.argv[1], sys.argv[2]
    elif len(sys.argv) == 2:
        sub_path = sys.argv[1]
        ans_path = "private/answers.csv"
    else:
        print("Usage: python grade.py submission.csv [answers.csv]", file=sys.stderr)
        sys.exit(1)

    sub_df = pd.read_csv(sub_path)
    ans_df = pd.read_csv(ans_path)
    score = grade(sub_df, ans_df)
    print(score)
