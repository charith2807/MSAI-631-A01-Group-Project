# Team guide: who owns what

Ownership follows the effort assignments in the approved proposal and the extended design document. Every source file names its owner in its header docstring. Owners are the first reviewer for changes to their files; every member should be able to explain the *whole* system, so each section lists what to be ready to explain.

## Charith Reddy Mummadireddy Reddivari — architecture and integration
**Files:** `careerpath/config.py`, `models.py`, `engine.py`, `router.py`, `retriever.py`, `llm/*`, `ingestion/*`, `analysis/ats_check.py`, `analysis/gaps.py` (pipeline), `tailoring/*`, `export_docx.py`, `app.py`, most of `tests/`.
**Be ready to explain**
* Why a provider adapter (`llm/base.py`): one `complete()` interface, typed errors (rate limit, auth, timeout, unavailable, invalid response) that the UI turns into friendly messages; Groq, OpenRouter and Gemini share the OpenAI-compatible client, Anthropic uses its own SDK.
* How TF-IDF retrieval works (accent stripping, light stemming, bigrams, cosine score, threshold → fallback) and why no vector database.
* How the ATS-readiness score is built (weights from the design table, each failed rule shows evidence, reason and fix) and why it is labelled heuristic.
* Redaction → model → local re-attach of contact details; defence in depth in tailoring (prompt rules + deterministic checks + user review).
**Tests:** `tests/test_ingestion_ats.py`, `test_tailoring_export_engine.py`, `test_llm_config.py`.

## Dathan Neal — prompts and model evaluation
**Files:** `careerpath/prompts.py`, `jsonutil.py`, the prompt side of `analysis/jd_analyzer.py` and `analysis/gaps.py`, `evals/` (`harness.py`, `live.py`, `run_evals.py`, `data/qa_questions.json`, `data/grounding_cases.json`).
**Be ready to explain**
* Each prompt's rules (QA grounding in context only; JD → strict JSON; gap prompt must quote the résumé verbatim; tailoring immutability rules) and why prompts alone are not trusted.
* The evaluation design: what each suite measures, what the live run measures (JSON validity, context overlap, latency, error types, fabrication attempts, content preservation, job alignment), and how to read the model comparison.
* Limits of the evaluation (small hand-written sets, proxies such as token overlap, no human rating).
**Run:** `python -m evals.run_evals --live groq,anthropic,gemini`.

## Jangmu Sherpa — knowledge base, taxonomy, fixtures
**Files:** `knowledge_base/*.md` (six proposal topics + ATS guide + skills taxonomy), `careerpath/guard.py` (category patterns), `scripts/make_fixtures.py`, `tests/fixtures/`, `evals/data/gap_labels.json`, `evals/data/ats_labels.json`, `evals/data/guard_prompts.json`.
**Be ready to explain**
* How the knowledge base is structured (front matter topic/label, passages split at `##` headings) and how to add a topic.
* The taxonomy format (`canonical | aliases | related | learning suggestion`), why "related" decides *transferable*, and why loose relations (e.g. Pandas ↔ Python) were removed after the first gap evaluation.
* How labels were made independently of the code, and the caveat that constructed fixtures test rule correctness, not real-world coverage.
**Review duty:** retrieval-coverage review after each knowledge-base change (`python -m evals.run_evals`).

## Sisindri Rachakonda — interface, usability, documentation
**Files:** `careerpath/ui.py`, `messages.py`, `render.py`, `README.md`, `docs/results-report.md`.
**Be ready to explain**
* The HCI principles in the interface: visibility of system status (model/offline banner), transparency (every deduction shows evidence), user control (accept/reject each change, clear session), error prevention (file checks, rejected changes not exportable), recognition over recall (suggested questions), privacy (notice + acknowledgment before upload).
* Fallback and refusal wording (`messages.py`) and the design decision that unsafe or out-of-scope requests never reach the model.
* Usability study plan (5–8 classmates, synthetic data): **not yet run**, see the report's limitations.

## Working agreements
1. Branch per feature (`feature/<area>-<topic>`), pull request, one reviewer from another area.
2. `pytest` and `python -m evals.run_evals` pass before merging; paste changed metrics into the PR description.
3. Prompts, wording and knowledge-base text live in their own files so non-coders can edit them safely.
4. Secrets only in the local `.env`; synthetic data only in the repository.
5. Model names live in configuration; confirm availability in the provider console (a model that worked for one account returned "not found" on another during development).
