from types import SimpleNamespace

from app.detectors import GlinerRecognizer, character_windows


def test_character_windows_cover_boundaries_and_final_tail():
    text = "А" * 30_123
    windows = list(character_windows(text))
    assert windows[0][0] == 0
    assert windows[-1][0] + len(windows[-1][1]) == len(text)
    assert all(
        start + len(part) >= next_start
        for (start, part), (next_start, _) in zip(windows, windows[1:], strict=False)
    )


def test_gliner_subword_windows_cover_all_words_without_truncation():
    detector = object.__new__(GlinerRecognizer)
    detector.model = SimpleNamespace(config=SimpleNamespace(max_len=384))
    detector.tokenizer = SimpleNamespace(encode=lambda text, **kw: list(text))
    text = ("Иванов Пётр Сергеевич адрес Москва " * 250).strip()
    covered = set()
    for start, chunk in detector.windows(text, ["person"]):
        assert chunk == text[start : start + len(chunk)]
        assert len(chunk) <= 256
        covered.update(range(start, start + len(chunk)))
    assert all(i in covered for i, char in enumerate(text) if not char.isspace())
