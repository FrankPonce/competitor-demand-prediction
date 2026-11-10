"""Sprint 11 tests: span scoring, LLM span location, BIO encoding/decoding, dataset split, rule spans.

Run: python -m pytest -q
"""

import json
from pathlib import Path

import pytest

from src.skillmodel.data import is_test, rule_spans, split_sentences
from src.skillmodel.evaluate import STRICT_EXCLUDE, score
from src.skillmodel.llm_label import locate
from src.skillmodel.train import decode

D = Path(__file__).resolve().parents[1] / "data" / "skillmodel"


def sp(a, b):
    return {"start": a, "end": b}


# ---------------------------------------------------------------- scoring

def test_exact_and_overlap_scoring():
    gold = {"s1": {"spans": [sp(0, 6), sp(10, 20)]}}
    pred = {"s1": [sp(0, 6), sp(12, 25), sp(30, 35)]}
    ex, ov = score(gold, pred, "exact"), score(gold, pred, "overlap")
    assert (ex["tp"], ex["fp"], ex["fn"]) == (1, 2, 1)
    assert (ov["tp"], ov["fp"], ov["fn"]) == (2, 1, 0)


def test_overlap_is_one_to_one():
    # one long prediction covering two gold spans counts once
    gold = {"s1": {"spans": [sp(0, 5), sp(6, 10)]}}
    assert score(gold, {"s1": [sp(0, 10)]}, "overlap")["tp"] == 1


def test_empty_sentences_score_cleanly():
    assert score({"s1": {"spans": []}}, {"s1": []})["f1"] == 0.0


# ---------------------------------------------------------------- LLM span location

def test_locate_handles_repeats_case_and_missing():
    text = "incident response, SOC analyst, incident response"
    got = locate(text, ["incident response", "SOC analyst", "incident response", "not there"])
    assert [(s["start"], s["text"]) for s in got] == [(0, "incident response"), (19, "SOC analyst"),
                                                       (32, "incident response")]
    assert locate("Uses PYTHON daily", ["python"])[0]["text"] == "PYTHON"


# ---------------------------------------------------------------- BIO decoding

def test_decode_snaps_to_whole_words():
    text = "managing vendors (Pearson, Credly)"
    # sub-word pieces tagged inside words must not produce fragments such as "Pear" or "ly"
    offs = [(0, 8), (9, 16), (17, 18), (18, 22), (22, 25), (25, 26), (27, 28), (28, 33), (33, 34)]
    tags = [0, 0, 0, 1, 0, 0, 0, 2, 0]
    assert [s["text"] for s in decode(text, offs, tags)] == ["Pearson", "Credly"]


def test_decode_b_i_sequences_and_trailing_punctuation():
    text = "Python, Go / Rust."
    offs = [(0, 6), (6, 7), (8, 10), (11, 12), (13, 17), (17, 18)]
    tags = [1, 0, 1, 0, 1, 2]
    assert [s["text"] for s in decode(text, offs, tags)] == ["Python", "Go", "Rust"]


def test_encode_decode_roundtrip_with_real_tokenizer():
    transformers = pytest.importorskip("transformers")
    try:
        tok = transformers.AutoTokenizer.from_pretrained("FacebookAI/roberta-base", add_prefix_space=True,
                                                         local_files_only=True)
    except Exception:
        pytest.skip("roberta-base tokenizer not cached")
    from src.skillmodel.train import encode
    text = "Experience with distributed training and Kubernetes (EKS) at scale"
    spans = [{"start": 16, "end": 36}, {"start": 41, "end": 51}, {"start": 53, "end": 56}]
    enc = encode(tok, text, spans)
    got = decode(text, [tuple(o) for o in enc["offset_mapping"]], [max(t, 0) for t in enc["labels"]])
    assert [s["text"] for s in got] == ["distributed training", "Kubernetes", "EKS"]


# ---------------------------------------------------------------- dataset

def test_split_is_stable_and_about_ten_percent():
    ids = [f"job-{i}" for i in range(5000)]
    share = sum(map(is_test, ids)) / len(ids)
    assert 0.08 < share < 0.12 and is_test("job-7") == is_test("job-7")


def test_sentence_splitting_strips_bullets_and_filters_length():
    s = split_sentences("• Build data pipelines in Python and Spark. Ship them to production every single week.\n"
                        "Too short here.\nOK")
    assert s == ["Build data pipelines in Python and Spark.", "Ship them to production every single week."]


def test_rule_spans_prefer_longer_match():
    spans = rule_spans("We use machine learning and Python")
    texts = [s["text"] for s in spans]
    assert "Python" in texts and not any(t == "learning" for t in texts)


@pytest.mark.skipif(not (D / "gold.jsonl").exists(), reason="gold set not built")
def test_gold_set_is_verified_held_out_and_consistent():
    gold = [json.loads(l) for l in (D / "gold.jsonl").open(encoding="utf-8")]
    train_jobs = {json.loads(l)["job_id"] for l in (D / "train_pool.jsonl").open(encoding="utf-8")}
    cand = {json.loads(l)["id"]: json.loads(l) for l in (D / "gold_candidates.jsonl").open(encoding="utf-8")}
    assert len(gold) == 200 and all(r["status"] == "verified" for r in gold)
    assert not {cand[r["id"]]["job_id"] for r in gold} & train_jobs
    for r in gold:
        for s in r["spans"]:
            assert r["text"][s["start"]:s["end"]] == s["text"]
    for text, frag, _ in STRICT_EXCLUDE:  # every strict exclusion points at a real span
        assert any(frag in r["text"] and any(s["text"] == text for s in r["spans"]) for r in gold), (text, frag)
