"""Extract text and export anonymized documents without retaining sensitive metadata."""

import io
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field

from defusedxml import ElementTree

from app.config import Settings
from app.engine import DetectionEngine, Masker
from app.errors import ServiceError
from app.schemas import DocumentOptions

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass
class Segment:
    text: str
    location: tuple = ()


@dataclass
class Extracted:
    kind: str
    segments: list[Segment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, text, location, settings):
        # Limit while reading rather than after joining a potentially huge document.
        if len(text) + getattr(self, "_chars", 0) + 1 > settings.max_document_chars:
            raise ServiceError("document_text_limit_exceeded", 413)
        self._chars = len(text) + getattr(self, "_chars", 0) + 1
        self.segments.append(Segment(text, location))


def check_zip(data: bytes, settings: Settings):
    archive = zipfile.ZipFile(io.BytesIO(data))
    members = archive.infolist()
    if len(members) > 10_000 or sum(m.file_size for m in members) > settings.max_unpacked_mb * 1024**2:
        archive.close()
        raise ServiceError("archive_unpacked_limit_exceeded", 413)
    if any(m.flag_bits & 1 for m in members):
        archive.close()
        raise ServiceError("encrypted_document_not_supported")
    if len({m.filename for m in members}) != len(members):
        archive.close()
        raise ServiceError("duplicate_archive_members")
    return archive


def extract_docx(data: bytes, settings: Settings):
    result = Extracted("docx", warnings=["document_rebuilt_without_original_layout_or_metadata"])
    with check_zip(data, settings) as archive:
        names = archive.namelist()
        if "word/document.xml" not in names:
            raise ServiceError("invalid_docx")
        if any(n.startswith(("word/media/", "word/embeddings/")) or "vbaProject" in n for n in names):
            raise ServiceError("office_images_or_embeddings_require_separate_processing")
        # Includes tables, headers, footers, comments, footnotes, deleted/hidden text.
        parts = ["word/document.xml"] + sorted(
            n
            for n in names
            if re.fullmatch(r"word/(?:header\d*|footer\d*|footnotes|endnotes|comments)\.xml", n)
        )
        for name in parts:
            root = ElementTree.fromstring(archive.read(name))
            if any(
                node.tag.endswith(("}drawing", "}object", "}pict", "}altChunk", "}txbxContent"))
                for node in root.iter()
            ):
                raise ServiceError("unsupported_office_content")
            for paragraph in root.iter(W + "p"):
                text = "".join(
                    (node.text or "")
                    if node.tag in {W + "t", W + "delText"}
                    else "\t"
                    if node.tag == W + "tab"
                    else "\n"
                    for node in paragraph.iter()
                    if node.tag in {W + "t", W + "delText", W + "tab", W + "br", W + "cr"}
                )
                if text:
                    result.add(text, (), settings)
    return result


def extract_xlsx(data: bytes, settings: Settings):
    from openpyxl import load_workbook

    result = Extracted(
        "xlsx",
        warnings=[
            "workbook_rebuilt_without_styles_links_comments_or_metadata",
            "sheet_names_replaced_with_generic_names",
        ],
    )
    with check_zip(data, settings) as archive:
        if any(
            n.startswith(("xl/media/", "xl/embeddings/", "xl/drawings/")) or "vbaProject" in n
            for n in archive.namelist()
        ):
            raise ServiceError("office_images_or_embeddings_require_separate_processing")
    workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=False, keep_links=False)
    cached_workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True, keep_links=False)
    try:
        visited = 0
        has_formulas = False
        for sheet_index, (sheet, cached_sheet) in enumerate(
            zip(workbook.worksheets, cached_workbook.worksheets, strict=True)
        ):
            # Treat names as input text too, but never reuse them in output workbook metadata.
            result.add(sheet.title, (sheet_index, 0, 0), settings)
            # Declared dimensions are attacker controlled; never iterate a full XFD x 1M sheet.
            if (sheet.max_row or 0) * (sheet.max_column or 0) > settings.max_cells:
                raise ServiceError("workbook_cell_limit_exceeded", 413)
            for row in sheet.iter_rows():
                for cell in row:
                    visited += 1
                    if visited > settings.max_cells:
                        raise ServiceError("workbook_cell_limit_exceeded", 413)
                    if cell.data_type == "f":
                        has_formulas = True
                        # The rebuilt result never contains formulas: they can contain
                        # source values or external links that must not survive export.
                        # Use an Excel-saved cached result when available instead.
                        value = cached_sheet[cell.coordinate].value
                        if value is None:
                            raise ServiceError("formulas_require_cached_values")
                    else:
                        value = cell.value
                    if value is not None:
                        result.add(str(value), (sheet_index, cell.row, cell.column), settings)
        if has_formulas:
            result.warnings.append("formulas_replaced_with_cached_values")
    finally:
        workbook.close()
        cached_workbook.close()
    return result


def pdf_module():
    try:
        import pymupdf

        return pymupdf
    except ImportError as exc:
        raise ServiceError("pdf_extra_not_installed", 503) from exc


