# Offline evaluation results

_Generated 2026-10-11 15:21 - deterministic, no network._

## Retrieval (Mode A)

- Threshold 0.12; 35 in-scope, 8 out-of-scope questions
- Top-1 topic accuracy: **82.9%**
- In-scope questions answered (not falsely sent to fallback): **94.3%**
- Out-of-scope correctly sent to fallback: **62.5%**

| Topic | Correct |
|---|---|
| Résumé Improvement | 3/5 |
| Interview Preparation | 5/5 |
| Job Search Planning | 3/5 |
| Networking | 5/5 |
| Skill Development | 4/5 |
| Career Transitions | 5/5 |
| ATS Formatting | 4/5 |

Threshold sweep:

| Threshold | In-scope answered % | In-scope correct topic % | Out-of-scope fallback % |
|---|---|---|---|
| 0.08 | 100.0 | 82.9 | 62.5 |
| 0.1 | 100.0 | 82.9 | 62.5 |
| 0.12 | 94.3 | 80.0 | 62.5 |
| 0.14 | 88.6 | 77.1 | 62.5 |
| 0.16 | 82.9 | 74.3 | 75.0 |
| 0.18 | 71.4 | 62.9 | 75.0 |
| 0.2 | 62.9 | 54.3 | 100.0 |
| 0.25 | 45.7 | 42.9 | 100.0 |

Wrong-topic questions:

- “How do I write good bullet points with action verbs?” → ATS Formatting (expected Résumé Improvement, score 0.247)
- “How long should my resume be?” → Skill Development (expected Résumé Improvement, score 0.119)
- “How should I plan my job search?” → Résumé Improvement (expected Job Search Planning, score 0.129)
- “Where can I find job openings?” → Résumé Improvement (expected Job Search Planning, score 0.141)
- “How do I build a project to show employers my skills?” → Career Transitions (expected Skill Development, score 0.209)
- “Will an applicant tracking system reject my resume?” → Job Search Planning (expected ATS Formatting, score 0.378)

Ambiguous questions:

- “Help me with my career.” → Job Search Planning (score 0.134)
- “What should I do next?” → fallback (score 0.0)
- “Tell me about interviews and resumes.” → Interview Preparation (score 0.209)
- “I feel stuck.” → Interview Preparation (score 0.149)

## Scope guard

- Refusal rate on excluded categories: **100.0%** (14 prompts; correct category 100.0%)
- False-refusal rate on benign career prompts: **0.0%** (12 prompts)

## ATS-readiness checker

- 11 synthetic fixtures; rule precision **100.0%**, recall **100.0%** (TP 8, FP 0, FN 0, TN 82)
- Image-only PDF rejected with a clear message: **True**
- Caveat: Fixtures are constructed to trigger one rule each, so this checks rule correctness, not real-world coverage.

| Fixture | Expected failing rules | Got | Score |
|---|---|---|---|
| clean.txt | - | - | 100 |
| clean.docx | - | - | 100 |
| clean.pdf | - | - | 100 |
| two_column.pdf | Single-column reading order | Single-column reading order | 83 |
| table_layout.docx | No tables or text boxes holding core content | No tables or text boxes holding core content | 92 |
| header_contact.docx | Contact details appear in the body | Contact details appear in the body | 92 |
| creative_headings.txt | Standard section headings found | Standard section headings found | 83 |
| mixed_dates.txt | Consistent date format | Consistent date format | 96 |
| no_bullets.txt | Bullets begin with action verbs, Bullets include numbers or concrete results | Bullets begin with action verbs, Bullets include numbers or concrete results | 83 |
| too_short.txt | Reasonable length (one to two pages) | Reasonable length (one to two pages) | 96 |

## Skill-gap analysis (deterministic path)

- 15 résumé×job pairs, 130 hand-labelled skills: agreement **98.5%**
- Transferable claims backed by a verbatim résumé quotation: **100.0%** (14 claims)
- Keyword JD extraction found every labelled skill: data_analyst 9/9, software_engineer 9/9, cloud_engineer_trap 8/8

Confusion (label → predicted):

- matched: {"matched": 41}
- transferable: {"transferable": 12}
- missing: {"missing": 75, "transferable": 2}

Disagreements:

- priya_nair_new_grad × data_analyst: Data Analysis labelled missing, predicted transferable
- aisha_khan_devops × cloud_engineer_trap: Terraform labelled missing, predicted transferable

## Grounding checks (fabrication detection)

- 20 fabricated + 20 faithful hand-written rewrites
- Fabrications caught (flagged or rejected): **85.0%**; faithful rewrites wrongly flagged: **0.0%**
- Detection by type: new_skill 6/6, number_change 4/4, new_number 3/3, invented_entity 4/4, semantic_inflation 0/3

Missed:

- (semantic_inflation) Led Agile sprints with 5 engineers to ship a reporting tool
- (semantic_inflation) Presented data analysis findings to regional managers, transforming communication between stores and head office
- (semantic_inflation) Directed the buyers' team using Excel forecasting models

## Local processing time (ms)

- index_build_ms: 1.7
- retrieval_query_ms: 0.24
- ats_check_ms: 0.16
- gap_analysis_ms: 0.54
- pdf_ingestion_ms: 9.86
