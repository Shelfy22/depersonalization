import pytest

from app.detectors import usable_model_span
from app.engine import Masker, merge_findings
from app.errors import ServiceError
from app.rules import valid_card, valid_iin, valid_inn, valid_ogrn, valid_snils
from app.schemas import Finding, Options


def f(start, end, kind="PERSON", score=0.9, source="test"):
    return Finding(start=start, end=end, entity_type=kind, score=score, sources=[source])


def test_overlap_masks_longer_low_confidence_name():
    text = "Иванов Иван Иванович"
    result = merge_findings(text, [f(0, 11, score=0.99), f(7, len(text), score=0.5)])
    assert [(r.start, r.end) for r in result] == [(0, len(text))]
    assert Masker().apply(text, result) == "[PERSON_1]"


def test_person_parts_and_split_email_are_joined():
    assert len(merge_findings("Иван Иванов", [f(0, 4), f(5, 11)])) == 1
    assert len(merge_findings("elena@pochta.ru", [f(0, 2, "EMAIL"), f(2, 15, "EMAIL")])) == 1


def test_person_spans_join_across_initial_and_case_ending():
    text = "Ольга М. Петрова"
    merged = merge_findings(text, [f(0, 5), f(9, len(text))])
    assert [(item.start, item.end) for item in merged] == [(0, len(text))]
    text = "Александром Викторовичем"
    merged = merge_findings(text, [f(0, len(text) - 2)])
    assert [(item.start, item.end) for item in merged] == [(0, len(text))]


def test_conflicting_types_keep_entire_union():
    merged = merge_findings("abcdefgh", [f(0, 5), f(3, 8, "ADDRESS")])
    assert merged[0].entity_type == "SENSITIVE"
    assert Masker().apply("abcdefgh", merged) == "[SENSITIVE_1]"


def test_invalid_model_offsets_fail_closed():
    with pytest.raises(ServiceError):
        merge_findings("hello", [f(0, 100)])


@pytest.mark.parametrize(
    "validator,value",
    [
        (valid_inn, "7707083893"),
        (valid_inn, "500100732259"),
        (valid_iin, "870314300126"),
        (valid_snils, "112-233-445 95"),
        (valid_ogrn, "1027700132195"),
        (valid_card, "4111 1111 1111 1111"),
    ],
)
def test_checksums(validator, value):
    assert validator(value)
    assert not validator(value[:-1] + str((int(value[-1]) + 1) % 10))
    assert not validator("0" * len(value))


def test_rules_and_stable_request_local_placeholders(engine):
    text = "Email: ivan@example.ru, повтор: ivan@example.ru. ИНН 7707083893. СНИЛС 112-233-445 95"
    result = engine.anonymize(text, Options())
    assert "ivan@example.ru" not in result.text
    assert "7707083893" not in result.text
    assert "112-233-445" not in result.text
    assert result.text.count("[EMAIL_1]") == 2
    assert "rules_only" in result.warnings[0]


def test_russian_initials_are_masked(engine):
    result = engine.anonymize("Подписал И. И.", Options(entities=["PERSON"]))
    assert "И. И." not in result.text
    assert result.counts == {"PERSON": 1}


def test_contextual_russian_document_fields_are_masked(engine):
    text = (
        "Паспорт: серия 03 18 № 654321. Номер страхового свидетельства: 345-678-901 22. "
        "Дата рождения Екатерины — 22 августа 1992 года. Родился 05.11.1984 года рождения. "
        "Внутренний табельный номер сотрудника — EMP-2026-00481."
    )
    result = engine.anonymize(text, Options())
    for value in [
        "03 18 № 654321",
        "345-678-901 22",
        "22 августа 1992 года",
        "05.11.1984",
        "EMP-2026-00481",
    ]:
        assert value not in result.text
    assert result.counts["PASSPORT"] == 1
    assert result.counts["SNILS"] == 1
    assert result.counts["DATE_OF_BIRTH"] == 2
    assert result.counts["EMPLOYEE_ID"] == 1


