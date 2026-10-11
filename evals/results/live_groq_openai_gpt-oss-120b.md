# Live evaluation: groq / openai/gpt-oss-120b

_Run 2026-10-11 14:28:57._

## Mode A (Q&A)

- Answered by the model: 94.3% of 35 in-scope questions; source label present 94.3%; within 200 words 100.0%
- Mean overlap of answer with retrieved passage (relevance proxy): 0.279
- Out-of-scope sent to fallback: 62.5%

## JD extraction

- Valid JSON on first/second try (no keyword fallback): 100.0%
- data_analyst: precision 1.0, recall 0.78; extra []; missing ['Communication', 'Data Analysis']
- software_engineer: precision 0.89, recall 0.89; extra ['CI/CD pipelines']; missing ['CI/CD']
- cloud_engineer_trap: precision 1.0, recall 1.0; extra []; missing []

## Gap analysis (model-assisted)

- Transferable claims: 27; with verbatim résumé quote: 100.0%

## Tailoring

- 15 runs, 1 failed (invalid/unusable output) → valid 93.3%
- Changes proposed: 102 → ok 98.0%, flagged 0.0%, rejected by checks 2.0%
- Runs where model tried to add a skill the résumé lacks: 0; where it stayed exportable: 0
- Content preservation (mean): 0.847; job alignment before → after ok-changes: 0.317 → 0.317

## Operations

- calls: 68
- ok: 66
- errors: {'LLMRateLimitError': 2}
- latency_median_s: 3.11
- latency_p90_s: 14.32
- latency_mean_s: 6.06
- input_tokens: 24331
- output_tokens: 26344
