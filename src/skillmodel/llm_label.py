"""Label skill spans with a free LLM (Groq), following docs/skill-labelling-guidelines.md.

Resumable: results are appended to <input>.llm.<model>.jsonl and sentences already labelled are skipped, so the
free tier's daily token budget (about 200k tokens/day for gpt-oss-120b) can be spread over several runs.

Run: python -m src.skillmodel.llm_label data/skillmodel/gold_candidates.jsonl [--model openai/gpt-oss-120b] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from src import llm

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "docs" / "skill-labelling-guidelines.md").read_text(encoding="utf-8")
GUIDE = GUIDE.split("Gold labels were")[0]  # the provenance note is not an instruction
BATCH = 10

SYSTEM = ("You annotate job-posting sentences for skill spans. Follow the guidelines exactly. Copy every span "
          "character-for-character from the sentence (same case, same punctuation). Do not paraphrase, do not "
          "merge separate list items, do not label anything the guidelines exclude. Answer with one JSON object.\n\n"
          + GUIDE)


def locate(text: str, spans: list[str]) -> list[dict]:
    """Map span strings to character offsets: left to right, non-overlapping, exact match then case-insensitive."""
    out, taken = [], []
    for sp in spans:
        sp = str(sp).strip().strip(".,;:")
        if not sp:
            continue
        hit = None
        for flags in (0, re.I):
            for m in re.finditer(re.escape(sp), text, flags):
                if all(m.end() <= s or m.start() >= e for s, e in taken):
                    hit = m
                    break
            if hit:
                break
        if hit:
            taken.append((hit.start(), hit.end()))
            out.append({"start": hit.start(), "end": hit.end(), "text": text[hit.start():hit.end()]})
    return sorted(out, key=lambda x: x["start"])


def label_batch(batch: list[dict], model: str) -> dict[str, list[dict]] | None:
    import os
    os.environ["LLM_MODEL"] = model
    prompt = {"task": "List the skill spans in each sentence.",
              "output_schema": {"labels": [{"id": "<sentence id>", "spans": ["<exact substring>", "..."]}]},
              "sentences": [{"id": r["id"], "text": r["text"]} for r in batch]}
    res = llm.chat_json(SYSTEM, json.dumps(prompt, ensure_ascii=False), max_tokens=3000, temperature=0.0)
    if not res:
        return None
    obj, _ = res
    by_id = {r["id"]: r for r in batch}
    out = {}
    for item in obj.get("labels", []):
        sid = item.get("id")
        if sid in by_id and isinstance(item.get("spans"), list):
            out[sid] = locate(by_id[sid]["text"], item["spans"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--model", default="openai/gpt-oss-120b")
    ap.add_argument("--limit", type=int, default=None, help="label at most N new sentences this run")
    a = ap.parse_args()
    src = Path(a.path)
    out = src.with_suffix(f".llm.{a.model.split('/')[-1]}.jsonl")
    done = {json.loads(l)["id"] for l in out.open(encoding="utf-8")} if out.exists() else set()
    todo = [r for r in map(json.loads, src.open(encoding="utf-8")) if r["id"] not in done]
    if a.limit:
        todo = todo[:a.limit]
    print(f"{len(done)} already labelled, {len(todo)} to go → {out.name}")
    n = 0
    with out.open("a", encoding="utf-8") as f:
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            got = label_batch(batch, a.model)
            if got is None:
                print("LLM unavailable (rate limit or daily budget?); stopping, rerun later to resume")
                break
            for r in batch:
                if r["id"] in got:
                    f.write(json.dumps({"id": r["id"], "spans": got[r["id"]]}, ensure_ascii=False) + "\n")
                    n += 1
            f.flush()
            print(f"  {n} labelled", flush=True)
            time.sleep(8)  # stay under the tokens-per-minute limit
    print(f"done: {n} new labels")


if __name__ == "__main__":
    main()
