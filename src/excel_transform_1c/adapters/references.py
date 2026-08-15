from __future__ import annotations

import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from excel_transform_1c.adapters.excel import load_cached_workbook
from excel_transform_1c.core.detection import normalize_header
from excel_transform_1c.core.indicator_matching import full_article_path
from excel_transform_1c.core.models import (
    ArticleIndicatorRule,
    ERPArticle,
    IntalevCFO,
    OrganizationNode,
)


ERP_HEADERS = {
    "code": {"код"},
    "name": {"официальное наименование", "наименование erp"},
    "expense_type": {"тип расходов"},
    "expense_group": {"группа расходов"},
    "source_article": {"статья", "исходная статья"},
}

ORG_HEADERS = {
    "node_id": {"id", "идентификатор"},
    "code": {"код"},
    "name": {"наименование", "узел"},
    "parent_id": {"родитель id", "parent id"},
    "full_path": {"полный путь", "путь"},
}

INTALEV_CFO_NAME_ALIASES = {
    "цфо инталев",
    "наименование цфо",
    "наименование цфо инталев",
    "наименование центра финансовой ответственности",
    "центр финансовой ответственности инталев",
    "цфо / подразделение",
    "цфо подразделение",
    "отдел (цфо)",
    "цфо",
    "центр финансовой ответственности",
}
INTALEV_CFO_CODE_ALIASES = {
    "код цфо инталев",
    "код цфо",
    "код центра финансовой ответственности",
    "код",
}
INTALEV_CFO_PATH_ALIASES = {
    "полный путь цфо",
    "путь цфо",
    "иерархия цфо",
    "полное наименование цфо",
    "полный путь",
    "путь",
}

SCENARIO_HEADERS = {
    "name": {"наименование", "сценарий"},
    "year": {"год"},
    "erp_code": {"erp-код", "код"},
    "comment": {"комментарий"},
}

ARTICLE_INDICATOR_HEADERS = {
    "erp_code": {"erp-код статьи", "код erp-статьи", "код статьи"},
    "article_path": {"полный путь статьи", "полный бизнес-путь статьи"},
    "expense_type": {"тип расходов источника", "тип расходов"},
    "expense_group": {"группа расходов источника", "группа расходов"},
    "article_name": {"статья", "исходная статья", "наименование статьи"},
    "indicator": {"показатель", "тип расходов / показатель"},
    "sales_channel": {"канал сбыта"},
}

REAL_EXPORT_HEADERS = {
    "erp_articles": {
        "name": {
            "статья доходов и расходов",
            "статьи доходов и расходов",
            "иерархия статей доходов и расходов",
        },
        "code": {"код", "код элемента", "код справочника", "код записи"},
    },
    "organizations": {
        "name": {
            "организации",
            "организация",
            "структура организаций",
            "иерархия организаций",
            "наименование",
        },
        "code": {"код", "код элемента", "код справочника", "код записи"},
    },
    "scenarios": {
        "name": {
            "сценарии",
            "сценарий",
            "сценарии бюджетирования",
            "наименование",
        },
        "code": {"код", "erp-код", "код элемента", "код справочника", "код записи"},
    },
}

PATH_ALIASES = {"полный путь", "путь", "полное наименование"}
ORG_CFO_NAME_ALIASES = {"головная организация"}
ORG_UNIT_NAME_ALIASES = {"верхний уровень иерархии"}
MAX_HEADER_SCAN_ROWS = 120
ERP_INDENT_UNITS_PER_LEVEL = 2


def parse_reference_workbook(content: bytes, kind: str) -> list[dict[str, Any]]:
    if kind not in {
        "erp_articles",
        "organizations",
        "scenarios",
        "intalev_cfos",
        "article_indicators",
    }:
        raise ValueError("Неизвестный тип справочника")

    # Reference books use the same content-based preparation path as budget
    # books.  This accepts recoverable OOXML case defects and legacy BIFF/XML
    # while keeping the uploaded bytes untouched in a temporary snapshot.
    try:
        with TemporaryDirectory(prefix="excel_transform_1c_reference_") as temp_dir:
            source_path = Path(temp_dir) / "source-original.xlsx"
            source_path.write_bytes(content)
            with load_cached_workbook(source_path, read_only=False) as workbook:
                return _parse_reference_workbook_object(workbook, kind)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Файл справочника не открывается или повреждён") from exc


