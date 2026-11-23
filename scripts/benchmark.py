"""Evaluate local annotations without printing raw text. Exact typed spans + character coverage."""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from app.config import Settings
from app.engine import DetectionEngine
from app.schemas import Options


def evaluate(engine, rows, profile):
    tp = fp = fn = covered = sensitive = 0
    per_type = {}
    started = time.perf_counter()
    for row in rows:
        text = row["text"]
        truth = {(int(e["start"]), int(e["end"]), e["entity_type"]) for e in row["entities"]}
        prediction = {(e.start, e.end, e.entity_type) for e in engine.detect(text, Options(profile=profile))}
        tp += len(truth & prediction)
        fp += len(prediction - truth)
        fn += len(truth - prediction)
        for kind in {e[2] for e in truth | prediction}:
            counts = per_type.setdefault(kind, Counter())
            counts.update(
                tp=len({e for e in truth & prediction if e[2] == kind}),
                fp=len({e for e in prediction - truth if e[2] == kind}),
                fn=len({e for e in truth - prediction if e[2] == kind}),
            )
        # Type-independent coverage catches a partial name escaping even after union merging.
        expected = {i for start, end, _ in truth for i in range(start, end)}
        actual = {i for start, end, _ in prediction for i in range(start, end)}
        sensitive += len(expected)
        covered += len(expected & actual)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    return {
        "profile": profile,
        "documents": len(rows),
        "seconds": round(time.perf_counter() - started, 3),
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
        "sensitive_character_recall": covered / sensitive if sensitive else None,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "per_type": per_type,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path, help="JSONL: text + entities[{start,end,entity_type}]")
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=["rules", "rubert", "hybrid"],
        choices=["rules", "rubert", "gliner", "hybrid"],
    )
    args = parser.parse_args()
    rows = [
        json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if not rows:
        parser.error("The dataset is empty")
    for row in rows:
        for entity in row["entities"]:
            if not 0 <= entity["start"] < entity["end"] <= len(row["text"]):
                parser.error("Invalid annotation offsets")
    settings = Settings(
        enable_rubert=bool(set(args.profiles) & {"rubert", "hybrid"}),
        enable_gliner=bool(set(args.profiles) & {"gliner", "hybrid"}),
        default_profile=args.profiles[0],
    )
    engine = DetectionEngine(settings)
    for profile in args.profiles:
        print(json.dumps(evaluate(engine, rows, profile), ensure_ascii=False))


if __name__ == "__main__":
    main()
