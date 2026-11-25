import io
import zipfile

import pytest
from docx import Document
from openpyxl import Workbook, load_workbook

from app.documents import export_pdf_with_layout, extract, process_document
from app.engine import Masker
from app.errors import ServiceError
from app.schemas import DocumentOptions, Finding


def test_docx_split_runs_tables_headers_and_hidden_metadata(engine):
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("test@")
    paragraph.add_run("example.ru")
    document.add_table(rows=1, cols=1).cell(0, 0).text = "other@example.ru"
    document.sections[0].header.paragraphs[0].text = "header@example.ru"
    document.core_properties.author = "secret-author"
    stream = io.BytesIO()
    document.save(stream)
    output, report = process_document(stream.getvalue(), "docx", DocumentOptions(output="document"), engine)
    with zipfile.ZipFile(io.BytesIO(output)) as archive:
        content = b"\n".join(archive.read(n) for n in archive.namelist())
    for secret in [b"test@example.ru", b"other@example.ru", b"header@example.ru", b"secret-author"]:
        assert secret not in content
    assert report["counts"]["EMAIL"] == 3


def test_xlsx_hidden_sheets_and_literals(engine):
    workbook = Workbook()
    workbook.active["A1"] = "hello@example.ru"
    hidden = workbook.create_sheet("person@example.ru")
    hidden.sheet_state = "hidden"
    hidden["C3"] = "private@example.ru"
    workbook.active["B2"] = "=literal"
    workbook.active["B2"].data_type = "s"
    stream = io.BytesIO()
    workbook.save(stream)
    output, report = process_document(stream.getvalue(), "xlsx", DocumentOptions(output="document"), engine)
    cleaned = load_workbook(io.BytesIO(output))
    assert cleaned.sheetnames == ["Sheet 1", "Sheet 2"]
    assert cleaned.worksheets[0]["A1"].value.startswith("[EMAIL_")
    assert cleaned.worksheets[1]["C3"].value.startswith("[EMAIL_")
    assert cleaned.worksheets[0]["B2"].data_type == "s"
    assert report["counts"]["EMAIL"] == 3


def test_xlsx_formulas_rejected(engine):
    workbook = Workbook()
    workbook.active["A1"] = '=HYPERLINK("https://private.example.ru")'
    stream = io.BytesIO()
    workbook.save(stream)
    with pytest.raises(ServiceError, match="formulas_require_cached_values"):
        process_document(stream.getvalue(), "xlsx", DocumentOptions(), engine)


def test_xlsx_formulas_use_cached_values_and_do_not_export_formula(engine):
    workbook = Workbook()
    workbook.active["A1"] = "=1+2"
    stream = io.BytesIO()
    workbook.save(stream)
    # openpyxl does not calculate formulas. Simulate an Excel-saved cached value.
    cached = io.BytesIO()
    with zipfile.ZipFile(stream) as source, zipfile.ZipFile(cached, "w", zipfile.ZIP_DEFLATED) as target:
        for member in source.infolist():
            content = source.read(member.filename)
            if member.filename == "xl/worksheets/sheet1.xml":
                content = content.replace(b"<f>1+2</f><v></v>", b"<f>1+2</f><v>3</v>")
            target.writestr(member, content)
    output, report = process_document(cached.getvalue(), "xlsx", DocumentOptions(output="document"), engine)
    cleaned = load_workbook(io.BytesIO(output), data_only=False)
    assert cleaned.active["A1"].value == "3"
    assert "formulas_replaced_with_cached_values" in report["warnings"]


def test_cross_paragraph_entity_uses_same_placeholder(engine):
    document = Document()
    document.add_paragraph("Иван")
    document.add_paragraph("Иванов")
    stream = io.BytesIO()
    document.save(stream)
    output, _ = process_document(
        stream.getvalue(), "docx", DocumentOptions(output="document", dictionary=["Иван\nИванов"]), engine
    )
    cleaned = Document(io.BytesIO(output))
    assert [p.text for p in cleaned.paragraphs] == ["[CUSTOM_1]", "[CUSTOM_1]"]


