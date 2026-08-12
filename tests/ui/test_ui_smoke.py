import json
import re

import pytest
from fastapi.testclient import TestClient

from excel_transform_1c.ui.app import create_app
from tests.helpers.workbooks import reference_bytes, workbook_bytes


pytestmark = pytest.mark.ui


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "runtime")
    test_client = TestClient(app)
    for kind in ("erp_articles", "organizations", "scenarios"):
        response = test_client.post(
            "/references",
            data={"kind": kind},
            files={
                "reference_file": (
                    f"synthetic-{kind}.xlsx",
                    reference_bytes(kind),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
    return test_client


def upload(client, payload: bytes, **form):
    scenario_id = client.app.state.workflow.store.list_scenarios()[0].scenario_id
    data = {
        "reporting_unit": "ПС",
        "organization_node_id": "ps",
        "scenario_id": scenario_id,
        "year": "2026",
        "period_selector_present": "1",
        "all_year": "1",
        **form,
    }
    return client.post(
        "/uploads",
        data=data,
        files={
            "budget_file": (
                "synthetic.xlsx",
                payload,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        follow_redirects=True,
    )


def run_id_from(response) -> str:
    match = re.search(r"/runs/([a-f0-9]+)", str(response.url))
    assert match
    return match.group(1)


def erp_catalog_from(response) -> list[dict[str, str]]:
    match = re.search(
        r'<script id="erp-catalog-data" type="application/json">(.*?)</script>',
        response.text,
        re.DOTALL,
    )
    assert match
    return json.loads(match.group(1))


def test_home_uses_hierarchical_organization_selector_without_access_block(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'data-testid="organization-root"' in response.text
    assert 'data-testid="organization-node"' in response.text
    assert 'data-root-id="root"' in response.text
    assert "После выбора верхней ветки доступны" in response.text
    assert "Область доступа" not in response.text
    assert "Применить поддеревья" not in response.text
    assert 'data-testid="scenario-select"' in response.text
    assert "ПЛАН 2026" in response.text
    assert 'data-testid="all-year"' in response.text
    assert 'name="all_year" value="1" type="checkbox" checked' in response.text


def test_legacy_delegation_is_cleared_and_all_nodes_remain_available(tmp_path):
    runtime = tmp_path / "runtime"
    first = TestClient(create_app(runtime))
    for kind in ("erp_articles", "organizations", "scenarios"):
        first.post(
            "/references",
            data={"kind": kind},
            files={
                "reference_file": (
                    f"synthetic-{kind}.xlsx",
                    reference_bytes(kind),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            follow_redirects=True,
        )
    first.app.state.workflow.store.set_delegations("local", ["ps"])

    restarted = TestClient(create_app(runtime))
    assert restarted.app.state.workflow.store.get_delegations("local") == []
    response = restarted.get("/")
    assert 'value="other"' in response.text
    assert "Сосед (ORG-5)" in response.text


def test_happy_path_to_preview_and_export(client):
    response = upload(client, workbook_bytes())
    assert response.status_code == 200
    assert "24" in response.text
    assert "Максимально полный preview" in response.text
    run_id = run_id_from(response)
    exported = client.get(f"/runs/{run_id}/export")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith(
        "application/vnd.openxmlformats"
    )


def test_explicit_month_selection_filters_view_but_keeps_full_result(client):
    response = upload(
        client,
        workbook_bytes(),
        all_year="",
        months=["1", "2"],
    )
    assert response.status_code == 200
    run = client.app.state.workflow.get_run(run_id_from(response))
    assert len(run.records) == 24
    assert len(run.visible_records()) == 4


def test_period_requires_all_year_or_at_least_one_month(client):
    response = upload(client, workbook_bytes(), all_year="", months=[])
    assert response.status_code == 200
    assert "Выберите «Весь год» либо хотя бы один месяц" in response.text


def test_attention_path_with_manual_erp_correction(client):
    response = upload(client, workbook_bytes(missing_mapping=True))
    run_id = run_id_from(response)
    assert "Точное соответствие ERP не найдено" in response.text
    corrected = client.post(
        f"/runs/{run_id}/correct",
        data={
            "source_row": 3,
            "erp_code": "ERP-001",
            "tax": "",
            "department": "",
            "cfo": "",
            "expense_group": "",
            "source_article": "",
        },
        follow_redirects=True,
    )
    assert "Исправление применено без повторного запуска" in corrected.text
    assert "ERP-001" in corrected.text


def test_attention_editor_is_grouped_by_source_row_and_shows_business_context(client):
    response = upload(
        client,
        workbook_bytes(missing_mapping=True, department_error=True),
    )

    assert '<select name="source_row">' not in response.text
    assert response.text.count('data-testid="attention-editor"') == 1
    assert 'data-source-row="3"' in response.text
    assert 'name="source_row" value="3"' in response.text
    assert "Административные → Связь → Нет в ERP" in response.text
    assert "Точное соответствие ERP не найдено" in response.text
    assert "Не заполнено поле: департамент" in response.text
    assert "Произвольное имя!H3" in response.text
    assert "Произвольное имя!C3" in response.text
    assert "Затронутые месяцы" in response.text
    assert "Январь, Февраль" in response.text
    assert "Ноябрь, Декабрь" in response.text


def test_erp_cascade_uses_exact_catalog_paths_and_keeps_duplicate_names_separate(client):
    store = client.app.state.workflow.store
    articles = store.load_reference("erp_articles")
    articles.extend(
        [
            {
                "code": "ERP-DUP-A",
                "name": "Общая статья ERP A",
                "expense_type": "Административные",
                "expense_group": "Связь",
                "source_article": "Общая статья",
            },
            {
                "code": "ERP-DUP-B",
                "name": "Общая статья ERP B",
                "expense_type": "Коммерческие",
                "expense_group": "Маркетинг",
                "source_article": "Общая статья",
            },
        ]
    )
    store.replace_reference("erp_articles", articles)

    response = upload(client, workbook_bytes(missing_mapping=True))
    catalog = erp_catalog_from(response)
    duplicate_paths = {
        (item["expenseType"], item["expenseGroup"], item["sourceArticle"], item["code"])
        for item in catalog
        if item["sourceArticle"] == "Общая статья"
    }

    assert duplicate_paths == {
        ("Административные", "Связь", "Общая статья", "ERP-DUP-A"),
        ("Коммерческие", "Маркетинг", "Общая статья", "ERP-DUP-B"),
    }
    assert any(item["sourceArticle"] == "Удалить" for item in catalog)
    assert response.text.index('data-erp-level="type"') < response.text.index(
        'data-erp-level="group"'
    )
    assert response.text.index('data-erp-level="group"') < response.text.index(
        'data-erp-level="article"'
    )
    assert response.text.index('data-erp-level="article"') < response.text.index(
        'data-erp-level="code"'
    )

    script = client.get("/static/run.js").text
    assert "article.expenseType === expenseType" in script
    assert "article.expenseGroup === expenseGroup" in script
    assert "article.sourceArticle === sourceArticle" in script
    assert "candidates.length === 1" in script
    assert 'const EMPTY_LEVEL = "__EMPTY__"' in script
    assert "selectedLevelValue(codeSelect)" in script


def test_erp_cascade_preserves_empty_group_for_multiple_articles_and_codes(client):
    store = client.app.state.workflow.store
    articles = store.load_reference("erp_articles")
    articles.extend(
        [
            {
                "code": "ERP-EMPTY-A1",
                "name": "Корневая статья A, вариант 1",
                "expense_type": "Прочие доходы",
                "expense_group": "",
                "source_article": "Корневая статья A",
            },
            {
                "code": "ERP-EMPTY-A2",
                "name": "Корневая статья A, вариант 2",
                "expense_type": "Прочие доходы",
                "expense_group": "",
                "source_article": "Корневая статья A",
            },
            {
                "code": "ERP-EMPTY-B",
                "name": "Корневая статья B",
                "expense_type": "Прочие доходы",
                "expense_group": "",
                "source_article": "Корневая статья B",
            },
        ]
    )
    store.replace_reference("erp_articles", articles)

    response = upload(client, workbook_bytes(missing_mapping=True))
    catalog = erp_catalog_from(response)
    empty_group_entries = [
        item
        for item in catalog
        if item["expenseType"] == "Прочие доходы" and item["expenseGroup"] == ""
    ]
    assert {item["sourceArticle"] for item in empty_group_entries} == {
        "Корневая статья A",
        "Корневая статья B",
    }
    assert {item["code"] for item in empty_group_entries} == {
        "ERP-EMPTY-A1",
        "ERP-EMPTY-A2",
        "ERP-EMPTY-B",
    }

    script = client.get("/static/run.js").text
    assert 'const EMPTY_LEVEL = "__EMPTY__"' in script
    assert 'return value === "" ? EMPTY_LEVEL' in script
    assert 'if (value === EMPTY_LEVEL) return ""' in script
    assert 'displayLevel(value, "Корневой уровень")' in script
    assert 'displayLevel(value, "Без группы")' in script
    assert 'displayLevel(value, "Без статьи")' in script
    assert "article.expenseGroup === expenseGroup" in script


def test_manual_erp_correction_updates_all_months_and_keeps_other_issue_visible(client):
    response = upload(
        client,
        workbook_bytes(missing_mapping=True, department_error=True),
    )
    run_id = run_id_from(response)

    corrected = client.post(
        f"/runs/{run_id}/correct",
        data={
            "source_row": 3,
            "erp_code": "ERP-001",
            "tax": "",
            "department": "",
            "cfo": "",
            "expense_group": "",
            "source_article": "",
        },
        follow_redirects=True,
    )
    run = client.app.state.workflow.get_run(run_id)
    row_records = [record for record in run.records if record.source_row == 3]
    row_issues = [
        issue.description
        for issue in run.unresolved_issues
        if issue.pointer.row == 3
    ]

    assert len(row_records) == 12
    assert {record.erp_code for record in row_records} == {"ERP-001"}
    assert run.rerun_count == 0
    assert "Не заполнено поле: департамент" in row_issues
    assert "Точное соответствие ERP не найдено" not in row_issues
    assert "Не заполнено поле: департамент" in corrected.text
    assert corrected.text.count('data-testid="attention-editor"') == 1


def test_add_scenario_shows_erp_unconfirmed_marker(client):
    response = client.post(
        "/scenarios",
        data={"name": "ПЛАН_2027", "year": 2027, "comment": "synthetic"},
        follow_redirects=True,
    )
    assert "ПЛАН 2027" in response.text
    assert "Не подтверждён справочником ERP" in response.text
    restarted = TestClient(create_app(client.app.state.workflow.runtime_dir))
    assert "ПЛАН 2027" in restarted.get("/").text


def test_blocked_no_range_state_has_reset_action(client):
    response = upload(client, workbook_bytes(no_range=True))
    assert response.status_code == 200
    assert "Подготовленный диапазон не найден" in response.text
    assert "Сбросить и выбрать другой файл" in response.text
    upload_id = next(iter(client.app.state.workflow.pending))
    reset = client.post(f"/uploads/{upload_id}/reset", follow_redirects=True)
    assert "Выбор файла сброшен" in reset.text


def test_multiple_ranges_are_not_selected_silently(client):
    response = upload(client, workbook_bytes(two_candidates=True))
    assert "Выберите подготовленный диапазон" in response.text
    assert response.text.count('name="candidate_id"') == 2


def test_skipped_month_is_visible_in_preview_with_cell_pointer(client):
    response = upload(client, workbook_bytes(monthly_error=True))
    assert response.status_code == 200
    assert "Пропущено" in response.text
    assert "M3" in response.text
    assert "Ошибка Excel в месячной ячейке" in response.text
    assert response.text.count('data-testid="read-only-attention"') == 1
    assert response.text.count('data-testid="attention-editor"') == 0
    assert "Исправьте месячную ячейку в исходном Excel" in response.text
    assert "Применить к исходной строке и всем месяцам" not in response.text


def test_reporting_unit_conflict_is_visible_and_does_not_block(client):
    response = upload(
        client,
        workbook_bytes(reporting_unit="ПС"),
        reporting_unit="АЮ",
    )
    assert response.status_code == 200
    assert "24" in response.text
    assert "не совпадает с выбранной" in response.text
    assert "A3" in response.text
    assert response.text.count('data-testid="read-only-attention"') == 2
    assert response.text.count('data-testid="attention-editor"') == 0
    assert "Измените выбранную единицу отчёта" in response.text
    assert "Применить к исходной строке и всем месяцам" not in response.text


def test_editable_and_read_only_reasons_share_one_group_without_hiding_either(client):
    response = upload(client, workbook_bytes(missing_mapping=True, negative=True))

    assert response.text.count('data-testid="attention-group"') == 1
    assert response.text.count('data-testid="attention-editor"') == 1
    assert response.text.count('data-testid="read-only-attention"') == 0
    assert "Точное соответствие ERP не найдено" in response.text
    assert "Отрицательная сумма" in response.text
    assert "Проверьте сумму в исходном Excel" in response.text
    assert 'data-testid="read-only-reason"' in response.text
    assert "Применить к исходной строке и всем месяцам" in response.text