def _parse_reference_workbook_object(workbook: Any, kind: str) -> list[dict[str, Any]]:
    if kind == "article_indicators":
        result = _parse_article_indicators(workbook)
        if not result:
            raise ValueError(
                "Не найден классификатор статья → показатель. Нужны колонки "
                "«Показатель», «Канал сбыта» и хотя бы один точный ключ: "
                "«ERP-код статьи», «Полный путь статьи» или «Статья»."
            )
        return validate_reference_payload(kind, result)

    if kind == "intalev_cfos":
        result = _parse_intalev_cfos(workbook)
        if not result:
            raise ValueError(
                "Не найден каталог ЦФО Инталев. Нужна колонка «ЦФО Инталев» "
                "или «Наименование ЦФО»; код и полный путь необязательны."
            )
        return result

    flat = _parse_flat_interchange(workbook, kind)
    if flat is not None:
        return flat

    if kind == "erp_articles":
        result = _parse_real_erp_articles(workbook)
    elif kind == "organizations":
        result = _parse_real_organizations(workbook)
    else:
        result = _parse_real_scenarios(workbook)

    if not result:
        raise ValueError(
            "Не найден распознаваемый диапазон справочника. "
            "Загрузите известную ERP-выгрузку либо документированный плоский interchange-файл."
        )
    return result


def intalev_cfo_source_key(code: str, name: str, full_path: str = "") -> str:
    code = code.strip()
    full_path = full_path.strip()
    if code:
        return f"code:{code}"
    if full_path:
        return f"path:{full_path}"
    raise ValueError(
        "ЦФО Инталев не имеет точного ключа: нужен код или полный путь; "
        "одного наименования недостаточно"
    )


def reference_exact_key(kind: str, item: dict[str, Any]) -> str:
    """Return the documented exact identity without display-name guessing."""

    if kind == "erp_articles":
        code = _clean_scalar(item.get("code"))
        path = tuple(
            _clean_scalar(item.get(field))
            for field in ("expense_type", "expense_group", "source_article")
        )
        if not code or not path[-1]:
            raise ValueError(
                "ERP-статья не имеет точного ключа: нужны код и полный путь статьи"
            )
        return "erp_article:" + repr((code, *path))

    if kind == "organizations":
        code = _clean_scalar(item.get("code"))
        full_path = _clean_scalar(item.get("full_path"))
        if code:
            return f"organization:code:{code}"
        if full_path:
            return f"organization:path:{full_path}"
        raise ValueError(
            "Узел организации не имеет точного ключа: нужен код или полный путь"
        )

    if kind == "intalev_cfos":
        source_key = intalev_cfo_source_key(
            _clean_scalar(item.get("code")),
            _clean_scalar(item.get("name")),
            _clean_scalar(item.get("full_path")),
        )
        supplied = _clean_scalar(item.get("source_key"))
        if supplied and supplied != source_key:
            raise ValueError(
                "ЦФО Инталев содержит source_key, который не совпадает "
                "с точным кодом или полным путём"
            )
        return f"intalev_cfo:{source_key}"

    if kind == "article_indicators":
        code = _clean_scalar(item.get("erp_code"))
        path = _clean_scalar(item.get("article_path"))
        name = _clean_scalar(item.get("article_name"))
        if code:
            return f"article_indicator:code:{code}"
        if path:
            return f"article_indicator:path:{path}"
        if name:
            return f"article_indicator:name:{name}"
        raise ValueError(
            "Соответствие статья → показатель не имеет точного ключа: "
            "нужен ERP-код, полный путь или точное имя статьи"
        )

    raise ValueError(f"Для справочника {kind} не определён точный ключ")


