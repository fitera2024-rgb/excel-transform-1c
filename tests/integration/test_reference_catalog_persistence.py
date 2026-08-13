from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment

from excel_transform_1c.application.service import WorkflowService


def _bytes(workbook: Workbook) -> bytes:
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _split_header_reference(kind: str, *, supplement: bool = False) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Лист_1"

    if kind == "erp_articles":
        sheet.cell(3, 1, "Иерархия статей доходов и расходов")
        sheet.cell(6, 15, "Код элемента")
        rows = [
            (8, "Административные", 0, None),
            (9, "Связь", 2, None),
            (10, "Интернет" if not supplement else "Телефония", 4, None),
            (11, None, 0, "ERP-001" if not supplement else "ERP-003"),
        ]
        for row, name, level, code in rows:
            if name is not None:
                cell = sheet.cell(row, 1, name)
                cell.alignment = Alignment(indent=level)
            if code:
                sheet.cell(row, 15, code)

    elif kind == "organizations":
        sheet.cell(2, 1, "Иерархия организаций")
        sheet.cell(5, 39, "Код справочника")
        rows = (
            [
                (8, "Группа", "ORG-1", 0),
                (9, "ПС", "ORG-2", 1),
                (10, "ЦФО 1", "ORG-3", 2),
            ]
            if not supplement
            else [
                (8, "Группа", "ORG-1", 0),
                (9, "ПС", "ORG-2", 1),
                (10, "ЦФО 1 обновлён", "ORG-3", 2),
                (11, "ЦФО 2", "ORG-4", 2),
            ]
        )
        for row, name, code, level in rows:
            cell = sheet.cell(row, 1, name)
            cell.alignment = Alignment(indent=level)
            sheet.cell(row, 39, code)

    elif kind == "scenarios":
        sheet.cell(4, 1, "Сценарии бюджетирования")
        sheet.cell(7, 19, "Код записи")
        rows = (
            [
                (9, "ПЛАН 2026", 10),
                (10, "Факт", 1),
            ]
            if not supplement
            else [
                (9, "ПЛАН 2026", 10),
                (10, "ПЛАН 2027", 11),
            ]
        )
        for row, name, code in rows:
            sheet.cell(row, 1, name)
            code_cell = sheet.cell(row, 19, code)
            code_cell.number_format = "00000"
    else:
        raise AssertionError(kind)

    return _bytes(workbook)


def test_real_exports_accept_split_multiline_header_rows(tmp_path):
    service = WorkflowService(tmp_path / "runtime")

    assert service.upload_reference(
        "erp_articles", _split_header_reference("erp_articles")
    ) == 1
    assert service.upload_reference(
        "organizations", _split_header_reference("organizations")
    ) == 3
    assert service.upload_reference(
        "scenarios", _split_header_reference("scenarios")
    ) == 2

    assert service.erp_articles()[0].code == "ERP-001"
    assert [node.code for node in service.organization_nodes()] == [
        "ORG-1",
        "ORG-2",
        "ORG-3",
    ]
    plan = next(
        scenario
        for scenario in service.store.list_scenarios()
        if scenario.name == "ПЛАН 2026"
    )
    assert plan.erp_code == "00010"


def test_organization_catalog_is_global_persistent_and_supplemented(tmp_path):
    runtime = tmp_path / "runtime"
    first = WorkflowService(runtime)

    first.upload_reference(
        "organizations", _split_header_reference("organizations")
    )
    first.upload_reference(
        "organizations",
        _split_header_reference("organizations", supplement=True),
    )

    assert first.reference_counts()["organizations"] == 4
    assert {
        node.code: node.name for node in first.organization_nodes()
    }["ORG-3"] == "ЦФО 1 обновлён"

    restarted = WorkflowService(runtime)
    assert restarted.reference_counts()["organizations"] == 4
    assert {node.code for node in restarted.allowed_organization_nodes()} == {
        "ORG-1",
        "ORG-2",
        "ORG-3",
        "ORG-4",
    }


def test_scenario_catalog_is_loaded_once_and_incrementally_supplemented(tmp_path):
    runtime = tmp_path / "runtime"
    first = WorkflowService(runtime)

    first.upload_reference("scenarios", _split_header_reference("scenarios"))
    original_plan = next(
        scenario
        for scenario in first.store.list_scenarios()
        if scenario.name == "ПЛАН 2026"
    )

    first.upload_reference(
        "scenarios",
        _split_header_reference("scenarios", supplement=True),
    )

    scenarios = first.store.list_scenarios()
    assert {scenario.name for scenario in scenarios} == {
        "ПЛАН 2026",
        "ПЛАН 2027",
        "Факт",
    }
    assert next(
        scenario for scenario in scenarios if scenario.name == "ПЛАН 2026"
    ).scenario_id == original_plan.scenario_id

    restarted = WorkflowService(runtime)
    assert {
        scenario.name for scenario in restarted.store.list_scenarios()
    } == {"ПЛАН 2026", "ПЛАН 2027", "Факт"}
