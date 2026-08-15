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


def _predicates(condition: str) -> tuple[FormulaPredicate, ...]:
    result: list[FormulaPredicate] = []
    aliases = {
        "Организация": "organization",
        "ЦФО": "cfo",
        "Регион": "region",
        "Регион продаж": "region",
        "Сеть": "network",
        "Канал сбыта": "network",
        "Код статьи": "article_code",
    }
    for part in re.split(r"[;\r\n]+", condition):
        if "=" not in part:
            continue
        label, expected = (_clean(value) for value in part.split("=", 1))
        field = aliases.get(label)
        if field and expected:
            result.append(FormulaPredicate(field=field, expected=expected))
    return tuple(dict.fromkeys(result))


def _disclosure_groups(condition: str) -> tuple[str, ...]:
    groups: list[str] = []
    for match in DISCLOSURE_GROUP_START_RE.finditer(condition):
        start = match.end()
        depth = 1
        end = start
        while end < len(condition) and depth:
            if condition[end] == "(":
                depth += 1
            elif condition[end] == ")":
                depth -= 1
            end += 1
        if depth:
            continue
        raw = condition[start : end - 1]
        item_start = 0
        nested = 0
        for index, character in enumerate(raw):
            if character == "(":
                nested += 1
            elif character == ")" and nested:
                nested -= 1
            elif character == "," and nested == 0:
                if value := _clean(raw[item_start:index]):
                    groups.append(value)
                item_start = index + 1
        if value := _clean(raw[item_start:]):
            groups.append(value)
    return tuple(dict.fromkeys(groups))


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
        groups = _disclosure_groups(condition)
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
                predicates=_predicates(condition),
            )
        )
    return tuple(parsed)
