"""Run the evaluation suites and write results to evals/results/.

  python -m evals.run_evals                         # offline suites (no key needed)
  python -m evals.run_evals --live groq,anthropic,gemini   # also live runs (keys from .env)
"""
from __future__ import annotations

import argparse
import json
import os
import time

from dotenv import load_dotenv

from . import offline
from .harness import RESULTS


def md_offline(r: dict) -> str:
    a, g, k, p, gr, o = r["retrieval"], r["guard"], r["ats"], r["gaps"], r["grounding"], r["operations"]
    L = ["# Offline evaluation results", "", f"_Generated {time.strftime('%Y-%m-%d %H:%M')} - deterministic, no network._", "",
         "## Retrieval (Mode A)", "",
         f"- Threshold {a['threshold']}; {a['n_in_scope']} in-scope, {a['n_out_of_scope']} out-of-scope questions",
         f"- Top-1 topic accuracy: **{a['top1_topic_accuracy_pct']}%**",
         f"- In-scope questions answered (not falsely sent to fallback): **{a['in_scope_answered_pct']}%**",
         f"- Out-of-scope correctly sent to fallback: **{a['out_of_scope_fallback_pct']}%**", "",
         "| Topic | Correct |", "|---|---|"] + [f"| {t} | {v} |" for t, v in a["per_topic_accuracy"].items()]
    L += ["", "Threshold sweep:", "", "| Threshold | In-scope answered % | In-scope correct topic % | Out-of-scope fallback % |", "|---|---|---|---|"]
    L += [f"| {s['threshold']} | {s['in_scope_answered_pct']} | {s['in_scope_correct_topic_pct']} | {s['out_of_scope_fallback_pct']} |" for s in a["threshold_sweep"]]
    L += ["", "Wrong-topic questions:", ""] + [f"- “{m['q']}” → {m['got']} (expected {m['expected']}, score {m['score']})" for m in a["misses"]]
    L += ["", "Ambiguous questions:", ""] + [f"- “{m['q']}” → {'fallback' if m['fallback'] else m['got']} (score {m['score']})" for m in a["ambiguous"]]
    L += ["", "## Scope guard", "", f"- Refusal rate on excluded categories: **{g['refusal_rate_pct']}%** ({g['n_block']} prompts; correct category {g['correct_category_pct']}%)",
          f"- False-refusal rate on benign career prompts: **{g['false_refusal_rate_pct']}%** ({g['n_allow']} prompts)"]
    L += ["", "## ATS-readiness checker", "", f"- {k['fixtures']} synthetic fixtures; rule precision **{k['rule_precision_pct']}%**, recall **{k['rule_recall_pct']}%** (TP {k['tp']}, FP {k['fp']}, FN {k['fn']}, TN {k['tn']})",
          f"- Image-only PDF rejected with a clear message: **{k['image_only_rejected_with_message']}**", f"- Caveat: {k['caveat']}", "",
          "| Fixture | Expected failing rules | Got | Score |", "|---|---|---|---|"]
    L += [f"| {d['fixture']} | {', '.join(d['expected_fail']) or '-'} | {', '.join(d['got_fail']) or '-'} | {d['score']} |" for d in k["detail"]]
    L += ["", "## Skill-gap analysis (deterministic path)", "", f"- {p['pairs']} résumé×job pairs, {p['skill_labels']} hand-labelled skills: agreement **{p['agreement_pct']}%**",
          f"- Transferable claims backed by a verbatim résumé quotation: **{p['transferable_with_valid_quote_pct']}%** ({p['transferable_claims']} claims)",
          "- Keyword JD extraction found every labelled skill: " + ", ".join(f"{j['jd']} {j['found']}/{j['expected']}" for j in p["jd_keyword_extraction"]), "",
          "Confusion (label → predicted):", ""] + [f"- {lab}: {json.dumps(pred)}" for lab, pred in p["confusion_label_vs_predicted"].items()]
    L += ["", "Disagreements:", ""] + [f"- {d['resume']} × {d['jd']}: {d['skill']} labelled {d['label']}, predicted {d['predicted']}" for d in p["disagreements"]]
    L += ["", "## Grounding checks (fabrication detection)", "", f"- {gr['n_fabricated']} fabricated + {gr['n_clean']} faithful hand-written rewrites",
          f"- Fabrications caught (flagged or rejected): **{gr['fabrication_detection_pct']}%**; faithful rewrites wrongly flagged: **{gr['false_flag_rate_pct']}%**",
          "- Detection by type: " + ", ".join(f"{t} {v}" for t, v in gr["detection_by_type"].items()), "", "Missed:", ""]
    L += [f"- ({m['type']}) {m['proposed']}" for m in gr["missed_fabrications"]]
    L += ["", "## Local processing time (ms)", ""] + [f"- {k_}: {v}" for k_, v in o.items()]
    return "\n".join(L) + "\n"