def extract_pdf(data: bytes, settings: Settings):
    fitz = pdf_module()
    result = Extracted(
        "pdf",
        warnings=[
            "pdf_text_extraction_requires_review_of_reading_order",
            "pdf_layout_preserved_but_mask_positions_require_review",
        ],
    )
    with fitz.open(stream=data, filetype="pdf") as document:
        if document.needs_pass:
            raise ServiceError("encrypted_document_not_supported")
        if document.page_count > settings.max_pages:
            raise ServiceError("pdf_page_limit_exceeded", 413)
        for page in document:
            if page.get_images(full=True):
                raise ServiceError("pdf_images_require_ocr_pipeline")
            text = page.get_text("text", sort=True)
            if not text.strip():
                raise ServiceError("pdf_empty_or_scanned_page_requires_ocr")
            result.add(text, (page.number,), settings)
    return result


def extract(data: bytes, kind: str, settings: Settings):
    try:
        if kind == "txt":
            text = data.decode("utf-8-sig", errors="strict")
            if "\x00" in text:
                raise ServiceError("text_must_be_utf8_without_null_bytes")
            result = Extracted("txt")
            result.add(text, (), settings)
        elif kind == "docx":
            result = extract_docx(data, settings)
        elif kind == "xlsx":
            result = extract_xlsx(data, settings)
        elif kind == "pdf":
            result = extract_pdf(data, settings)
        else:
            raise ServiceError("unsupported_file_type", 415)
        if not any(s.text.strip() for s in result.segments):
            raise ServiceError("document_contains_no_text")
        return result
    except ServiceError:
        raise
    except Exception as exc:
        # Parser errors can contain original text, paths, filenames or XML.
        raise ServiceError("invalid_or_unsupported_document") from exc


def export_pdf_with_layout(data: bytes, extracted: Extracted, findings, masker: Masker):
    """Erase detected text in place, preserving pages, tables, vector lines and layout.

    PDF text has no editable paragraph model. Redaction annotations physically remove
    source glyphs; replacement labels are then drawn in the same rectangles. If a
    value cannot be located, fail closed rather than return a document with a leak.
    """
    fitz = pdf_module()
    document = fitz.open(stream=data, filetype="pdf")
    try:
        if document.page_count != len(extracted.segments):
            raise ServiceError("pdf_page_mapping_failed")
        if document.embfile_count():
            for index in range(document.embfile_count() - 1, -1, -1):
                document.embfile_del(index)
        if document.get_xml_metadata():
            document.del_xml_metadata()
        document.set_metadata({key: "" for key in document.metadata})

        segment_start = 0
        verification_regions: list[tuple[int, object, str]] = []
        for segment in extracted.segments:
            page = document[segment.location[0]]
            if page.first_annot or page.first_widget:
                raise ServiceError("pdf_annotations_or_forms_require_separate_processing")
            segment_end = segment_start + len(segment.text)
            labels: list[tuple[object, str]] = []
            for finding in findings:
                if finding.end <= segment_start or finding.start >= segment_end:
                    continue
                start = max(0, finding.start - segment_start)
                end = min(len(segment.text), finding.end - segment_start)
                if not segment.text[start:end].strip():
                    continue
                replacement = masker.replacement("\n".join(s.text for s in extracted.segments), finding)
                for rectangle, words in _pdf_rectangles_for_span(page, segment.text, start, end):
                    page.add_redact_annot(rectangle, fill=(1, 1, 1), cross_out=False)
                    labels.append((rectangle, replacement))
                    verification_regions.extend((page.number, rectangle, word) for word in words)
            if labels and not page.apply_redactions(images=0, graphics=0, text=0):
                raise ServiceError("pdf_redaction_failed")
            for rectangle, replacement in labels:
                _write_pdf_mask(page, rectangle, replacement)
            segment_start = segment_end + 1

        output = document.tobytes(garbage=4, deflate=True, clean=True)
    finally:
        document.close()

    # Confirm the source text is absent from the exact redaction rectangles. A
    # document-wide string check is unsafe: an equal word on another page may be
    # non-sensitive or may be an independently missed entity, neither of which
    # proves that this particular redaction failed.
    with fitz.open(stream=output, filetype="pdf") as cleaned:
        for page_number, rectangle, word in verification_regions:
            if word and word.casefold() in cleaned[page_number].get_textbox(rectangle).casefold():
                raise ServiceError("pdf_redaction_verification_failed")
    return output


