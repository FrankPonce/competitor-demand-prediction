"""Fine-tune a token classifier (BIO tags) for skill spans, then score it on the gold set (Sprint 11).

    python -m src.skillmodel.train --labels llm            # LLM-labelled sentences (teacher → student)
    python -m src.skillmodel.train --labels rules          # Sprint 4 rule spans on all 3,000 sentences
    python -m src.skillmodel.train --labels union          # LLM ∪ rules on the LLM-labelled sentences

Model weights go to models/skill-<labels>-<base>/ (gitignored); predictions on the gold set go to
data/skillmodel/preds/ and metrics to data/skillmodel/results.json. Uses the GPU with fp16 when available.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForTokenClassification, AutoTokenizer, get_linear_schedule_with_warmup

from .evaluate import D, ROOT, gold, load_jsonl, score

LABELS = ["O", "B-SKILL", "I-SKILL"]
SEED = 11


def training_rows(kind: str) -> list[dict]:
    pool = {r["id"]: r for r in load_jsonl(D / "train_pool.jsonl")}
    llm_path = D / "train_pool.llm.gpt-oss-120b.jsonl"
    llm = {r["id"]: r["spans"] for r in load_jsonl(llm_path)} if llm_path.exists() else {}
    if kind == "rules":
        return [{"text": r["text"], "spans": r["rule_spans"]} for r in pool.values()]
    if kind == "llm":
        return [{"text": pool[i]["text"], "spans": s} for i, s in llm.items()]
    if kind == "union":  # LLM spans, plus rule spans that do not overlap them
        out = []
        for i, s in llm.items():
            spans = list(s)
            for rs in pool[i]["rule_spans"]:
                if all(rs["end"] <= x["start"] or rs["start"] >= x["end"] for x in spans):
                    spans.append(rs)
            out.append({"text": pool[i]["text"], "spans": spans})
        return out
    raise ValueError(kind)


def encode(tok, text: str, spans: list[dict], max_len: int = 128) -> dict:
    enc = tok(text, truncation=True, max_length=max_len, return_offsets_mapping=True)
    labels, prev_in = [], None
    for (a, b) in enc["offset_mapping"]:
        if a == b:  # special tokens
            labels.append(-100)
            prev_in = None
            continue
        tag = 0
        for k, s in enumerate(spans):
            if a >= s["start"] and b <= s["end"] or (a < s["end"] and b > s["start"]):
                tag = 2 if prev_in == k else 1
                prev_in = k
                break
        else:
            prev_in = None
        labels.append(tag)
    enc["labels"] = labels
    return enc


def decode(text: str, offsets: list[tuple[int, int]], tags: list[int]) -> list[dict]:
    """Token tags → character spans (an I without a preceding span starts one; spans snap to whitespace edges)."""
    spans, cur = [], None
    for (a, b), t in zip(offsets, tags):
        if a == b:
            continue
        if t == 1 or (t == 2 and cur is None):
            if cur:
                spans.append(cur)
            cur = [a, b]
        elif t == 2 and cur is not None:
            cur[1] = b
        else:
            if cur:
                spans.append(cur)
            cur = None
    if cur:
        spans.append(cur)
    out = []
    word = lambda ch: ch.isalnum() or ch in "+#"
    for a, b in spans:
        # whole words only: a span that starts or ends inside a word ("Pear|son", "C|redly") is extended to it
        while a > 0 and word(text[a - 1]) and word(text[a]):
            a -= 1
        while b < len(text) and word(text[b - 1]) and word(text[b]):
            b += 1
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1] in " .,;:/":
            b -= 1
        if b > a and not (out and a < out[-1]["end"]):
            out.append({"start": a, "end": b, "text": text[a:b]})
    return out


def collate(tok):
    def f(batch):
        feats = [{k: v for k, v in e.items() if k in ("input_ids", "attention_mask")} for e in batch]
        pad = tok.pad(feats, return_tensors="pt")
        n = pad["input_ids"].shape[1]
        pad["labels"] = torch.tensor([e["labels"] + [-100] * (n - len(e["labels"])) for e in batch])
        return pad
    return f


@torch.no_grad()
def predict(model, tok, rows: list[dict], device, bs: int = 32) -> list[list[dict]]:
    model.eval()
    out = []
    for i in range(0, len(rows), bs):
        texts = [r["text"] for r in rows[i:i + bs]]
        enc = tok(texts, truncation=True, max_length=128, padding=True, return_offsets_mapping=True,
                  return_tensors="pt")
        offs = enc.pop("offset_mapping").tolist()
        with torch.autocast(device.type, enabled=device.type == "cuda"):
            logits = model(**{k: v.to(device) for k, v in enc.items()}).logits
        tags = logits.argmax(-1).tolist()
        for t, o, text in zip(tags, offs, texts):
            out.append(decode(text, [tuple(x) for x in o], t))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", choices=["rules", "llm", "union"], default="llm")
    ap.add_argument("--base", default="FacebookAI/roberta-base")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--bs", type=int, default=16)
    a = ap.parse_args()
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    name = f"skill-{a.labels}-{a.base.split('/')[-1]}"

    rows = training_rows(a.labels)
    random.shuffle(rows)
    n_dev = max(50, len(rows) // 10)
    dev, train = rows[:n_dev], rows[n_dev:]
    tok = AutoTokenizer.from_pretrained(a.base, add_prefix_space=True) if "roberta" in a.base \
        else AutoTokenizer.from_pretrained(a.base)
    model = AutoModelForTokenClassification.from_pretrained(
        a.base, num_labels=3, id2label=dict(enumerate(LABELS)), label2id={l: i for i, l in enumerate(LABELS)},
        dtype=torch.float32).to(device)  # fp32 master weights; autocast does the fp16 maths

    enc = [encode(tok, r["text"], r["spans"]) for r in train]
    dl = DataLoader(enc, batch_size=a.bs, shuffle=True, collate_fn=collate(tok))
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * len(dl) * a.epochs), len(dl) * a.epochs)
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")
    dev_gold = {str(i): {"spans": r["spans"]} for i, r in enumerate(dev)}

    best, best_state, t0 = -1.0, None, time.time()
    for ep in range(a.epochs):
        model.train()
        for batch in dl:
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.autocast(device.type, enabled=device.type == "cuda"):
                loss = model(**batch).loss
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
        dev_pred = {str(i): p for i, p in enumerate(predict(model, tok, dev, device))}
        f1 = score(dev_gold, dev_pred, "overlap")["f1"]
        print(f"epoch {ep + 1}: loss {loss.item():.3f} · dev overlap F1 {f1:.3f} · {time.time() - t0:.0f}s", flush=True)
        if f1 > best:
            best, best_state = f1, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)

    out_dir = ROOT / "models" / name
    model.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)

    gold_rows = load_jsonl(D / "gold_candidates.jsonl")
    preds = predict(model, tok, gold_rows, device)
    pred = {r["id"]: p for r, p in zip(gold_rows, preds)}
    (D / "preds").mkdir(exist_ok=True)
    with (D / "preds" / f"{name}.jsonl").open("w", encoding="utf-8") as f:
        for r, p in zip(gold_rows, preds):
            f.write(json.dumps({"id": r["id"], "spans": p}, ensure_ascii=False) + "\n")

    res = {"model": name, "base": a.base, "labels": a.labels, "train_sentences": len(train),
           "epochs": a.epochs, "best_dev_f1": best, "train_seconds": round(time.time() - t0),
           "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu"}
    for view in ("verified", "strict"):
        g = gold(view)
        for mode in ("exact", "overlap"):
            res[f"{view}_{mode}"] = score(g, pred, mode)
    path = D / "results.json"
    allres = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    allres[name] = res
    path.write_text(json.dumps(allres, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("verified_exact", "verified_overlap")}, indent=1))


if __name__ == "__main__":
    main()
