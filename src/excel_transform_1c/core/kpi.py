from __future__ import annotations

from .models import IndicatorType, KPIResult, PreviewRecord


def kpi_result_from_record(record: PreviewRecord) -> KPIResult:
    """Map one resolved BDR KPI period without using expense/article fields."""

    if record.source_kind != "bdr_full" or record.indicator_type != IndicatorType.KPI:
        raise ValueError("Запись не является KPI полного БДР")

    department = record.source_cfo or record.cfo
    cfo = record.erp_department or record.cfo
    return KPIResult(
        organization=record.organization_unit or record.organization,
        organization_code=record.organization_unit_code,
        department=department,
        department_name=record.department,
        cfo=cfo,
        cfo_code=record.cfo_code,
        indicator_type=record.indicator_type_label,
        indicator_name=record.indicator or record.source_article,
        period=f"{record.month:02d}.{record.year}",
        value=record.amount,
    )


def kpi_results_from_records(records: list[PreviewRecord]) -> list[KPIResult]:
    return [
        kpi_result_from_record(record)
        for record in records
        if record.source_kind == "bdr_full"
        and record.indicator_type == IndicatorType.KPI
    ]
