import asyncio
import json
import re
import threading

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from excel_transform_1c.adapters import protected_ooxml as protected_adapter
from excel_transform_1c.application import service as service_module
from excel_transform_1c.ui.app import create_app
from tests.helpers.workbooks import (
    indicator_classifier_bytes,
    large_workbook_bytes,
    protected_workbook_bytes,
    reference_bytes,
    workbook_bytes,
)


pytestmark = pytest.mark.ui


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "runtime")
    test_client = TestClient(app)
    for kind in ("erp_articles", "organizations", "scenarios", "intalev_cfos"):
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
    test_client.app.state.workflow.store.save_cfo_mappings(
        {"code:INT-CFO-1": "cfo", "code:INT-CFO-2": "other"}
    )
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


def test_budget_form_shows_processing_state_and_blocks_duplicate_submit(client):
    response = client.get("/")
    assert "Файл загружается и анализируется; не закрывайте страницу" in response.text
    assert 'type="password" name="workbook_password"' in response.text
    assert "Пароль используется только для текущей локальной обработки" in response.text
    assert 'data-processing-form' in response.text
    assert 'processForm.dataset.submitting === "true"' in response.text
    assert "event.preventDefault()" in response.text
    assert "processButton.disabled = true" in response.text


def test_preview_shows_compact_indicator_counts_without_rules_workflow(client):
    response = upload(client, workbook_bytes())
    run_id = run_id_from(response)

    assert 'data-testid="indicator-classifier-summary"' in response.text
    assert "Найдено автоматически:" in response.text
    assert "Требует внимания:" in response.text
    assert "Не найдено:" in response.text
    assert "Классификатор:" in response.text
    assert "не загружен" in response.text
    assert 'data-testid="indicator-classifier-form"' in response.text
    assert "Rules" not in response.text

    response = client.post(
        f"/runs/{run_id}/indicator-classifier",
        files={
            "classifier_file": (
                "classifier.xlsx",
                indicator_classifier_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Автоматический поиск повторён в текущем RUN" in response.text
    assert re.search(r"Найдено автоматически:</dt><dd>2</dd>", response.text)
    assert re.search(r"Требует внимания:</dt><dd>0</dd>", response.text)
    assert re.search(r"Не найдено:</dt><dd>0</dd>", response.text)
    assert re.search(r"Классификатор:</dt><dd>загружен</dd>", response.text)


def test_legacy_delegation_is_cleared_and_all_nodes_remain_available(tmp_path):
    runtime = tmp_path / "runtime"
    first = TestClient(create_app(runtime))
    for kind in ("erp_articles", "organizations", "scenarios", "intalev_cfos"):
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
    assert "Файл загружается и анализируется; не закрывайте страницу" in response.text
    assert 'data-candidate-processing-form' in response.text
    assert 'button.disabled = true' in response.text


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


def test_wrong_protected_password_is_clear_and_health_remains_available(client):
    protected = protected_workbook_bytes(workbook_bytes(), "synthetic-correct-password")
    response = upload(
        client,
        protected,
        workbook_password="synthetic-wrong-password",
    )
    assert response.status_code == 200
    assert "Пароль не подошёл" in response.text
    assert "выберите файл повторно" in response.text
    assert client.get("/health").json() == {"status": "ok"}


def test_health_responds_while_budget_analysis_runs_in_worker(client, monkeypatch):
    service = client.app.state.workflow
    original_detect_path = service_module.detect_path
    started = threading.Event()
    release = threading.Event()

    def observed_detection(path):
        started.set()
        if not release.wait(timeout=5):
            raise RuntimeError("synthetic analysis gate timed out")
        return original_detect_path(path)

    monkeypatch.setattr(service_module, "detect_path", observed_detection)
    scenario_id = service.store.list_scenarios()[0].scenario_id
    payload = large_workbook_bytes()

    async def exercise():
        transport = ASGITransport(app=client.app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            follow_redirects=True,
        ) as async_client:
            request = asyncio.create_task(
                async_client.post(
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
                )
            )
            assert await asyncio.to_thread(started.wait, 2)
            health = await async_client.get("/health")
            assert health.status_code == 200
            assert health.json() == {"status": "ok"}
            release.set()
            response = await request
            assert response.status_code == 200
            assert "/runs/" in str(response.url)

    asyncio.run(exercise())


def test_unknown_decrypt_error_cannot_reveal_password_in_http_or_runtime(
    client,
    monkeypatch,
    caplog,
):
    synthetic_password = "synthetic-unknown-error-password"
    protected = protected_workbook_bytes(workbook_bytes(), synthetic_password)

    def fail_with_secret(_source):
        raise RuntimeError(f"dependency failed with {synthetic_password}")

    monkeypatch.setattr(protected_adapter.msoffcrypto, "OfficeFile", fail_with_secret)
    response = upload(
        client,
        protected,
        workbook_password=synthetic_password,
    )

    service = client.app.state.workflow
    assert response.status_code == 200
    assert "Не удалось расшифровать защищённый файл" in response.text
    assert synthetic_password not in response.text
    assert synthetic_password not in repr(dict(response.headers))
    assert synthetic_password not in repr(service.pending)
    assert synthetic_password not in repr(service.runs)
    assert synthetic_password not in caplog.text

    password_bytes = synthetic_password.encode()
    for path in service.runtime_dir.rglob("*"):
        assert synthetic_password not in path.name
        if path.is_file():
            assert password_bytes not in path.read_bytes()