def _pdf_rectangles_for_span(page, text: str, start: int, end: int):
    """Map one text offset span to its own PDF word rectangles.

    ``Page.search_for(value)`` returns *every* equal value on a page, losing the
    occurrence selected by a detector.  The word extractor supplies coordinates
    and reading order, so we align it with the exact text passed to the model and
    redact only words overlapped by the selected character interval.  A partial
    word is redacted as a whole word, which is fail-closed for PII.
    """
    word_spans = []
    cursor = 0
    for x0, y0, x1, y1, word, block, line, _ in page.get_text("words", sort=True):
        offset = text.find(word, cursor)
        if offset < 0:
            raise ServiceError("pdf_coordinate_mapping_failed")
        word_spans.append((offset, offset + len(word), (x0, y0, x1, y1), block, line, word))
        cursor = offset + len(word)

    selected = [span for span in word_spans if span[0] < end and span[1] > start]
    if not selected:
        raise ServiceError("pdf_redaction_location_not_found")

    rectangles = []
    current = None
    current_words: list[str] = []
    current_block_line = None
    for _, _, coords, block, line, word in selected:
        rectangle = page.rect.__class__(coords)
        block_line = (block, line)
        # Adjacent words on one rendered line form one readable replacement.
        if (
            current is not None
            and block_line == current_block_line
            and rectangle.x0 - current.x1 <= max(8.0, rectangle.height)
        ):
            current.include_rect(rectangle)
            current_words.append(word)
        else:
            if current is not None:
                rectangles.append((current, current_words))
            current = rectangle
            current_words = [word]
            current_block_line = block_line
    if current is not None:
        rectangles.append((current, current_words))
    return rectangles


def _write_pdf_mask(page, rectangle, replacement: str):
    """Use the compact marker if the typed placeholder cannot fit its original cell."""
    font_size = max(4.0, min(8.0, rectangle.height * 0.72))
    for label in (replacement, "[PII]"):
        result = page.insert_textbox(
            rectangle,
            label,
            fontname="helv",
            fontsize=font_size,
            color=(0, 0, 0),
            align=0,
            overlay=True,
        )
        if result >= 0:
            return
    # The original text was physically removed even if there is no room for a label.
    page.draw_rect(rectangle, color=None, fill=(0, 0, 0), overlay=True)


def export_document(extracted: Extracted, masked_segments: list[str], text: str, settings: Settings):
    stream = io.BytesIO()
    if extracted.kind == "docx":
        from docx import Document

        document = Document()
        document.core_properties.author = ""
        document.core_properties.last_modified_by = ""
        for part in masked_segments:
            document.add_paragraph(part)
        document.save(stream)
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif extracted.kind == "xlsx":
        from openpyxl import Workbook

        workbook = Workbook()
        workbook.remove(workbook.active)
        workbook.properties.creator = ""
        workbook.properties.lastModifiedBy = ""
        sheets = {}
        for segment, value in zip(extracted.segments, masked_segments, strict=True):
            index, row, column = segment.location
            if index not in sheets:
                sheets[index] = workbook.create_sheet(f"Sheet {index + 1}")
            if row:
                cell = sheets[index].cell(row, column, value)
                # Literal strings starting with '=' must never become formulas.
                cell.data_type = "s"
        workbook.save(stream)
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        return text.encode("utf-8"), "text/plain; charset=utf-8", "txt"
    return stream.getvalue(), mime, extracted.kind


def process_document(data: bytes, kind: str, options: DocumentOptions, engine: DetectionEngine):
    extracted = extract(data, kind, engine.settings)
    source = "\n".join(s.text for s in extracted.segments)
    findings = engine.detect(source, options)
    masker = Masker(options.mode)
    masked_text = masker.apply(source, findings)
    # Reconstruct cells/paragraphs using global findings, including spans crossing boundaries.
    masked_segments = []
    cursor = 0
    finding_index = 0
    for segment in extracted.segments:
        end = cursor + len(segment.text)
        while finding_index < len(findings) and findings[finding_index].end <= cursor:
            finding_index += 1
        pieces = []
        position = 0
        for index in range(finding_index, len(findings)):
            f = findings[index]
            if f.start >= end:
                break
            start = max(0, f.start - cursor)
            pieces.append(segment.text[position:start])
            pieces.append(masker.replacement(source, f))
            position = min(end, f.end) - cursor
        pieces.append(segment.text[position:])
        masked_segments.append("".join(pieces))
        cursor = end + 1
    if options.output == "document":
        if kind == "pdf":
            output, mime, extension = (
                export_pdf_with_layout(data, extracted, findings, masker),
                "application/pdf",
                "pdf",
            )
        else:
            output, mime, extension = export_document(
                extracted, masked_segments, masked_text, engine.settings
            )
    else:
        output, mime, extension = masked_text.encode("utf-8"), "text/plain; charset=utf-8", "txt"
    if len(output) > engine.settings.max_upload_mb * 4 * 1024**2:
        raise ServiceError("output_size_limit_exceeded", 413)
    warnings = list(extracted.warnings)
    if engine.resolve(options) == "rules":
        warnings.append("rules_only_does_not_detect_names_or_addresses")
    if any(f.entity_type == "SENSITIVE" for f in findings):
        warnings.append("overlapping_entity_types_masked_as_union")
    # The report deliberately excludes source values and original filenames.
    report = {
        "profile": engine.resolve(options),
        "counts": dict(Counter(f.entity_type for f in findings)),
        "finding_count": len(findings),
        "characters": len(source),
        "warnings": warnings,
        "output_name": f"anonymized.{extension}",
        "output_mime": mime,
    }
    return output, report
