# GraphRAG

GraphRAG ingests CSV or Excel files, stores them in a local SQLite/NetworkX graph as row communities, and answers questions with Ollama using graph context.

## What The Graph Looks Like

For a dataset with 1000 rows, the builder creates 1000 row groups.

Each row group contains:

- one `RowGroup` / `Community` node
- one primary-key `PrimaryEntity` cell
- one `Cell` node for each non-empty column value
- bidirectional group membership links between the row group and every cell
- bidirectional `RELATED_IN_ROW` links between every pair of cells in that row

Rows that share the same exact column/value also get bidirectional cross-row links:

- `Cell -> SAME_VALUE_AS -> Cell`
- `RowGroup -> SHARES_VALUE_WITH -> RowGroup`

This lets a query find one value, recover the full row group, and also traverse to related row groups when values overlap.

## Project Layout

```text
.
|-- cli.py                         # Small runner for python cli.py
|-- README.md                      # Project documentation
|-- requirements.txt               # Python dependencies
|-- actual_vs_target_data.csv      # Sample/local data
|-- scripts/
|   |-- examples.py                # Optional example workflows
|   `-- utils.py                   # Optional helper scripts
`-- src/
    `-- graphrag_app/
        |-- app.py                 # Application orchestrator
        |-- cli.py                 # Interactive menu
        |-- config.py              # SQLite/Ollama configuration
        |-- ingestion/
        |   `-- data_ingestion.py
        |-- graph/
        |   `-- graph_builder.py
        |-- llm/
        |   `-- ollama.py
        `-- query/
            `-- query_engine.py
```

## Setup

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure Local Runtime

The application uses a local SQLite database and a local Ollama model.

**Step 1:** Copy the example environment file:

```powershell
cp .env.example .env
```

**Step 2:** Edit `.env` if you want to override the defaults:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b-instruct-q4_K_M
OLLAMA_FALLBACK_MODEL=qwen3:0.6b
OLLAMA_TIMEOUT=300
OLLAMA_NUM_CTX=8192
GRAPH_DB_PATH=graphrag_local.db
```

**Important Security Notes:**
- ✅ The `.env` file is **gitignored** and will NOT be committed to GitHub
- ✅ Never share or commit `.env` with real credentials
- ✅ Only commit `.env.example` with placeholder values
- ✅ Each developer/deployment should have their own `.env` file

### Ollama Model

Make sure Ollama is running and the model is available:

```powershell
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama pull qwen3:0.6b
```

## Run

```powershell
streamlit run cli.py
```

This launches the Streamlit interface in a separate browser window. Use the
Data tab to load a CSV/Excel file, the Graph tab to build or refresh the local
graph, and the Ask tab to view answers and metadata outside the terminal.

You can also launch the UI directly:

```powershell
streamlit run src/graphrag_app/streamlit_app.py
```

After changing graph logic, build with `clear_existing=True` so SQLite does not keep the older graph shape.

## Python Usage

```python
from src.graphrag_app import GraphRAGApplication

app = GraphRAGApplication()
app.ingest_file("actual_vs_target_data.csv")
app.build_graph(clear_existing=True)
result = app.answer_question("Show details for row A")
print(result["answer"])
app.close()
```

## Useful SQLite Checks

Confirm one row group per dataset row:

```sql
SELECT COUNT(*) FROM nodes WHERE labels LIKE '%RowGroup%';
```

Inspect one row group:

```sql
SELECT id, value, column, row_index, group_id
FROM nodes
WHERE labels LIKE '%Cell%'
LIMIT 50;
```

Inspect bidirectional column links:

```sql
SELECT source, target, type
FROM edges
WHERE type = 'RELATED_COLUMN'
ORDER BY source, target;
```

## Notes

- CSV and Excel files are supported.
- Primary key selection prefers identifier-like unique columns, then any unique column, then the first column.
- Short search terms are matched exactly to avoid noisy row retrieval.
- Dataset-wide questions such as totals, averages, lists, comparisons, trends, or "all rows" retrieve all row groups, not just the first few matches.
- The `graphrag/` directory in this workspace is a virtual environment, not the source package.
