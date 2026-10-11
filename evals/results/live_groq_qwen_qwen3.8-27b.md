# Live evaluation: groq / qwen/qwen3.8-27b

_Run 2026-10-11 14:37:37._

## Mode A (Q&A)

- Answered by the model: 94.3% of 35 in-scope questions; source label present 94.3%; within 200 words 100.0%
- Mean overlap of answer with retrieved passage (relevance proxy): 0.399
- Out-of-scope sent to fallback: 62.5%

## JD extraction

- Valid JSON on first/second try (no keyword fallback): 100.0%
- data_analyst: precision 0.89, recall 0.89; extra ['Communication skills']; missing ['Communication']
- software_engineer: precision 0.89, recall 0.89; extra ['CI/CD pipelines']; missing ['CI/CD']
- cloud_engineer_trap: precision 1.0, recall 1.0; extra []; missing []

## Gap analysis (model-assisted)

- Transferable claims: 20; with verbatim résumé quote: 100.0%

## Tailoring

- 15 runs, 0 failed (invalid/unusable output) → valid 100.0%
- Changes proposed: 8 → ok 50.0%, flagged 12.5%, rejected by checks 37.5%
- Runs where model tried to add a skill the résumé lacks: 0; where it stayed exportable: 0
- Content preservation (mean): 0.915; job alignment before → after ok-changes: 0.297 → 0.297

## Operations

- calls: 69
- ok: 69
- errors: {}
- latency_median_s: 2.83
- latency_p90_s: 13.37
- latency_mean_s: 5.56
- input_tokens: 22084
- output_tokens: 9661
