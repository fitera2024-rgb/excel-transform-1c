from __future__ import annotations

import re
from collections.abc import Iterable

from .opiu_rule_models import (
    AnalyticInputRow,
    ERPSourceRule,
    FormulaInputRow,
    FormulaPredicate,
    OPIUAnalyticRule,
    OPIUFormulaRule,
)


SOURCE_TOKEN_RE = re.compile(r"\[([^\[\]]+)\]")
MXL_CELL_RE = re.compile(r"\{(?:16|20),\d+,(.*?)\},0\},([^\r\n]*)", re.DOTALL)
MXL_VALUE_RE = re.compile(r'\{"(?:#|ru)","((?:[^"]|"")*)"\}', re.DOTALL)
DISCLOSURE_GROUP_START_RE = re.compile(r"\bВ(?:\s+ИЕРАРХИИ)?\s*\(")

ANALYTIC_DIMENSIONS = {
    "Организационные единицы": "organization",
    "Организация": "organization",
    "ЦФО": "cfo",
    "ЦФО (казначейство)": "cfo",
    "Регион": "region",
    "Регион продаж": "region",
    "Сеть": "network",
    "Сети": "network",
    "Канал сбыта": "network",
    "ИНТ номенклатура": "nomenclature",
    "Инт Номенклатура": "nomenclature",
}


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def _ternary_condition(formula: str) -> str:
    text = formula.strip()
    if not text.startswith("?("):
        return ""
    depth = 0
    for index, character in enumerate(text[2:], start=2):
        if character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        elif character == "," and depth == 0:
            return text[2:index].strip()
    return ""


def parse_formula_rows(rows: Iterable[FormulaInputRow]) -> tuple[OPIUFormulaRule, ...]:
    """Build the exact report hierarchy encoded by row indentation."""

    lineage: dict[int, str] = {}
    parsed: list[OPIUFormulaRule] = []
    for row in rows:
        name = _clean(row.name)
        formula = _clean(row.formula)
        if not name:
            continue
        indent = max(int(row.indent), 0)
        for level in tuple(lineage):
            if level >= indent:
                del lineage[level]
        ancestors = dict(lineage)
        lineage[indent] = name
        if not formula:
            continue

        lower_levels = [level for level in ancestors if level < indent]
        report_line = ancestors[min(lower_levels)] if lower_levels else name
        if indent >= 4:
            group_levels = [level for level in ancestors if 0 < level < indent]
            disclosure_group = (
                ancestors[max(group_levels)] if group_levels else report_line
            )
            article = name
        else:
            disclosure_group = name
            article = ""

        parsed.append(
            OPIUFormulaRule(
                source_row=row.source_row,
                report_line=report_line,
                report_indicator=name,
                disclosure_group=disclosure_group,
                article=article,
                formula=formula,
                formula_condition=_ternary_condition(formula),
                source_tokens=tuple(dict.fromkeys(SOURCE_TOKEN_RE.findall(formula))),
                measure=_clean(row.measure) or "Сумма",
            )
        )
    return tuple(parsed)


def parse_analytic_rows(
    rows: Iterable[AnalyticInputRow],
) -> tuple[OPIUAnalyticRule, ...]:
    parsed: list[OPIUAnalyticRule] = []
    for row in rows:
        report_indicator = _clean(row.name)
        if not report_indicator:
            continue
        analytics = tuple(
            dict.fromkeys(value for raw in row.analytics if (value := _clean(raw)))
        )
        dimensions = {ANALYTIC_DIMENSIONS.get(value, "") for value in analytics}
        parsed.append(
            OPIUAnalyticRule(
                source_row=row.source_row,
                report_indicator=report_indicator,
                required_analytics=analytics,
                organization_required="organization" in dimensions,
                region_required="region" in dimensions,
                network_required="network" in dimensions,
                cfo_required="cfo" in dimensions,
            )
        )
    return tuple(parsed)


def read_mxl_grid(content: bytes) -> tuple[tuple[str, ...], ...]:
    """Read the bounded textual table inside a MOXCEL payload."""

    if not content.startswith(b"MOXCEL"):
        raise ValueError("Источник ERP не имеет сигнатуры MOXCEL")
    bom = content.find(b"\xef\xbb\xbf")
    if bom < 0:
        raise ValueError("В MXL отсутствует текстовый UTF-8 payload")
    text = content[bom + 3 :].decode("utf-8", errors="strict")
    rows: list[tuple[str, ...]] = []
    current: list[str] = []
    width: int | None = None
    for match in MXL_CELL_RE.finditer(text):
        values = MXL_VALUE_RE.findall(match.group(1))
        value = values[-1].replace('""', '"').strip() if values else ""
        current.append(value)
        numbers = [int(item) for item in re.findall(r"\d+", match.group(2))]
        is_row_end = (
            len(numbers) >= 4
            and numbers[1] == 0
            and numbers[3] == 0
            and numbers[2] > 0
        )
        if not is_row_end:
            continue
        width = width or numbers[2]
        if numbers[2] != width or len(current) != width:
            raise ValueError("MXL содержит строки разной ширины")
        rows.append(tuple(current))
        current = []
    if current:
        if width is None or len(current) != width:
            raise ValueError("MXL содержит незавершённую строку")
        rows.append(tuple(current))
    if not rows:
        raise ValueError("MXL не содержит читаемой таблицы")
    return tuple(rows)


def _source_condition(description: str) -> str:
    marker = "Ист:"
    if marker not in description:
        return ""
    condition = description.split(marker, 1)[1].split("Пр:", 1)[0]
    return " ".join(condition.split())