def test_invalid_checksum_is_still_masked_when_contextual(engine):
    assert "7707083894" not in engine.anonymize("ИНН 7707083894", Options()).text
    assert engine.anonymize("номер 7707083894", Options(entities=["INN"])).findings == []


def test_structured_identifiers_cover_pdf_linebreaks_and_contextual_invalid_values(engine):
    text = (
        "ИИН: 920822400567. СНИЛС: 234-\n567-890 11. "
        "Шаблон BIO-FACE-78412. Внутренний идентификатор USER-78125."
    )
    result = engine.anonymize(text, Options(profile="rules"))
    for value in ["920822400567", "234-\n567-890 11", "BIO-FACE-78412", "USER-78125"]:
        assert value not in result.text
    assert result.counts["IIN"] == 1
    assert result.counts["SNILS"] == 1
    assert result.counts["BIOMETRIC_ID"] == 1
    assert result.counts["EMPLOYEE_ID"] == 1


def test_medical_condition_and_business_data_policy(engine):
    text = "Диагноз: сахарный диабет второго типа. Показатель за 2кв составляет 195 855,00. Оклад: 100 000 ₽."
    result = engine.anonymize(text, Options(profile="rules"))
    assert "сахарный диабет второго типа" not in result.text
    assert "195 855,00" in result.text
    assert "100 000 ₽" not in result.text


def test_model_context_filters_preserve_business_location_and_player():
    assert not usable_model_span("ADDRESS", "Республика Адыгея", "Регион — Республика Адыгея", 9, 27)
    assert usable_model_span(
        "ADDRESS", "Республика Адыгея", "Адрес проживания: Республика Адыгея", 18, 36
    )
    assert not usable_model_span("PERSON", "Лунда", "Игрок — Лунда", 8, 13)
    assert not usable_model_span(
        "FINANCIAL_AMOUNT", "195 855,00", "Показатель за 2кв: 195 855,00", 20, 30
    )


def test_contextual_extended_categories_are_masked(engine):
    text = (
        "Дата выдачи паспорта 17.09.2015. Место рождения: Майкоп. "
        "Должность: Руководитель отдела. Место работы: ООО Ромашка. "
        "Оклад составляет 100 000 ₽. Диагноз: бронхит. "
        "Координаты 55.755826, 37.617300."
    )
    result = engine.anonymize(text, Options(profile="rules"))
    for value in [
        "17.09.2015",
        "Майкоп",
        "Руководитель отдела",
        "ООО Ромашка",
        "100 000 ₽",
        "бронхит",
        "55.755826, 37.617300",
    ]:
        assert value not in result.text
    assert set(result.counts) >= {
        "PASSPORT_ISSUE_DATE",
        "BIRTH_PLACE",
        "JOB_TITLE",
        "WORKPLACE",
        "FINANCIAL_AMOUNT",
        "MEDICAL_INFO",
        "GEOLOCATION",
    }


def test_persistent_dictionary_is_literal_and_selectable(engine):
    from app.schemas import DictionaryUpsert

    engine.dictionaries.replace(
        "projects", DictionaryUpsert(label="PROJECT", terms=["Альфа", "Проект Север", "альфа"])
    )
    result = engine.anonymize("Альфа и Проект Север", Options(entities=["EMAIL"], dictionaries=["projects"]))
    assert result.text == "[PROJECT_1] и [PROJECT_2]"
    assert result.counts == {"PROJECT": 2}


def test_selected_categories_dictionary_and_unicode_offsets(engine):
    text = "😀 СекретПроект +7 999 123-45-67 x@y.ru"
    result = engine.anonymize(text, Options(entities=["EMAIL"], dictionary=["СекретПроект"]))
    assert "+7 999 123-45-67" in result.text
    assert "СекретПроект" not in result.text and "x@y.ru" not in result.text
    email = next(f for f in result.findings if f.entity_type == "EMAIL")
    assert text[email.start : email.end] == "x@y.ru"


def test_models_never_fall_back_to_rules(engine):
    with pytest.raises(ServiceError, match="rubert_not_enabled"):
        engine.anonymize("Иванов", Options(profile="rubert"))
