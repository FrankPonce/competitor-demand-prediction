"""Sprint 11 report: rules vs LLM vs fine-tuned students on the verified gold set.

    python -m src.skillmodel.report

Writes reports/skillmodel/summary.md, comparison.png, new_skill_candidates.csv and data/skillmodel/report.json.
Confidence intervals: 2,000 bootstrap resamples of the 200 gold sentences (paired, so system differences are
judged on the same resamples).
"""

from __future__ import annotations

import json
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from src.style import THEME, apply_matplotlib, footnote

from .evaluate import D, ROOT, gold, llm_predictions, load_jsonl, rule_predictions, score

OUT = ROOT / "reports" / "skillmodel"
B = 2000
NICE = {"rules": "Rules (Sprint 4 taxonomy)", "llm": "LLM (gpt-oss-120b, zero-shot)"}
# Candidate list hygiene (not used in any metric): company/product names and one-word generic heads are not
# useful taxonomy additions even when the student tags them.
NAMES = ("openai", "chatgpt", "anthropic", "claude", "nvidia", "google", "gemini", "codex", "xai", "grok")
NOT_SKILLS = {"data", "systems", "system", "software", "platform", "platforms", "infrastructure", "security", "cloud",
              "training", "architecture", "solutions", "tools", "technology", "technologies", "engineering",
              "communication", "compute", "metrics", "operations", "products", "models", "ai", "ml", "research"}


def systems() -> dict[str, dict[str, list[dict]]]:
    out = {"rules": rule_predictions(), "llm": llm_predictions()}
    res = json.loads((D / "results.json").read_text(encoding="utf-8"))
    for name in res:
        out[name] = {r["id"]: r["spans"] for r in load_jsonl(D / "preds" / f"{name}.jsonl")}
    return out


def bootstrap(g: dict, preds: dict[str, dict], mode: str = "overlap") -> dict[str, np.ndarray]:
    ids = list(g)
    rng = random.Random(11)
    draws = defaultdict(list)
    for _ in range(B):
        sample = [rng.choice(ids) for _ in ids]
        sub = {f"{k}-{i}": g[i] for k, i in enumerate(sample)}
        for name, p in preds.items():
            sp = {f"{k}-{i}": p.get(i, []) for k, i in enumerate(sample)}
            draws[name].append(score(sub, sp, mode)["f1"])
    return {k: np.array(v) for k, v in draws.items()}


def throughput(model_dir: Path, n: int = 1000) -> float:
    """Sentences per second for a saved student on this machine (GPU if available)."""
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    from .train import predict
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForTokenClassification.from_pretrained(model_dir).to(dev)
    rows = load_jsonl(D / "train_pool.jsonl")[:n]
    predict(model, tok, rows[:64], dev)  # warm-up
    if dev.type == "cuda":
        torch.cuda.synchronize()
    t = time.time()
    predict(model, tok, rows, dev, bs=64)
    if dev.type == "cuda":
        torch.cuda.synchronize()
    return n / (time.time() - t)


def new_skill_candidates(model_dir: Path, n: int = 5000) -> list[dict]:
    """Run the student over unseen sentences; keep frequent spans that no taxonomy rule matches."""
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    from src.skillmodel.data import rule_spans, sentences
    from .train import predict
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForTokenClassification.from_pretrained(model_dir).to(dev)
    gold_jobs = {r["job_id"] for r in load_jsonl(D / "gold_candidates.jsonl")}
    train_ids = {r["text"] for r in load_jsonl(D / "train_pool.jsonl")}
    df = sentences()
    df = df[~df.job_id.isin(gold_jobs) & ~df.text.isin(train_ids)].sample(n, random_state=11)
    rows = df.to_dict("records")
    preds = predict(model, tok, rows, dev, bs=64)
    count, companies, example = Counter(), defaultdict(set), {}
    for r, spans in zip(rows, preds):
        rules = rule_spans(r["text"])
        for s in spans:
            if any(s["start"] < q["end"] and q["start"] < s["end"] for q in rules):
                continue
            key = re.sub(r"\s+", " ", s["text"].strip()).lower()
            if len(key) < 3 or len(key.split()) > 5 or key in NOT_SKILLS or any(n in key for n in NAMES):
                continue
            count[key] += 1
            companies[key].add(r["company"])
            example.setdefault(key, r["text"])
    return [{"span": k, "mentions": c, "companies": len(companies[k]), "example": example[k]}
            for k, c in count.most_common() if c >= 3][:60]


