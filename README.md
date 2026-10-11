# CareerPath Guide

LLM-assisted career-preparation chatbot — **Group 7**, MSAI-631-A01 *Artificial Intelligence for Human-Computer Interaction* (University of the Cumberlands).

| Member | Primary area |
|---|---|
| Charith Reddy Mummadireddy Reddivari | Technical architecture, provider adapters, ingestion, ATS engine, export, tests |
| Dathan Neal | Prompt design, model evaluation, fabrication measurement |
| Jangmu Sherpa | Knowledge base, skills taxonomy, scope-guard coverage, synthetic fixtures and labels |
| Sisindri Rachakonda | Gradio interface, HCI/usability, user-facing wording, documentation |

Details of who owns what: [`docs/TEAM_GUIDE.md`](docs/TEAM_GUIDE.md). Project write-up: [`docs/results-report.md`](docs/results-report.md).

## What it does

* **Mode A – Career Q&A.** Ask about résumés, interviews, job search, networking, skills or career change. The app retrieves the best passage from a small Markdown knowledge base with **TF-IDF**, has an LLM write a short answer from that passage, and labels it with its **source topic**. Out-of-scope questions get a clear fallback; legal, medical, financial and mental-health advice, job guarantees, scraping and auto-applying are refused *without* calling the model.
* **Mode B – Résumé Studio.** Upload a résumé (PDF/DOCX/TXT, session memory only) and paste a job description to get an **ATS-readiness report** (transparent heuristic rules), a **skill-gap report** (matched / transferable with quoted evidence / missing, with learning suggestions) and an optional **grounded tailored résumé** you accept or reject change by change before exporting a single-column DOCX.

## Quick start (for the evaluator)

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # then edit .env: set LLM_PROVIDER and the matching key
python app.py                        # open http://127.0.0.1:7860
```

In `.env`, set **one** provider and its key:

| `LLM_PROVIDER` | Key variable | Default `LLM_MODEL` (override in `.env`) |
|---|---|---|
| `groq` (default) | `GROQ_API_KEY` | `openai/gpt-oss-120b` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-5` |
| `gemini` | `GEMINI_API_KEY` | `gemini-2.5-flash` |
| `openrouter` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct:free` |

Model names change and depend on your account: if you see *"The selected model or provider is unavailable"*, set `LLM_MODEL` to a model listed in your provider console.

**No key? It still runs.** Without a key the app starts in *offline mode*: Q&A returns the retrieved passage directly, and the ATS check and skill-gap analysis work (they are rule-based). Only model-written answers, model-assisted job-description extraction and résumé tailoring need a key.

Try: *"How do I prepare for a behavioral interview?"*, then tick the privacy box, upload `tests/fixtures/resumes/maya_chen_data_analyst.txt`, paste `tests/fixtures/jds/data_analyst.txt`, press **Analyse**, then **Tailor résumé**.
All fixture people and companies are fictional.

## Tests and evaluations

```bash
pip install -r requirements-dev.txt
pytest                                        # 54 tests, no network or key needed

python -m evals.run_evals                     # offline suites (no key) -> evals/results/offline_results.md
python -m evals.run_evals --live groq         # + live model run (needs the key in .env)
python -m evals.run_evals --live groq,anthropic,gemini --pace 2
python -m evals.run_evals --live groq --model qwen/qwen3.8-27b
```

Results are written to `evals/results/` (JSON + Markdown). The report's tables are built from those files (`python scripts/build_report.py`).

## Repository layout

```
app.py                     entry point (Gradio)
careerpath/
  config.py                env/.env settings
  engine.py                orchestration: routes to Mode A / Mode B
  router.py  guard.py      rule-based intent routing and scope guard
  retriever.py             TF-IDF over knowledge_base/
  prompts.py               every system prompt (one place)
  messages.py  render.py   user-facing wording and Markdown rendering
  ui.py                    Gradio Blocks interface
  ingestion/               PDF/DOCX/TXT loading, redaction, sectioning
  analysis/                ats_check, jd_analyzer, gaps, taxonomy
  tailoring/               tailor (LLM) + grounding (deterministic checks)
  llm/                     base interface + Groq/OpenRouter/Gemini (OpenAI-compatible) + Anthropic + fake
  export_docx.py           ATS-friendly DOCX export
knowledge_base/            curated Markdown topics, ATS guide, skills taxonomy
tests/                     pytest; synthetic fixtures in tests/fixtures/
evals/                     evaluation data, suites, results
scripts/                   fixture generator, report builder, submission-zip builder
docs/                      proposal, design document, results report (.md + .docx), team guide
docs/screenshots/          application screenshots used in the report (git only; not in the submission zip)
```

## Results and documents

* Results report: [`docs/results-report.md`](docs/results-report.md) and the Word version `docs/Group_7_CareerPath_Guide_Results_Report.docx` (includes application screenshots). The zip copy of the `.md` omits the images, so its figure links are blank; use the `.docx` to see them.
* Raw evaluation output: `evals/results/offline_results.{json,md}` and `evals/results/live_*.{json,md}` (Groq `openai/gpt-oss-120b` and `qwen/qwen3.8-27b`, synthetic data only).
* Design document and proposal: `docs/`.
* Headline offline results: retrieval top-1 82.9%, guard refusal 100% (0% false refusals), ATS rules 100%, skill-gap agreement 98.5%, grounding checks 85%. 54 tests pass without network access.

## Building the submission zip

```bash
python scripts/make_submission_zip.py   # -> dist/CareerPath_Guide_Group7_Source.zip
```

The zip contains source, tests, knowledge base, docs and evaluation results. It excludes `.env` and API keys, `.venv`, caches, `.git`, build output and all image files. After unzipping, follow the Quick start above (create your own `.env` from `.env.example`).

## Privacy and limits

* Résumé text is held in memory for the browser session only; nothing is logged. Name, email, phone and links are replaced by placeholders before any model call and re-attached locally on export. The user must tick an acknowledgment before the first upload.
* One deliberate exception: the exported DOCX must exist as a temporary file so the browser can download it. It is only created when you press **Export**.
* The ATS score is a heuristic, not any vendor's algorithm. The tool never invents résumé content: model rewrites pass deterministic grounding checks and a human review step. It gives no guarantee of interviews or offers.
* Never commit `.env` or real résumés (both are git-ignored).

## Development workflow

Short-lived feature branches, pull requests reviewed by at least one other member, `pytest` must pass before merging. See [`docs/TEAM_GUIDE.md`](docs/TEAM_GUIDE.md).

## AI-tool disclosure

AI coding assistants were used to help draft code, tests and documentation, as stated in the project proposal. All outputs were reviewed by the team.
