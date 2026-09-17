# Text2SQL: Assignment for Students

## Competition on Building a Natural Language to SQL Conversion System

---

## 📋 Description

You need to develop a **Text2SQL system** — a model or pipeline that converts questions in natural language (Russian) into correct SQL queries for given relational databases.

The system should take as input:
- **Question** in natural language (e.g., "How many orders were placed in 2023?")
- **Database schema** (list of tables, columns, types, foreign keys)

And return as output:
- **SQL query** that, when executed on the corresponding database, returns the correct answer to the question.

---

## 🗄️ Dataset

We provide **5 domain databases** with realistic, multi-table schemas and large volumes of synthetic data for 2020–2025:

| # | Domain | Description | Tables | Questions |
|---|--------|-------------|--------|-----------|
| 1 | **Trading company** | B2B/B2C, products, orders, warehouses, suppliers | 24 | 100 |
| 2 | **Law firm** | Cases, clients, lawyers, invoices, hearings | 22 | 100 |
| 3 | **Logistics company** | Shipments, routes, transport, tracking | 21 | 100 |
| 4 | **Mining company** | Mines, extraction, processing, contracts | 20 | 100 |
| 5 | **Oil production company** | Fields, wells, production, liftings | 21 | 100 |

### Directory Structure

All databases live under the `databases/` directory:

```text
databases/
├── 01_trading_company/
├── 02_legal_firm/
├── 03_logistics_company/
├── 04_mining_company/
└── 05_oil_company/
```

Each domain directory contains:

- `schema.sql` — DDL (table and column definitions, data types, keys, constraints)
- `generate_data.py` — Russian synthetic data generator (writes `data.sql`)
- `generate_data_en.py` — English synthetic data generator (writes `data.sql`)
- `questions.json` — 100 questions with gold SQL answers

Format of `questions.json`:
```json
[
  {
    "id": 1,
    "question": "How many orders are there in 2023?",
    "gold_sql": "SELECT COUNT(*) FROM sales_orders WHERE EXTRACT(YEAR FROM order_date) = 2023;"
  },
  ...
]
```

The full list of tables, columns, and data types for each domain is defined in the corresponding `schema.sql` file and summarized in the dataset card.

---

## 📊 Evaluation Metrics

### 1. **Execution Accuracy (EX)**
Share of questions for which the **executed** generated SQL returns the same result as the gold query.

- **Formula:** `EX = (number of result-correct queries) / (total number of questions)`
- **Importance:** High. Main correctness metric.

### 2. **Exact Match (EM)**
Share of questions for which the generated SQL **textually matches** the gold query (taking into account normalization of whitespace, case, and order).

- **Formula:** `EM = (number of exact matches) / (total number of questions)`
- **Note:** Strict metric; different syntactically equivalent queries are not counted.

### 3. **Jaccard Similarity (JD)**
Measure of similarity between the token sets (tables, columns, SQL keywords) of the predicted and gold queries.

- **Formula:** `Jaccard = |A ∩ B| / |A ∪ B|`, where A, B are token sets.
- **Use:** Evaluates semantic closeness of queries even when the exact text differs.

### 4. **Latency (response time)**
Average time from receiving the question to producing SQL (in milliseconds).

- **Condition:** Measured on CPU; batch size = 1.
- **Goal:** Assess suitability of the system for interactive use.

### 5. **Valid SQL Rate (VSR)**
Share of generated queries that are **syntactically valid** SQL and execute without errors.

- **Formula:** `VSR = (number of valid queries) / (total number of questions)`
- **Use:** Basic assessment of the model’s "operability".

### 6. **Test Suite Accuracy (TSA)** *(optional)*
For a subset of questions, evaluation on a **set of test databases** with different data but the same schema. This measures how well the model generalizes rather than overfits to specific data.

---

## 🏆 Final Score

For each database separately we compute:

- `EX_d`, `EM_d`, `VSR_d`, `Jaccard_d` — metrics on that domain in \[0, 1\]
- `Latency_d` — mean latency (ms) of your system on that domain (batch size = 1)

Latency is normalized per-domain across all submissions using min–max scaling:

```text
normLatency_d = 0                          if L_max_d == L_min_d
normLatency_d = (L_d - L_min_d) / (L_max_d - L_min_d)  otherwise
```

The per-domain composite score is:

```text
Score_d = 0.50 × EX_d
        + 0.20 × Jaccard_d
        + 0.15 × VSR_d
        + 0.10 × EM_d
        - 0.05 × normLatency_d
```

