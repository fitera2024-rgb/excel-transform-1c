from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile
from xml.etree import ElementTree as ET

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment


ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
ILLEGAL_XML_CHARACTERS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
OFFICE_DOCUMENT_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
EXTERNAL_RELATIONSHIP_SUFFIXES = ("/externalLink", "/calcChain")
REMOVED_PART_PREFIXES = ("xl/externalLinks/",)
REMOVED_PARTS = {"xl/calcChain.xml"}


class WorkbookRepairError(ValueError):
    """A local workbook working copy cannot be reconstructed safely."""


def has_zip_signature(path: str | Path) -> bool:
    with Path(path).open("rb") as source:
        return source.read(4) in ZIP_SIGNATURES


def repair_ooxml_workbook(source_path: str | Path, target_path: str | Path) -> str:
    """Create a values-only, structurally clean OOXML working copy.

    The immutable source is never modified. The first pass lets openpyxl rebuild
    dimensions, relationships and worksheet metadata. If the source contains a
    repairable XML defect, a second pass removes unsupported external-link parts
    and illegal XML control characters before reserializing the workbook.
    """

    source = Path(source_path)
    target = Path(target_path)
    target.unlink(missing_ok=True)
    if not has_zip_signature(source):
        raise WorkbookRepairError("Файл не является книгой Excel OOXML")

    first_error: Exception | None = None
    try:
        _reserialize_ooxml(source, target)
        return "Структура книги восстановлена во внутреннюю рабочую копию"
    except Exception as exc:  # noqa: BLE001 - normalized below
        first_error = exc
        target.unlink(missing_ok=True)

    with TemporaryDirectory(prefix="opiu-ooxml-repair-") as temporary_directory:
        sanitized = Path(temporary_directory) / "sanitized.xlsx"
        try:
            _sanitize_ooxml_archive(source, sanitized)
            _reserialize_ooxml(sanitized, target)
            return (
                "Повреждённые служебные части книги удалены; "
                "данные открыты во внутренней рабочей копии"
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            target.unlink(missing_ok=True)
            raise WorkbookRepairError(
                "Автоматическое восстановление книги Excel не удалось"
            ) from exc if first_error is None else exc


def convert_legacy_xls(source_path: str | Path, target_path: str | Path) -> str:
    """Convert a legacy BIFF .xls workbook to a values-only OOXML working copy."""

    try:
        import xlrd  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - packaging guard
        raise WorkbookRepairError(
            "Для восстановления старого формата Excel отсутствует локальный компонент xlrd"
        ) from exc

    source = Path(source_path)
    target = Path(target_path)
    target.unlink(missing_ok=True)

    book = None
    formatting_info = True
    try:
        try:
            book = xlrd.open_workbook(
                filename=str(source),
                formatting_info=True,
                on_demand=True,
            )
        except Exception:
            formatting_info = False
            book = xlrd.open_workbook(
                filename=str(source),
                formatting_info=False,
                on_demand=True,
            )

        workbook = Workbook()
        used_titles: set[str] = set()
        try:
            for index in range(book.nsheets):
                source_sheet = book.sheet_by_index(index)
                title = _unique_sheet_title(source_sheet.name, used_titles)
                if index == 0:
                    target_sheet = workbook.active
                    target_sheet.title = title
                else:
                    target_sheet = workbook.create_sheet(title)

                for row_index in range(source_sheet.nrows):
                    for column_index in range(source_sheet.ncols):
                        source_cell = source_sheet.cell(row_index, column_index)
                        value = _xlrd_value(book, source_cell)
                        if value is None:
                            continue
                        target_cell = target_sheet.cell(
                            row=row_index + 1,
                            column=column_index + 1,
                            value=value,
                        )
                        if formatting_info:
                            indent = _xlrd_indent(book, source_cell)
                            if indent:
                                target_cell.alignment = Alignment(indent=indent)

                for row_low, row_high, col_low, col_high in getattr(
                    source_sheet, "merged_cells", []
                ):
                    if row_high - row_low > 1 or col_high - col_low > 1:
                        target_sheet.merge_cells(
                            start_row=row_low + 1,
                            end_row=row_high,
                            start_column=col_low + 1,
                            end_column=col_high,
                        )

            workbook.save(target)
        finally:
            workbook.close()
    except Exception as exc:  # noqa: BLE001 - normalized below
        target.unlink(missing_ok=True)
        raise WorkbookRepairError(
            "Старый формат Excel не удалось преобразовать во внутреннюю рабочую копию"
        ) from exc
    finally:
        if book is not None:
            try:
                book.release_resources()
            except Exception:
                pass

    _validate_ooxml(target)
    return "Старый формат Excel преобразован во внутреннюю рабочую копию"


def repair_reference_content(content: bytes, suffix: str = ".xlsx") -> bytes:
    """Best-effort repair for reference uploads without modifying the source bytes."""

    with TemporaryDirectory(prefix="opiu-reference-repair-") as directory:
        root = Path(directory)
        source = root / f"source{suffix}"
        target = root / "source-repaired.xlsx"
        source.write_bytes(content)
        if has_zip_signature(source):
            repair_ooxml_workbook(source, target)
        else:
            convert_legacy_xls(source, target)
        return target.read_bytes()


def _reserialize_ooxml(source: Path, target: Path) -> None:
    workbook = load_workbook(
        source,
        data_only=True,
        read_only=False,
        keep_links=False,
    )
    try:
        if not workbook.worksheets:
            raise WorkbookRepairError("В книге Excel отсутствуют листы")
        workbook.save(target)
    finally:
        workbook.close()
    _validate_ooxml(target)


def _validate_ooxml(path: Path) -> None:
    workbook = load_workbook(path, data_only=True, read_only=True, keep_links=False)
    try:
        if not workbook.worksheets:
            raise WorkbookRepairError("В восстановленной книге Excel отсутствуют листы")
    finally:
        workbook.close()


def _sanitize_ooxml_archive(source: Path, target: Path) -> None:
    try:
        with ZipFile(source, "r") as input_archive, ZipFile(
            target, "w", ZIP_DEFLATED
        ) as output_archive:
            for item in input_archive.infolist():
                name = item.filename
                if name in REMOVED_PARTS or name.startswith(REMOVED_PART_PREFIXES):
                    continue
                payload = input_archive.read(item)
                if name.endswith((".xml", ".rels")):
                    payload = _sanitize_xml_part(name, payload)
                output_archive.writestr(item, payload)
    except BadZipFile as exc:
        target.unlink(missing_ok=True)
        raise WorkbookRepairError("Архив книги Excel повреждён") from exc


def _sanitize_xml_part(name: str, payload: bytes) -> bytes:
    text = payload.decode("utf-8", errors="replace")
    text = ILLEGAL_XML_CHARACTERS.sub("", text)
    if name == "[Content_Types].xml":
        return _remove_content_type_parts(text)
    if name == "xl/_rels/workbook.xml.rels":
        return _remove_external_relationships(text)
    if name == "xl/workbook.xml":
        return _remove_external_references(text)
    return text.encode("utf-8")


def _remove_content_type_parts(text: str) -> bytes:
    ET.register_namespace("", CONTENT_TYPES_NS)
    root = ET.fromstring(text)
    for child in list(root):
        part_name = child.attrib.get("PartName", "").lstrip("/")
        if part_name in REMOVED_PARTS or part_name.startswith(REMOVED_PART_PREFIXES):
            root.remove(child)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _remove_external_relationships(text: str) -> bytes:
    ET.register_namespace("", OFFICE_DOCUMENT_REL_NS)
    root = ET.fromstring(text)
    for child in list(root):
        relation_type = child.attrib.get("Type", "")
        if relation_type.endswith(EXTERNAL_RELATIONSHIP_SUFFIXES):
            root.remove(child)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _remove_external_references(text: str) -> bytes:
    ET.register_namespace("", SPREADSHEET_NS)
    root = ET.fromstring(text)
    for child in list(root):
        if child.tag == f"{{{SPREADSHEET_NS}}}externalReferences":
            root.remove(child)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _unique_sheet_title(raw_title: str, used: set[str]) -> str:
    base = re.sub(r"[\\/*?:\[\]]", "_", (raw_title or "Лист").strip())[:31] or "Лист"
    title = base
    number = 2
    while title in used:
        suffix = f" ({number})"
        title = f"{base[:31 - len(suffix)]}{suffix}"
        number += 1
    used.add(title)
    return title


def _xlrd_value(book, cell):
    import xlrd  # type: ignore[import-not-found]

    if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return None
    if cell.ctype == xlrd.XL_CELL_DATE:
        return xlrd.xldate_as_datetime(cell.value, book.datemode)
    if cell.ctype == xlrd.XL_CELL_BOOLEAN:
        return bool(cell.value)
    if cell.ctype == xlrd.XL_CELL_ERROR:
        return xlrd.error_text_from_code.get(cell.value, "#VALUE!")
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        number = float(cell.value)
        return int(number) if number.is_integer() else number
    return str(cell.value) if cell.value is not None else None


def _xlrd_indent(book, cell) -> int:
    try:
        xf = book.xf_list[cell.xf_index]
        alignment = xf.alignment
        return max(0, min(int(getattr(alignment, "indent_level", 0) or 0), 15))
    except Exception:
        return 0