def test_document_size_and_encoding_failures(settings):
    settings.max_document_chars = 10
    with pytest.raises(ServiceError, match="document_text_limit"):
        extract(b"a" * 100, "txt", settings)
    with pytest.raises(ServiceError, match="invalid_or_unsupported_document"):
        extract(b"\xff\xfe", "txt", settings)


def test_archive_expansion_limit(settings):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "x" * (2 * 1024**2))
    settings.max_unpacked_mb = 1
    with pytest.raises(ServiceError, match="archive_unpacked_limit"):
        extract(stream.getvalue(), "docx", settings)


def test_pdf_preserves_page_layout_and_removes_sensitive_text(engine):
    fitz = pytest.importorskip("pymupdf")
    original = fitz.open()
    page = original.new_page()
    page.insert_text((50, 50), "Mail: hello@example.ru")
    # Grid lines stand in for a table: they must survive physical redaction.
    page.draw_rect(fitz.Rect(40, 70, 300, 150), color=(0, 0, 0), width=1)
    page.draw_line((40, 110), (300, 110), color=(0, 0, 0), width=1)
    page.insert_text((50, 95), "invoice@example.ru")
    original.set_metadata({"author": "private-author"})
    original.embfile_add("secret.txt", b"secret attachment")
    output, report = process_document(original.tobytes(), "pdf", DocumentOptions(output="document"), engine)
    with fitz.open(stream=output, filetype="pdf") as cleaned:
        text = "".join(page.get_text() for page in cleaned)
        assert cleaned.page_count == 1
        assert "hello@example.ru" not in text and "invoice@example.ru" not in text
        assert "[EMAIL_" in text
        assert len(cleaned[0].get_drawings()) >= 2
        assert cleaned.embfile_count() == 0
        assert cleaned.metadata["author"] != "private-author"
    assert report["counts"]["EMAIL"] == 2


def test_pdf_redacts_only_the_detected_repeated_occurrence(engine):
    """A detector offset must not make search_for redact every equal page value."""
    fitz = pytest.importorskip("pymupdf")
    original = fitz.open()
    page = original.new_page()
    page.insert_text((50, 50), "First: duplicate@example.ru")
    page.insert_text((50, 90), "Second: duplicate@example.ru")
    data = original.tobytes()
    extracted = extract(data, "pdf", engine.settings)
    source = "\n".join(segment.text for segment in extracted.segments)
    value = "duplicate@example.ru"
    finding = Finding(
        start=source.index(value),
        end=source.index(value) + len(value),
        entity_type="EMAIL",
        score=1,
        sources=["test"],
    )
    output = export_pdf_with_layout(data, extracted, [finding], Masker())
    with fitz.open(stream=output, filetype="pdf") as cleaned:
        text = cleaned[0].get_text()
    assert text.count(value) == 1
    assert "[EMAIL_1]" in text


def test_pdf_redacts_every_detected_repeated_medical_value(engine):
    fitz = pytest.importorskip("pymupdf")
    original = fitz.open()
    for page_number in range(2):
        page = original.new_page()
        page.insert_font(fontname="arial", fontfile="C:/Windows/Fonts/arial.ttf")
        page.insert_text(
            (50, 50),
            f"Диагноз пациента {page_number + 1}: сахарный диабет второго типа.",
            fontname="arial",
        )
    output, report = process_document(
        original.tobytes(), "pdf", DocumentOptions(profile="rules", output="document"), engine
    )
    with fitz.open(stream=output, filetype="pdf") as cleaned:
        text = "".join(page.get_text() for page in cleaned)
    assert "сахарный диабет" not in text.casefold()
    assert report["counts"]["MEDICAL_INFO"] == 2


def test_pdf_images_and_empty_pages_rejected(engine):
    fitz = pytest.importorskip("pymupdf")
    document = fitz.open()
    document.new_page()
    with pytest.raises(ServiceError, match="requires_ocr"):
        process_document(document.tobytes(), "pdf", DocumentOptions(), engine)
    page = document[0]
    page.insert_text((50, 50), "some text")
    image = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10), False)
    image.clear_with(255)
    page.insert_image(fitz.Rect(50, 80, 100, 130), pixmap=image)
    with pytest.raises(ServiceError, match="pdf_images_require_ocr"):
        process_document(document.tobytes(), "pdf", DocumentOptions(), engine)