The final score is the unweighted mean over the 5 databases:

```text
FinalScore = (Score_trading + Score_legal + Score_logistics + Score_mining + Score_oil) / 5
```

**Priority:** Execution Accuracy is the main criterion; the other metrics help distinguish teams with similar EX and reward robust, valid, and efficient systems.

---

## 📁 Solution Structure

Expected repository/archive structure:

```text
solution/
├── README.md                 # Description of approach, dependencies, how to run
├── requirements.txt          # Python dependencies
├── config.yaml               # Configuration (optional)
├── src/
│   ├── model.py              # Model / inference
│   ├── schema_encoder.py     # DB schema encoding
│   └── evaluator.py          # Evaluation script
├── inference.py              # Entry point: question + schema → SQL
└── evaluate.py               # Run evaluation on the test set
```

### Interface

**Input (inference):**
- `question`: string (question in Russian)
- `schema`: JSON or path to `schema.sql` (or structured description of tables/columns)
- `db_path`: path to SQLite/PostgreSQL (for execution check)

**Output:**
- `predicted_sql`: string with the SQL query

---

## ⚙️ Rules and Constraints

1. **Allowed approaches:**
   - Fine-tuned LLM (GPT, LLaMA, Codex, CodeLlama, etc.)
   - Seq2Seq (T5, BART)
   - Specialized Text2SQL models (T5-3B, RESDSQL, etc.)
   - Hybrid (retrieval + generation, rule-based preprocessing)

2. **Constraints:**
   - Only **open** pre-trained models and datasets are allowed.
   - It is forbidden to use gold SQL from the test set for training (no data leakage).
   - It is allowed to train on **other** Text2SQL datasets (Spider, WikiSQL, RuBQ, etc.).

3. **Runtime environment:**
   - PostgreSQL 14+ or SQLite 3.
   - Python 3.9+.
   - Evaluation is performed on the provided server with memory limits (16 GB RAM, GPU if needed).

---

## 📅 Stages

| Stage | Description | Timeframe |
|-------|-------------|-----------|
| 1 | Assignment release, data access | Day 1 |
| 2 | Development and debugging | 2–3 weeks |
| 3 | Submission of solution (code + short report) | Day N |
| 4 | Evaluation on hidden test set | Day N+1 |
| 5 | Publication of results and review | Day N+2 |

---

## 📤 Submission

Your **primary submission** for automatic grading is a CSV file with one row per question in the public split:

- **Filename:** `submission.csv`
- **Columns:**
  - `domain` — string, domain directory name (e.g. `01_trading_company`)
  - `id` — integer, question ID from `questions.json`
  - `predicted_sql` — string, your predicted SQL query

Example:

```text
domain,id,predicted_sql
01_trading_company,1,SELECT COUNT(*) FROM sales_orders WHERE EXTRACT(YEAR FROM order_date)=2023;
02_legal_firm,10,SELECT status, COUNT(*) FROM cases GROUP BY status;
```

In addition to the CSV, you should also provide for offline review:

1. **Archive** with code (without model weights >500MB — only a link to HuggingFace/other storage).
2. **Report** (2–4 pages): approach, architecture, experiments, validation results.
3. **Instructions** for running your system and reproducing results.

---

## 📚 Recommended Resources

- [Spider: A Large-Scale Human-Labeled Dataset for Text-to-SQL](https://yale-lily.github.io/spider)
- [RESDSQL: Decoupling Schema Linking and Skeleton Parsing for Text-to-SQL](https://github.com/RUCKBReasoning/RESDSQL)
- [BIRD: A Big Bench for Large-Scale Database Grounded Text-to-SQL](https://bird-bench.github.io/)
- [RuBQ 2.0: Russian Dataset for Question-Answering over DBpedia](https://github.com/TruePositiveRu/rubq)

---

## ❓ FAQ

**Q: Can we use GPT-4 / Claude via API?**  
A: Yes, but you must specify cost and limits in the report. A local model may be used for the final evaluation.

**Q: Do we need to support all 5 databases?**  
A: Yes. Evaluation is performed separately for each database; the final score is the average over databases (or weighted).

**Q: What if the SQL executes with an error?**  
A: Execution Accuracy for that example = 0. It is recommended to add validation and fallback (e.g., a simplified query).

**Q: Is row order in the result taken into account?**  
A: When comparing results, sorting by all columns before comparison is allowed (ORDER BY all columns).

---

*Good luck with your development! 🚀*

