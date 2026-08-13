import json
import re
import sqlite3

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


def upload(client, payload: bytes):
    scenario_id = client.app.state.workflow.store.list_scenarios()[0].scenario_id
    return client.post(
        "/uploads",
        data={
            "reporting_unit": "ПС",
            "organization_node_id": "ps",
            "scenario_id": scenario_id,
            "year": "2026",
            "period_selector_present": "1",
            "all_year": "1",
        },
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


def filled_selection(
    *,
    source_row: int = 3,
    expense_type: str = "Административные",
    expense_group: str = "Связь",
    source_article: str = "Интернет",
    erp_code: str = "ERP-001",
) -> dict[str, object]:
    return {
        "source_row": source_row,
        "expense_type": expense_type,
        "expense_group": expense_group,
        "source_article": source_article,
        "erp_code": erp_code,
    }


def persistence_counts(client) -> tuple[int, int]:
    store = client.app.state.workflow.store
    with sqlite3.connect(store.database) as connection:
        overrides = connection.execute("SELECT COUNT(*) FROM overrides").fetchone()[0]
        mappings = connection.execute("SELECT COUNT(*) FROM manual_mappings").fetchone()[0]
    return overrides, mappings


def test_bulk_control_counts_source_rows_not_months_and_keeps_individual_editor(client):
    response = upload(client, workbook_bytes(department_error=True))

    assert response.status_code == 200
    assert 'data-testid="bulk-confirm-form"' in response.text
    assert "Подтверждаю все заполненные ERP-сопоставления" in response.text
    assert "Будет подтверждено: 1 строк" in response.text
    assert "Применить все заполненные" in response.text
    assert response.text.count('data-testid="attention-editor"') == 1
    assert "Подтверждаю выбранный ERP-код и полный путь" in response.text

    script = client.get("/static/run.js").text
    assert "currentBulkSelections" in script
    assert "JSON.stringify(selections)" in script
    assert "bulkConfirmation.checked" in script
    assert "selection.source_row" in script


def test_bulk_apply_updates_all_months_preserves_other_issue_and_is_idempotent(client):
    response = upload(
        client,
        workbook_bytes(missing_mapping=True, department_error=True),
    )
    run_id = run_id_from(response)
    selection_payload = json.dumps([filled_selection()], ensure_ascii=False)

    first = client.post(
        f"/runs/{run_id}/confirm-filled-erp",
        data={"confirmed": "1", "selections": selection_payload},
        follow_redirects=True,
    )
    run = client.app.state.workflow.get_run(run_id)
    row_records = [record for record in run.records if record.source_row == 3]
    unresolved = [
        issue.description
        for issue in run.unresolved_issues
        if issue.pointer.row == 3
    ]

    assert first.status_code == 200
    assert "Подтверждено ERP-сопоставлений: 1" in first.text
    assert len(row_records) == 12
    assert {record.erp_code for record in row_records} == {"ERP-001"}
    assert {record.department for record in row_records} == {""}
    assert run.rerun_count == 0
    assert "Не заполнено поле: департамент" in unresolved
    assert "Точное соответствие ERP не найдено" not in unresolved
    assert persistence_counts(client) == (1, 1)

    second = client.post(
        f"/runs/{run_id}/confirm-filled-erp",
        data={"confirmed": "1", "selections": selection_payload},
        follow_redirects=True,
    )

    assert second.status_code == 200
    assert "Подтверждено ERP-сопоставлений: 1" in second.text
    assert persistence_counts(client) == (1, 1)
    assert run.rerun_count == 0


def test_bulk_apply_rejects_catalog_mismatch_without_partial_changes(client):
    response = upload(client, workbook_bytes(missing_mapping=True))
    run_id = run_id_from(response)
    payload = json.dumps(
        [filled_selection(expense_group="Несуществующая группа")],
        ensure_ascii=False,
    )

    rejected = client.post(
        f"/runs/{run_id}/confirm-filled-erp",
        data={"confirmed": "1", "selections": payload},
        follow_redirects=True,
    )
    row_records = [
        record
        for record in client.app.state.workflow.get_run(run_id).records
        if record.source_row == 3
    ]

    assert rejected.status_code == 200
    assert "больше не соответствует загруженному справочнику" in rejected.text
    assert {record.erp_code for record in row_records} == {""}
    assert persistence_counts(client) == (0, 0)


def test_bulk_control_is_disabled_for_read_only_only_attention(client):
    response = upload(client, workbook_bytes(monthly_error=True))

    assert response.status_code == 200
    assert 'data-testid="bulk-confirm-form"' in response.text
    assert "Будет подтверждено: 0 строк" in response.text
    assert "Сейчас нет полностью заполненных ERP-сопоставлений" in response.text
    assert response.text.count('data-testid="attention-editor"') == 0
    assert response.text.count('data-testid="read-only-attention"') == 1


def test_bulk_apply_accepts_explicit_empty_hierarchy_level(client):
    store = client.app.state.workflow.store
    articles = store.load_reference("erp_articles")
    articles.append(
        {
            "code": "ERP-ROOT",
            "name": "Корневая статья ERP",
            "expense_type": "Прочие доходы",
            "expense_group": "",
            "source_article": "Корневая статья",
        }
    )
    store.replace_reference("erp_articles", articles)

    response = upload(client, workbook_bytes(missing_mapping=True))
    run_id = run_id_from(response)
    payload = json.dumps(
        [
            filled_selection(
                expense_type="Прочие доходы",
                expense_group="",
                source_article="Корневая статья",
                erp_code="ERP-ROOT",
            )
        ],
        ensure_ascii=False,
    )

    confirmed = client.post(
        f"/runs/{run_id}/confirm-filled-erp",
        data={"confirmed": "1", "selections": payload},
        follow_redirects=True,
    )
    row_records = [
        record
        for record in client.app.state.workflow.get_run(run_id).records
        if record.source_row == 3
    ]

    assert confirmed.status_code == 200
    assert "Подтверждено ERP-сопоставлений: 1" in confirmed.text
    assert {record.erp_code for record in row_records} == {"ERP-ROOT"}
    assert client.app.state.workflow.store.load_manual_mappings()[
        row_records[0].mapping_key
    ] == "ERP-ROOT"