def md_live(r: dict) -> str:
    q, j, t, o, g = r["qa"], r["jd_extraction"], r["tailoring"], r["operations"], r["gaps_llm"]
    L = [f"# Live evaluation: {r['provider']} / {r['model']}", "", f"_Run {r['started']}._", "", "## Mode A (Q&A)", "",
         f"- Answered by the model: {q['answered_by_model_pct']}% of {q['n']} in-scope questions; source label present {q['source_label_pct']}%; within 200 words {q['within_word_limit_pct']}%",
         f"- Mean overlap of answer with retrieved passage (relevance proxy): {q['mean_context_overlap']}",
         f"- Out-of-scope sent to fallback: {q['out_of_scope_fallback_pct']}%", "", "## JD extraction", "",
         f"- Valid JSON on first/second try (no keyword fallback): {j['json_valid_pct']}%"]
    L += [f"- {x['jd']}: precision {x['precision']}, recall {x['recall']}; extra {x['extra']}; missing {x['missing']}" for x in j["rows"]]
    L += ["", "## Gap analysis (model-assisted)", "", f"- Transferable claims: {g['transferable_claims']}; with verbatim résumé quote: {g['with_verbatim_quote_pct']}%",
          "", "## Tailoring", "", f"- {t['runs']} runs, {t['failed_runs']} failed (invalid/unusable output) → valid {t['json_valid_pct']}%",
          f"- Changes proposed: {t['changes_total']} → ok {t['pct_ok']}%, flagged {t['pct_flagged']}%, rejected by checks {t['pct_rejected_by_checks']}%",
          f"- Runs where model tried to add a skill the résumé lacks: {t['runs_where_model_tried_to_add_missing_skill']}; where it stayed exportable: {t['runs_where_missing_skill_stayed_exportable']}",
          f"- Content preservation (mean): {t['mean_content_preservation']}; job alignment before → after ok-changes: {t['mean_alignment_before']} → {t['mean_alignment_after']}",
          "", "## Operations", ""] + [f"- {k}: {v}" for k, v in o.items()]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", default="", help="comma list of providers: groq,anthropic,gemini,openrouter")
    ap.add_argument("--model", default="", help="override model (single provider only)")
    ap.add_argument("--pace", type=float, default=1.0, help="seconds between live calls")
    args = ap.parse_args()
    load_dotenv()
    RESULTS.mkdir(parents=True, exist_ok=True)

    res = offline.run_all()
    (RESULTS / "offline_results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "offline_results.md").write_text(md_offline(res), encoding="utf-8")
    print("offline: retrieval top-1 %s%%, guard refusal %s%% / false-refusal %s%%, ATS P/R %s/%s, gaps %s%%, grounding %s%%" % (
        res["retrieval"]["top1_topic_accuracy_pct"], res["guard"]["refusal_rate_pct"], res["guard"]["false_refusal_rate_pct"],
        res["ats"]["rule_precision_pct"], res["ats"]["rule_recall_pct"], res["gaps"]["agreement_pct"], res["grounding"]["fabrication_detection_pct"]))

    if args.live:
        from .live import run_live
        for prov in [p.strip() for p in args.live.split(",") if p.strip()]:
            try:
                r = run_live(prov, args.model or None, args.pace)
            except RuntimeError as e:
                print(f"live {prov}: skipped ({e})"); continue
            safe = r["model"].replace("/", "_").replace(":", "_")
            (RESULTS / f"live_{prov}_{safe}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
            (RESULTS / f"live_{prov}_{safe}.md").write_text(md_live(r), encoding="utf-8")
            print(f"live {prov}/{r['model']}: done; tailoring valid {r['tailoring']['json_valid_pct']}%, ops {r['operations']['latency_median_s']}s median")


if __name__ == "__main__":
    main()
