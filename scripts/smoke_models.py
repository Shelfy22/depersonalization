"""Real, offline model smoke check using synthetic examples only."""

import argparse
import json
import time

from app.config import Settings
from app.engine import DetectionEngine
from app.schemas import Options


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gliner", action="store_true")
    parser.add_argument("--long", action="store_true")
    args = parser.parse_args()
    settings = Settings(
        enable_rubert=True, enable_gliner=args.gliner, local_files_only=True, default_profile="rubert"
    )
    started = time.perf_counter()
    engine = DetectionEngine(settings)
    print(json.dumps({"model_load_seconds": round(time.perf_counter() - started, 2)}))
    text = (
        "Передайте документы Иванову Сергею Петровичу. "
        "Адрес: г. Москва, ул. Ленина, д. 10. Почта: test@example.ru. ИНН 7707083893."
    )
    for profile in ["rubert", "gliner", "hybrid"] if args.gliner else ["rubert"]:
        started = time.perf_counter()
        result = engine.anonymize(text, Options(profile=profile))
        print(
            json.dumps(
                {
                    "profile": profile,
                    "seconds": round(time.perf_counter() - started, 3),
                    "text": result.text,
                    "counts": result.counts,
                },
                ensure_ascii=False,
            )
        )
        assert "test@example.ru" not in result.text
        assert "7707083893" not in result.text
        assert result.counts.get("PERSON", 0) > 0, "No PERSON detected in the synthetic example"
    if args.long:
        long_text = "Это служебная строка без персональных данных.\n" * 320 + text
        started = time.perf_counter()
        result = engine.anonymize(long_text, Options(profile="rubert"))
        assert "test@example.ru" not in result.text and result.counts.get("PERSON", 0) > 0
        print(
            json.dumps(
                {
                    "long_text_characters": len(long_text),
                    "counts": result.counts,
                    "seconds": round(time.perf_counter() - started, 3),
                }
            )
        )


if __name__ == "__main__":
    main()