def validate_reference_payload(
    kind: str,
    payload: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate all identities before persistence and collapse exact duplicates."""

    if kind not in {
        "erp_articles",
        "organizations",
        "intalev_cfos",
        "article_indicators",
    }:
        raise ValueError(f"Неизвестный тип справочника: {kind}")

    validated: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}
    article_codes: dict[str, str] = {}
    organization_nodes: dict[str, str] = {}

    for position, raw_item in enumerate(payload, start=1):
        if not isinstance(raw_item, dict):
            raise ValueError(
                f"Справочник {kind} содержит некорректную запись №{position}"
            )
        item = dict(raw_item)
        key = reference_exact_key(kind, item)

        if kind == "erp_articles":
            code = _clean_scalar(item.get("code"))
            previous_key = article_codes.get(code)
            if previous_key is not None and previous_key != key:
                raise ValueError(
                    "Конфликт exact key ERP-статьи: "
                    f"код {code} указан для разных полных путей"
                )
            article_codes[code] = key
        elif kind == "organizations":
            node_id = _clean_scalar(item.get("node_id"))
            if not node_id:
                raise ValueError(
                    "Узел организации не имеет стабильного node_id"
                )
            previous_key = organization_nodes.get(node_id)
            if previous_key is not None and previous_key != key:
                raise ValueError(
                    "Конфликт exact key организации: "
                    f"node_id {node_id} относится к разным записям"
                )
            organization_nodes[node_id] = key
        elif kind == "intalev_cfos":
            item["source_key"] = key.removeprefix("intalev_cfo:")
        else:
            item = {
                field: _clean_scalar(item.get(field))
                for field in (
                    "erp_code",
                    "article_path",
                    "article_name",
                    "indicator",
                    "sales_channel",
                )
            }
            key = reference_exact_key(kind, item)

        previous = by_key.get(key)
        if previous is None:
            by_key[key] = item
            validated.append(item)
            continue
        if previous != item:
            raise ValueError(
                f"Конфликт exact key в справочнике {kind}: {key}"
            )

    return validated


def _parse_article_indicators(workbook: Any) -> list[dict[str, Any]]:
    candidates: list[tuple[Any, int, dict[str, int]]] = []
    for sheet in workbook.worksheets:
        for row_number in range(1, min(sheet.max_row, 80) + 1):
            columns = _match_article_indicator_headers(
                [cell.value for cell in sheet[row_number]]
            )
            if columns:
                candidates.append((sheet, row_number, columns))
    if not candidates:
        return []
    if len(candidates) != 1:
        raise ValueError(
            "Классификатор содержит несколько структурно подходящих диапазонов "
            "статья → показатель"
        )

    sheet, header_row, columns = candidates[0]
    result: list[dict[str, Any]] = []
    for row_number in range(header_row + 1, sheet.max_row + 1):
        values = {
            field: sheet.cell(row_number, column)
            for field, column in columns.items()
        }
        if all(_is_blank(cell.value) for cell in values.values()):
            continue

        article_name = _clean_scalar(values["article_name"].value) if "article_name" in values else ""
        article_path = _clean_scalar(values["article_path"].value) if "article_path" in values else ""
        if not article_path and all(
            field in values for field in ("expense_type", "expense_group", "article_name")
        ):
            article_path = full_article_path(
                _clean_scalar(values["expense_type"].value),
                _clean_scalar(values["expense_group"].value),
                article_name,
            )

        item = {
            "erp_code": _code_text(values["erp_code"]) if "erp_code" in values else "",
            "article_path": article_path,
            "article_name": article_name,
            "indicator": _clean_scalar(values["indicator"].value),
            "sales_channel": _clean_scalar(values["sales_channel"].value),
        }
        try:
            reference_exact_key("article_indicators", item)
        except ValueError as exc:
            raise ValueError(
                f"Классификатор статья → показатель, строка {row_number}: {exc}"
            ) from exc
        result.append(item)
    return result


def _match_article_indicator_headers(values: list[Any]) -> dict[str, int] | None:
    normalized = {
        index: normalize_header(value)
        for index, value in enumerate(values, start=1)
    }
    columns: dict[str, int] = {}
    for field, aliases in ARTICLE_INDICATOR_HEADERS.items():
        normalized_aliases = {normalize_header(alias) for alias in aliases}
        matches = [index for index, value in normalized.items() if value in normalized_aliases]
        if len(matches) > 1:
            return None
        if matches:
            columns[field] = matches[0]

    if not {"indicator", "sales_channel"}.issubset(columns):
        return None
    if not {"erp_code", "article_path", "article_name"}.intersection(columns):
        return None
    return columns


def _parse_intalev_cfos(workbook: Any) -> list[dict[str, Any]]:
    candidates: list[tuple[int, Any, int, int, int | None, int | None]] = []
    for sheet in workbook.worksheets:
        for row_number in range(1, min(sheet.max_row, 80) + 1):
            headers = [normalize_header(cell.value) for cell in sheet[row_number]]

            def best_column(aliases: set[str], *, allow_contains: bool) -> int | None:
                scores: list[tuple[int, int]] = []
                normalized_aliases = {normalize_header(alias) for alias in aliases}
                for index, value in enumerate(headers, start=1):
                    if not value:
                        continue
                    quality = 3 if value in normalized_aliases else 0
                    if not quality and allow_contains:
                        for alias in normalized_aliases:
                            if len(alias) >= 4 and (alias in value or value in alias):
                                quality = max(quality, 2)
                    if quality:
                        scores.append((quality, index))
                if not scores:
                    return None
                best = max(score for score, _ in scores)
                columns = {column for score, column in scores if score == best}
                return next(iter(columns)) if len(columns) == 1 else None

            name_col = best_column(INTALEV_CFO_NAME_ALIASES, allow_contains=True)
            if name_col is None:
                continue
            code_col = best_column(INTALEV_CFO_CODE_ALIASES, allow_contains=False)
            path_col = best_column(INTALEV_CFO_PATH_ALIASES, allow_contains=True)
            if code_col == name_col:
                code_col = None
            if path_col == name_col:
                path_col = None
            if path_col == code_col:
                path_col = None
            data_count = sum(
                1
                for data_row in range(row_number + 1, sheet.max_row + 1)
                if not _is_blank(sheet.cell(data_row, name_col).value)
            )
            if data_count:
                score = data_count * 10 + (20 if code_col else 0) + (10 if path_col else 0)
                candidates.append((score, sheet, row_number, name_col, code_col, path_col))

    if not candidates:
        return []
    candidates.sort(key=lambda item: item[0], reverse=True)
    best_score = candidates[0][0]
    best = [item for item in candidates if item[0] == best_score]
    if len(best) != 1:
        raise ValueError("Классификатор содержит несколько одинаково подходящих диапазонов ЦФО Инталев")

    _, sheet, header_row, name_col, code_col, path_col = best[0]
    result: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    for row_number in range(header_row + 1, sheet.max_row + 1):
        name = _clean_scalar(sheet.cell(row_number, name_col).value)
        code = _code_text(sheet.cell(row_number, code_col)) if code_col else ""
        full_path = _clean_scalar(sheet.cell(row_number, path_col).value) if path_col else ""
        if not name and not code and not full_path:
            continue
        if not name:
            name = full_path.split("→")[-1].strip() if full_path else code
        if not name:
            raise ValueError(
                f"Каталог ЦФО Инталев содержит запись без наименования: строка {row_number}"
            )
        try:
            source_key = intalev_cfo_source_key(code, name, full_path)
        except ValueError as exc:
            raise ValueError(
                f"Каталог ЦФО Инталев, строка {row_number}: {exc}"
            ) from exc
        item = {
            "source_key": source_key,
            "code": code,
            "name": name,
            "full_path": full_path,
        }
        if source_key in seen:
            if seen[source_key] != item:
                raise ValueError(
                    f"Каталог ЦФО Инталев содержит конфликтующий ключ: "
                    f"{code or full_path or name}"
                )
            # Combined article classifiers often repeat one CFO on many rows.
            # Exact duplicates describe one source entity and are collapsed.
            continue
        seen[source_key] = item
        result.append(item)
    return result


def _parse_flat_interchange(workbook: Any, kind: str) -> list[dict[str, Any]] | None:
    required = {
        "erp_articles": ERP_HEADERS,
        "organizations": ORG_HEADERS,
        "scenarios": SCENARIO_HEADERS,
    }[kind]
    candidates: list[tuple[Any, int, dict[str, int]]] = []
    for sheet in workbook.worksheets:
        for row_number in range(1, min(sheet.max_row, 80) + 1):
            values = [cell.value for cell in sheet[row_number]]
            columns = _match_headers(values, required)
            if columns:
                candidates.append((sheet, row_number, columns))
    if not candidates:
        return None
    if len(candidates) != 1:
        raise ValueError("Справочник содержит несколько плоских структурно подходящих диапазонов")

    sheet, header_row, columns = candidates[0]
    rows: list[dict[str, Any]] = []
    for row_number in range(header_row + 1, sheet.max_row + 1):
        cells = {field: sheet.cell(row_number, column) for field, column in columns.items()}
        if all(_is_blank(cell.value) for cell in cells.values()):
            continue
        rows.append(
            {
                field: _clean_flat_cell(field, cell)
                for field, cell in cells.items()
            }
        )
    return rows


def _parse_real_erp_articles(workbook: Any) -> list[dict[str, Any]]:
    sheet, first_data_row, name_col, code_col = _best_real_layout(workbook, "erp_articles")
    stack: list[str] = []
    result: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for row_number in range(first_data_row, sheet.max_row + 1):
        raw_name = sheet.cell(row_number, name_col).value
        code_cell = sheet.cell(row_number, code_col)
        code = _code_text(code_cell)
        is_code_row = bool(
            code
            and not _looks_like_header(code, REAL_EXPORT_HEADERS["erp_articles"]["code"])
        )

        # In the documented ERP export, the hierarchy node is the nearest
        # preceding non-code row. A value beside the code is technical
        # analytics and must not replace the official article in the stack.
        if not is_code_row and not _is_blank(raw_name):
            name = _hierarchy_text(raw_name)
            if not _looks_like_header(name, REAL_EXPORT_HEADERS["erp_articles"]["name"]):
                level = _erp_row_level(sheet, row_number, name_col, raw_name)
                if level > len(stack):
                    raise ValueError(
                        "ERP-иерархия содержит пропущенный уровень: "
                        f"лист '{sheet.title}', строка {row_number}"
                    )
                _set_stack(stack, level, name)

        if not is_code_row:
            continue
        if code in seen_codes:
            raise ValueError(f"ERP-справочник статей содержит повторяющийся код: {code}")
        if not stack:
            raise ValueError(
                "Строка с ERP-кодом не имеет предшествующего узла иерархии: "
                f"лист '{sheet.title}', строка {row_number}, код {code}"
            )

        article = stack[-1]
        expense_type = stack[0] if len(stack) >= 2 else ""
        expense_group = stack[-2] if len(stack) >= 3 else ""
        result.append(
            {
                "code": code,
                "name": article,
                "expense_type": expense_type,
                "expense_group": expense_group,
                "source_article": article,
            }
        )
        seen_codes.add(code)

    return result


def _parse_real_organizations(workbook: Any) -> list[dict[str, Any]]:
    sheet, first_data_row, name_col, code_col = _best_real_layout(workbook, "organizations")
    path_col = _find_optional_column(
        sheet,
        first_data_row,
        PATH_ALIASES,
        excluded_columns={name_col, code_col},
    )
    cfo_name_col = _find_exact_header_column(
        sheet,
        ORG_CFO_NAME_ALIASES,
        excluded_columns={name_col, code_col},
    )
    organization_unit_col = _find_exact_header_column(
        sheet,
        ORG_UNIT_NAME_ALIASES,
        excluded_columns={name_col, code_col},
    )

    stack: list[str] = []
    coded_stack: dict[int, str] = {}
    raw_nodes: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for row_number in range(first_data_row, sheet.max_row + 1):
        raw_name = sheet.cell(row_number, name_col).value
        code_cell = sheet.cell(row_number, code_col)

        level = 0
        if not _is_blank(raw_name):
            name = _hierarchy_text(raw_name)
            if _looks_like_header(name, REAL_EXPORT_HEADERS["organizations"]["name"]):
                continue
            level = _row_level(sheet, row_number, name_col, raw_name)
            _set_stack(stack, level, name)
        elif stack:
            name = stack[-1]
            level = max(len(stack) - 1, 0)
        else:
            continue

        explicit_path = ""
        if path_col is not None:
            explicit_path = _clean_scalar(sheet.cell(row_number, path_col).value)
        full_path = explicit_path or " → ".join(stack)
        source_department = _clean_scalar(raw_name)
        cfo_name = (
            _clean_scalar(sheet.cell(row_number, cfo_name_col).value)
            if cfo_name_col is not None
            else ""
        )
        organization_unit_name = (
            _clean_scalar(sheet.cell(row_number, organization_unit_col).value)
            if organization_unit_col is not None
            else ""
        )
        code = _code_text(code_cell)
        if _looks_like_header(code, REAL_EXPORT_HEADERS["organizations"]["code"]):
            continue
        if not code and not (source_department and cfo_name and organization_unit_name):
            continue
        if code and code in seen_codes:
            raise ValueError(f"Справочник организаций содержит повторяющийся код: {code}")
        if not code:
            full_path = " → ".join(
                (organization_unit_name, cfo_name, source_department)
            )
        node_id = code or f"organization:path:{full_path}"

        parent_id = None
        for parent_level in range(level - 1, -1, -1):
            if parent_level in coded_stack:
                parent_id = coded_stack[parent_level]
                break

        raw_nodes.append(
            {
                "node_id": node_id,
                "code": code,
                "name": name,
                "parent_id": parent_id,
                "full_path": full_path,
                "source_department": source_department,
                "cfo_name": cfo_name,
                "organization_unit_name": organization_unit_name,
            }
        )
        if code:
            seen_codes.add(code)
            coded_stack[level] = code
            for deeper in [item for item in coded_stack if item > level]:
                del coded_stack[deeper]

    if path_col is not None:
        by_path = {node["full_path"]: node["node_id"] for node in raw_nodes}
        for node in raw_nodes:
            separator = " → " if " → " in node["full_path"] else None
            if separator:
                parent_path = node["full_path"].rsplit(separator, 1)[0]
                node["parent_id"] = by_path.get(parent_path)

    return raw_nodes


def _parse_real_scenarios(workbook: Any) -> list[dict[str, Any]]:
    sheet, first_data_row, name_col, code_col = _best_real_layout(workbook, "scenarios")
    result: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for row_number in range(first_data_row, sheet.max_row + 1):
        raw_name = sheet.cell(row_number, name_col).value
        if _is_blank(raw_name):
            continue
        name = str(raw_name).strip()
        if not name or _looks_like_header(name, REAL_EXPORT_HEADERS["scenarios"]["name"]):
            continue

        code = _code_text(sheet.cell(row_number, code_col))
        year_match = re.search(r"(?<!\d)(20\d{2}|21\d{2})(?!\d)", name.replace("_", " "))
        year = int(year_match.group(1)) if year_match else 0
        identity = f"{name}\0{year}"
        if identity in seen_names:
            continue
        seen_names.add(identity)
        result.append(
            {
                "name": name,
                "year": str(year),
                "erp_code": code,
                "comment": "",
            }
        )
    return result


def _best_real_layout(workbook: Any, kind: str) -> tuple[Any, int, int, int]:
    aliases = REAL_EXPORT_HEADERS[kind]
    candidates: list[tuple[int, Any, int, int, int]] = []

    for sheet in workbook.worksheets:
        name_headers = _header_positions(sheet, aliases["name"], allow_contains=True)
        code_headers = _header_positions(sheet, aliases["code"], allow_contains=True)

        for name_row, name_col, name_quality in name_headers:
            for code_row, code_col, code_quality in code_headers:
                if name_col == code_col:
                    continue
                first_data_row = max(name_row, code_row) + 1
                score = _layout_score(sheet, first_data_row, name_col, code_col, kind)
                if score <= 0:
                    continue
                score += name_quality * 50 + code_quality * 50
                score += max(0, 30 - abs(name_row - code_row))
                if name_col < code_col:
                    score += 20
                candidates.append((score, sheet, first_data_row, name_col, code_col))

    if not candidates:
        expected_name = " / ".join(sorted(aliases["name"]))
        expected_code = " / ".join(sorted(aliases["code"]))
        raise ValueError(
            "Не найден заголовок известной ERP-выгрузки. "
            f"Ожидается поле наименования ({expected_name}) и поле кода ({expected_code}); "
            "они могут находиться на соседних строках заголовка."
        )

    candidates.sort(key=lambda item: item[0], reverse=True)
    _, sheet, first_data_row, name_col, code_col = candidates[0]
    return sheet, first_data_row, name_col, code_col


def _header_positions(
    sheet: Any,
    aliases: set[str],
    *,
    allow_contains: bool,
) -> list[tuple[int, int, int]]:
    results: list[tuple[int, int, int]] = []
    max_row = min(sheet.max_row, MAX_HEADER_SCAN_ROWS)
    for row_number in range(1, max_row + 1):
        for column_number, cell in enumerate(sheet[row_number], start=1):
            quality = _header_quality(cell.value, aliases, allow_contains=allow_contains)
            if quality:
                results.append((row_number, column_number, quality))
    return results


def _header_quality(value: Any, aliases: set[str], *, allow_contains: bool) -> int:
    normalized = normalize_header(value)
    if not normalized:
        return 0

    normalized_aliases = {normalize_header(alias) for alias in aliases}
    if normalized in normalized_aliases:
        return 3

    if "код" in normalized_aliases and re.match(r"^код(?:\s|$|\()", normalized):
        return 2

    if allow_contains:
        for alias in normalized_aliases:
            if len(alias) >= 4 and (alias in normalized or normalized in alias):
                return 2

    compact = re.sub(r"[^0-9a-zа-я]+", " ", normalized).strip()
    for alias in normalized_aliases:
        compact_alias = re.sub(r"[^0-9a-zа-я]+", " ", alias).strip()
        if compact == compact_alias:
            return 2
        if allow_contains and len(compact_alias) >= 4 and compact_alias in compact:
            return 1
    return 0


def _layout_score(
    sheet: Any,
    first_data_row: int,
    name_col: int,
    code_col: int,
    kind: str,
) -> int:
    if first_data_row > sheet.max_row:
        return 0

    code_values: list[str] = []
    name_count = 0
    rows_with_both = 0
    for row_number in range(first_data_row, sheet.max_row + 1):
        name_value = sheet.cell(row_number, name_col).value
        code_value = _code_text(sheet.cell(row_number, code_col))
        if not _is_blank(name_value):
            name_count += 1
        if code_value and not _looks_like_header(code_value, REAL_EXPORT_HEADERS[kind]["code"]):
            code_values.append(code_value)
            if not _is_blank(name_value):
                rows_with_both += 1

    if not code_values or not name_count:
        return 0

    unique_codes = len(set(code_values))
    score = min(len(code_values), 1000) * 4 + min(unique_codes, 1000) * 6
    score += min(name_count, 1000) + min(rows_with_both, 500) * 2
    if unique_codes == len(code_values):
        score += 30
    return score


def _find_optional_column(
    sheet: Any,
    first_data_row: int,
    aliases: set[str],
    *,
    excluded_columns: set[int] | None = None,
) -> int | None:
    matches: list[tuple[int, int]] = []
    excluded = excluded_columns or set()
    scan_to = min(max(first_data_row, 1), MAX_HEADER_SCAN_ROWS)
    for row_number in range(1, scan_to + 1):
        for index, cell in enumerate(sheet[row_number], start=1):
            if index in excluded:
                continue
            quality = _header_quality(cell.value, aliases, allow_contains=True)
            if quality:
                matches.append((quality, index))
    if not matches:
        return None
    matches.sort(reverse=True)
    best_quality = matches[0][0]
    best_columns = {column for quality, column in matches if quality == best_quality}
    return next(iter(best_columns)) if len(best_columns) == 1 else None


def _find_exact_header_column(
    sheet: Any,
    aliases: set[str],
    *,
    excluded_columns: set[int] | None = None,
) -> int | None:
    normalized_aliases = {normalize_header(alias) for alias in aliases}
    excluded = excluded_columns or set()
    matches: set[int] = set()
    for row_number in range(1, min(sheet.max_row, MAX_HEADER_SCAN_ROWS) + 1):
        for column_number, cell in enumerate(sheet[row_number], start=1):
            if column_number in excluded:
                continue
            if normalize_header(cell.value) in normalized_aliases:
                matches.add(column_number)
    return next(iter(matches)) if len(matches) == 1 else None


def _row_level(sheet: Any, row_number: int, name_col: int, value: Any) -> int:
    cell = sheet.cell(row_number, name_col)
    indent = int(cell.alignment.indent or 0)
    outline = int(sheet.row_dimensions[row_number].outlineLevel or 0)
    text = str(value)
    leading = len(text) - len(text.lstrip(" \t"))
    leading_level = leading // 2
    return max(indent, outline, leading_level)


def _erp_row_level(sheet: Any, row_number: int, name_col: int, value: Any) -> int:
    cell = sheet.cell(row_number, name_col)
    indent = int(cell.alignment.indent or 0)
    outline = int(sheet.row_dimensions[row_number].outlineLevel or 0)
    text = str(value)
    prefix = text[: len(text) - len(text.lstrip(" \t"))]
    spaces = prefix.count(" ")
    tabs = prefix.count("\t")

    if indent % ERP_INDENT_UNITS_PER_LEVEL:
        raise ValueError(
            "ERP-иерархия использует неподдерживаемый отступ: "
            f"лист '{sheet.title}', строка {row_number}, indent={indent}; "
            f"ожидается кратность {ERP_INDENT_UNITS_PER_LEVEL}"
        )
    if spaces % ERP_INDENT_UNITS_PER_LEVEL:
        raise ValueError(
            "ERP-иерархия использует неоднозначный текстовый отступ: "
            f"лист '{sheet.title}', строка {row_number}, spaces={spaces}"
        )

    levels = {
        level
        for level in (
            indent // ERP_INDENT_UNITS_PER_LEVEL,
            outline,
            spaces // ERP_INDENT_UNITS_PER_LEVEL + tabs,
        )
        if level > 0
    }
    if len(levels) > 1:
        raise ValueError(
            "ERP-иерархия содержит противоречивые уровни отступа: "
            f"лист '{sheet.title}', строка {row_number}, "
            f"indent={indent}, outlineLevel={outline}, leading={len(prefix)}"
        )
    return next(iter(levels), 0)


def _set_stack(stack: list[str], level: int, name: str) -> None:
    level = max(level, 0)
    if level > len(stack):
        level = len(stack)
    del stack[level:]
    stack.append(name)


def _hierarchy_text(value: Any) -> str:
    return str(value).lstrip(" \t\r\n")


def _looks_like_header(value: Any, aliases: set[str]) -> bool:
    # Contains matching is useful while locating header cells, but data values
    # such as "Сценарий отчетности КИК" must not be discarded as headers.
    return _header_quality(value, aliases, allow_contains=False) > 0


def _match_headers(values: list[Any], required: dict[str, set[str]]) -> dict[str, int] | None:
    normalized = {index: normalize_header(value) for index, value in enumerate(values, start=1)}
    columns: dict[str, int] = {}
    for field, aliases in required.items():
        normalized_aliases = {normalize_header(alias) for alias in aliases}
        matches = [index for index, value in normalized.items() if value in normalized_aliases]
        if len(matches) != 1:
            return None
        columns[field] = matches[0]
    return columns


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _clean_scalar(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _clean_flat_cell(field: str, cell: Any) -> str:
    if cell.value is None:
        return ""
    if field in {"code", "node_id", "parent_id", "erp_code"}:
        return _code_text(cell)
    text = str(cell.value)
    if field in {"year", "comment"}:
        return text.strip()
    return text


def _code_text(cell: Any) -> str:
    value = cell.value
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        number_format = str(cell.number_format or "")
        if re.fullmatch(r"0+", number_format):
            return f"{value:0{len(number_format)}d}"
        return str(value)
    if isinstance(value, float) and value.is_integer():
        number_format = str(cell.number_format or "")
        if re.fullmatch(r"0+", number_format):
            return f"{int(value):0{len(number_format)}d}"
        return str(int(value))
    return str(value).strip()


def erp_articles(payload: list[dict[str, Any]]) -> list[ERPArticle]:
    return [ERPArticle(**item) for item in validate_reference_payload("erp_articles", payload)]


def organization_nodes(payload: list[dict[str, Any]]) -> list[OrganizationNode]:
    return [
        OrganizationNode(
            node_id=item["node_id"],
            code=item["code"],
            name=item["name"],
            parent_id=item["parent_id"] or None,
            full_path=item["full_path"],
            source_department=_clean_scalar(item.get("source_department")),
            cfo_name=_clean_scalar(item.get("cfo_name")),
            organization_unit_name=_clean_scalar(item.get("organization_unit_name")),
        )
        for item in validate_reference_payload("organizations", payload)
    ]


def intalev_cfos(payload: list[dict[str, Any]]) -> list[IntalevCFO]:
    return [
        IntalevCFO(**item)
        for item in validate_reference_payload("intalev_cfos", payload)
    ]


def article_indicator_rules(
    payload: list[dict[str, Any]],
) -> list[ArticleIndicatorRule]:
    return [
        ArticleIndicatorRule(**item)
        for item in validate_reference_payload("article_indicators", payload)
    ]