def _split_top_level_and(condition: str) -> tuple[str, ...]:
    """Split an ERP condition by top-level Russian ``И`` conjunctions."""

    text = _clean(condition)
    if not text:
        return ()
    parts: list[str] = []
    depth = 0
    start = 0
    index = 0
    while index < len(text):
        character = text[index]
        if character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        elif depth == 0 and text.startswith(" И ", index):
            if value := _clean(text[start:index]):
                parts.append(value)
            index += 3
            start = index
            continue
        index += 1
    if value := _clean(text[start:]):
        parts.append(value)
    return tuple(parts)


def _split_balanced_values(raw: str) -> tuple[str, ...]:
    values: list[str] = []
    depth = 0
    start = 0
    for index, character in enumerate(raw):
        if character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        elif character == "," and depth == 0:
            if value := _clean(raw[start:index]):
                values.append(value)
            start = index + 1
    if value := _clean(raw[start:]):
        values.append(value)
    return tuple(dict.fromkeys(values))


def _parenthesized_argument(clause: str, prefix_pattern: str) -> str | None:
    match = re.match(prefix_pattern, clause)
    if not match:
        return None
    start = match.end()
    depth = 1
    index = start
    while index < len(clause) and depth:
        if clause[index] == "(":
            depth += 1
        elif clause[index] == ")":
            depth -= 1
        index += 1
    if depth or _clean(clause[index:]):
        return None
    return clause[start : index - 1]


def _parse_source_condition(
    condition: str,
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[FormulaPredicate, ...],
    tuple[str, ...],
]:
    """Parse only exact, semantically proven source filters.

    ``С1``/``КС1`` is the article dimension in the supplied OPIU ERP
    sources. Values from ``С2``/``С3`` can represent departments, channels or
    other analytics depending on ``Пр:`` and are therefore never promoted to a
    disclosure group without a separate proven mapping.
    """

    hierarchy_groups: list[str] = []
    article_values: list[str] = []
    predicates: list[FormulaPredicate] = []
    unsupported: list[str] = []
    predicate_aliases = {
        "Организация": "organization",
        "ЦФО": "cfo",
        "Регион": "region",
        "Регион продаж": "region",
        "Сеть": "network",
        "Канал сбыта": "network",
        "Код статьи": "article_code",
    }

    for clause in _split_top_level_and(condition):
        normalized = " ".join(clause.split())
        if normalized == "Организация В ПЕРИМЕТРЕ":
            continue

        raw = _parenthesized_argument(
            normalized,
            r"^(?:КС1|С1)\s+В\s+ИЕРАРХИИ\s*\(",
        )
        if raw is not None:
            hierarchy_groups.extend(_split_balanced_values(raw))
            continue

        raw = _parenthesized_argument(
            normalized,
            r"^(?:КС1|С1)\s+В\s*\(",
        )
        if raw is not None:
            article_values.extend(_split_balanced_values(raw))
            continue

        match = re.match(r"^(?:КС1|С1)\s*=\s*(.+)$", normalized)
        if match and (value := _clean(match.group(1))):
            article_values.append(value)
            continue

        match = re.match(
            r"^(Организация|ЦФО|Регион(?: продаж)?|Сеть|Канал сбыта|Код статьи)\s*=\s*(.+)$",
            normalized,
        )
        if match:
            label, expected = _clean(match.group(1)), _clean(match.group(2))
            field = predicate_aliases.get(label)
            if field and expected:
                predicates.append(FormulaPredicate(field=field, expected=expected))
                continue

        # Any other operator, dimension or perimeter variant is deliberately
        # not interpreted. The builder keeps it visible as unresolved and the
        # active resolver cannot silently ignore it.
        unsupported.append(normalized)

    return (
        tuple(dict.fromkeys(hierarchy_groups)),
        tuple(dict.fromkeys(article_values)),
        tuple(dict.fromkeys(predicates)),
        tuple(dict.fromkeys(unsupported)),
    )

def parse_erp_source_rules(content: bytes) -> tuple[ERPSourceRule, ...]:
    rows = read_mxl_grid(content)
    headers = rows[0]
    required = {
        "Код упрощенной формулы",
        "Наименование",
        "Описание",
        "Регистр ИБ",
        "Счет",
        "Корр счет",
        "Потребитель расчета",
        "Способ получения",
        "Код",
    }
    missing = sorted(required.difference(headers))
    if missing:
        raise ValueError(f"MXL не содержит обязательные поля: {', '.join(missing)}")
    indexes = {header: index for index, header in enumerate(headers)}
    parsed: list[ERPSourceRule] = []
    for row in rows[1:]:
        value = lambda header: _clean(row[indexes[header]])
        description = value("Описание")
        condition = _source_condition(description)
        groups, article_values, predicates, unsupported = _parse_source_condition(
            condition
        )
        register = value("Регистр ИБ")
        method = value("Способ получения")
        parsed.append(
            ERPSourceRule(
                formula_code=value("Код упрощенной формулы"),
                name=value("Наименование"),
                description=description,
                source=register or method,
                register=register,
                account=value("Счет"),
                corresponding_account=value("Корр счет"),
                consumer=value("Потребитель расчета"),
                method=method,
                code=value("Код"),
                formula_condition=condition,
                disclosure_groups=groups,
                article_values=article_values,
                predicates=predicates,
                unsupported_conditions=unsupported,
            )
        )
    return tuple(parsed)