def chart(rows: list[dict]) -> None:
    import matplotlib.pyplot as plt

    apply_matplotlib()
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    labels = [r["label"] for r in rows]
    x = np.arange(len(rows))
    w = 0.26
    cols = {"precision": "#58a6ff", "recall": "#d29922", "f1": "#e6edf3"}
    for k, (m, c) in enumerate(cols.items()):
        vals = [r[m] for r in rows]
        bars = ax.bar(x + (k - 1) * w, vals, w * 0.92, color=c, alpha=0.9 if m != "f1" else 1, label=m.upper() if m == "f1" else m.capitalize())
        if m == "f1":
            lo = [r["f1"] - r["ci"][0] for r in rows]
            hi = [r["ci"][1] - r["f1"] for r in rows]
            ax.errorbar(x + (k - 1) * w, vals, yerr=[lo, hi], fmt="none", ecolor=THEME["muted"], capsize=3, lw=1.2)
        for b, v, r in zip(bars, vals, rows):
            top = r["ci"][1] if m == "f1" else v  # F1 labels sit above the whisker
            ax.text(b.get_x() + b.get_width() / 2, top + 0.02, f"{v:.2f}", ha="center", fontsize=8.5,
                    color=THEME["text"] if m == "f1" else THEME["text2"], fontweight="bold" if m == "f1" else None)
    ax.set_xticks(x, labels)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("overlap match")
    ax.set_title("Skill-span extraction on 200 verified gold sentences")
    ax.legend(loc="upper left", ncol=3)
    footnote(fig, "F1 whiskers: 95% bootstrap interval (2,000 resamples). Overlap match forgives span-boundary choices. "
                  "Source: Sprint 11, src/skillmodel.")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "comparison.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    preds = systems()
    res = json.loads((D / "results.json").read_text(encoding="utf-8"))
    students = sorted(res, key=lambda k: -res[k]["verified_overlap"]["f1"])
    best = students[0]
    g, gs = gold("verified"), gold("strict")
    boot = bootstrap(g, preds)

    table = []
    for name in ["rules", "llm"] + students:
        r = {"system": name, "label": NICE.get(name, name.replace("skill-", "student: ")),
             **{f"{view}_{mode}": score(G, preds[name], mode) for view, G in (("verified", g), ("strict", gs))
                for mode in ("exact", "overlap")}}
        r["ci"] = [round(float(np.percentile(boot[name], 2.5)), 3), round(float(np.percentile(boot[name], 97.5)), 3)]
        if name in res:
            r.update({k: res[name][k] for k in ("train_sentences", "train_seconds", "labels", "base")})
        table.append(r)

    diff = {other: [round(float(np.percentile(boot[best] - boot[other], q)), 3) for q in (2.5, 50, 97.5)]
            for other in ("rules", "llm")}
    speed = throughput(ROOT / "models" / best)
    cands = new_skill_candidates(ROOT / "models" / best)
    llm_daily = len(load_jsonl(D / "train_pool.llm.gpt-oss-120b.jsonl"))

    chart([{"label": ["Rules", "LLM", "Student"][k], "precision": r["verified_overlap"]["precision"],
            "recall": r["verified_overlap"]["recall"], "f1": r["verified_overlap"]["f1"], "ci": r["ci"]}
           for k, r in enumerate([table[0], table[1], next(t for t in table if t["system"] == best)])])

    import csv
    with (OUT / "new_skill_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["span", "mentions", "companies", "example"])
        w.writeheader()
        w.writerows(cands)

    report = {"best_student": best, "table": table, "best_minus": diff, "student_sentences_per_second": round(speed),
              "llm_labels_collected": llm_daily, "new_skill_candidates": len(cands)}
    (D / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    def row(t):
        v, s = t["verified_overlap"], t["verified_exact"]
        return (f"| {t['label']} | {v['precision']:.2f} | {v['recall']:.2f} | **{v['f1']:.2f}** "
                f"({t['ci'][0]:.2f}–{t['ci'][1]:.2f}) | {s['f1']:.2f} | {t['strict_overlap']['f1']:.2f} |")
    md = [
        "# Skill-span extraction: rules vs LLM vs fine-tuned student",
        "",
        "_Generated by `python -m src.skillmodel.report`. Gold: 200 held-out sentences, 422 spans, verified by the "
        "project owner. Overlap match forgives boundary choices; exact match does not; \"strict\" removes 19 "
        "owner-added spans the guidelines exclude._",
        "",
        "| System | Precision | Recall | F1 (95% CI) | Exact F1 | Strict F1 |",
        "|---|---:|---:|---:|---:|---:|",
        *[row(t) for t in table],
        "",
        f"![comparison](comparison.png)",
        "",
        f"- Best student **{best}** vs rules: F1 difference {diff['rules'][1]:+.2f} "
        f"(95% CI {diff['rules'][0]:+.2f} to {diff['rules'][2]:+.2f}); vs LLM: {diff['llm'][1]:+.2f} "
        f"({diff['llm'][0]:+.2f} to {diff['llm'][2]:+.2f}).",
        f"- Speed: the student tags about **{speed:,.0f} sentences/second** on the laptop GPU; the free LLM tier "
        f"labelled {llm_daily:,} sentences before its daily limit.",
        f"- {len(cands)} frequent skill spans found by the student that no taxonomy rule matches: "
        "[new_skill_candidates.csv](new_skill_candidates.csv).",
    ]
    (OUT / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
