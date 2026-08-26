# Professional Demo

The demo is a self-contained showcase of the Enterprise Knowledge Platform. It uses synthetic Persian enterprise knowledge and does not require an API key, an external LLM, or a downloaded embedding model.

The demo image uses `requirements-demo.txt`, deliberately excluding Torch, sentence-transformers, and FAISS. This keeps the evaluator download substantially smaller while the full production-oriented dependency set remains available through `requirements.txt`.

## Start in one command

```bash
docker compose -f compose.demo.yml up --build
```

Without Docker, use the existing virtual environment:

```powershell
.\scripts\run-demo-local.ps1
```

On Linux or macOS:

```bash
sh scripts/run-demo-local.sh
```

The local launcher isolates all demo state under the ignored `.demo/` directory and shuts down the background API when the UI process exits.

Open:

- Demo UI: <http://localhost:8501>
- API documentation: <http://localhost:8000/docs>
- Health endpoint: <http://localhost:8000/health>

The first startup seeds five synthetic knowledge records across maintenance, human resources, information security, supply chain, and IT operations. Four records are published and one remains in the review queue to demonstrate the governance workflow.

## Recommended five-minute walkthrough

1. Open **Dashboard** and review the publication, review-queue, document, and gap indicators.
2. Open **Review**, inspect the pending infrastructure-migration lesson, and approve or request changes.
3. Open **Knowledge Map** to inspect domains, extracted entities, and governed relations.
4. Open **Search & RAG**, select a suggested question, and inspect the answer, relevance score, and source records.
5. Open **Audit** to show that capture, review, upload, and publication events are traceable.

## Demo guarantees

- All seeded records are fictional and safe to publish.
- Seeding is idempotent; restarting containers does not duplicate records.
- Demo answers are deterministic and generated locally from published records.
- No external AI request is performed while `DEMO_MODE=true`.
- Unpublished knowledge is excluded from demo retrieval and the public knowledge map.

## Reset the demo

This command deletes only the named volumes created by `compose.demo.yml`:

```bash
docker compose -f compose.demo.yml down --volumes
```

Run the start command again to obtain a clean seeded environment.

## Custom ports

```powershell
$env:DEMO_UI_PORT = "8601"
$env:DEMO_API_PORT = "8100"
docker compose -f compose.demo.yml up --build
```

## Important scope statement

Demo Mode is designed for product walkthroughs and repository evaluation. It is not a security boundary and must not be exposed as a production service. Authentication, RBAC, retrieval-time access filtering, hardened uploads, and production persistence remain required before operational deployment. See [SECURITY.md](SECURITY.md).
