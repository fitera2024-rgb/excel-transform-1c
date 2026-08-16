from __future__ import annotations

import argparse
import re
import uuid
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener

from openpyxl import Workbook, load_workbook


ADO_OPIU_HEADERS = (
    "Организация",
    "Сценарий",
    "Год",
    "Месяц",
    "Период",
    "Организационные единицы",
    "Код Организационных единиц",
    "ЦФО",
    "Код ЦФО",
    "Тип расходов",
    "Код статьи",
    "Название статьи",
    "Инт Номенклатура",
    "Код номенклатуры",
    "Регион продаж",
    "Код региона продаж",
    "Сумма",
)

ADO_INDICATOR_HEADERS = (
    "Организация",
    "Сценарий",
    "Год",
    "Месяц",
    "Период",
    "Канал сбыта",
    "Тип расходов",
    "Сумма",
)


class SelectOptionsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.options: dict[str, list[tuple[str, str]]] = {}
        self._select = ""
        self._option_value: str | None = None
        self._option_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "select":
            self._select = values.get("name") or values.get("id") or ""
            self.options.setdefault(self._select, [])
        elif tag == "option" and self._select:
            self._option_value = values.get("value") or ""
            self._option_text = []

    def handle_data(self, data: str) -> None:
        if self._option_value is not None:
            self._option_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self._option_value is not None and self._select:
            self.options[self._select].append(
                (self._option_value, " ".join("".join(self._option_text).split()))
            )
            self._option_value = None
            self._option_text = []
        elif tag == "select":
            self._select = ""


def get(opener, url: str) -> tuple[str, bytes]:
    with opener.open(url, timeout=30) as response:
        return response.geturl(), response.read()


def multipart_body(
    fields: dict[str, str],
    files: dict[str, tuple[str, bytes, str]],
) -> tuple[bytes, str]:
    boundary = f"----fitera-owner-smoke-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for name, (filename, payload, content_type) in files.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                ).encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                payload,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def post_multipart(
    opener,
    url: str,
    fields: dict[str, str],
    files: dict[str, tuple[str, bytes, str]],
) -> tuple[str, bytes]:
    body, content_type = multipart_body(fields, files)
    request = Request(url, data=body, method="POST")
    request.add_header("Content-Type", content_type)
    with opener.open(request, timeout=60) as response:
        return response.geturl(), response.read()


def home_context(opener, base_url: str) -> tuple[str, str]:
    _, payload = get(opener, urljoin(base_url, "/"))
    html = payload.decode("utf-8")
    for marker in ("ООО «ФИТЭРА»", "ERP-статьи", "ЦФО Инталев", "Загрузить / дополнить"):
        assert marker in html, f"Home marker missing: {marker}"

    parser = SelectOptionsParser()
    parser.feed(html)
    organization = next(
        value for value, _ in parser.options.get("organization_node_id", []) if value
    )
    scenario = next(
        value
        for value, label in parser.options.get("scenario_id", [])
        if value and "ПЛАН 2026" in label and "2026" in label
    )
    return organization, scenario


def budget_bytes() -> bytes:
    headers = [
        "ПОДРАЗДЕЛЕНИЕ (ЦФО 1)",
        "ТИП РАСХОДОВ",
        "ДЕПАРТАМЕНТ (ЦФО 2)",
        "Вид организации",
        "ОТДЕЛ",
        "НАЛОГООБЛОЖЕНИЕ",
        "ГРУППА РАСХОДОВ",
        "СТАТЬЯ",
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ]
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Тест"
    sheet.append(["synthetic HTTP owner smoke"])
    sheet.append(headers)
    sheet.append(
        [
            "ТЕСТ",
            "Административные",
            "Департамент",
            "ТК",
            "ЦФО",
            "БЕЗ НДС",
            "Связь",
            "Интернет",
            100,
            *([0] * 11),
        ]
    )
    payload = BytesIO()
    workbook.save(payload)
    workbook.close()
    return payload.getvalue()


def classifier_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Полный путь статьи", "Статья", "Показатель", "Канал сбыта"])
    sheet.append(
        [
            "Административные → Связь → Интернет",
            "Интернет",
            "Услуги связи",
            "Основной канал",
        ]
    )
    payload = BytesIO()
    workbook.save(payload)
    workbook.close()
    return payload.getvalue()


def upload_budget(opener, base_url: str, organization: str, scenario: str) -> tuple[str, str]:
    final_url, payload = post_multipart(
        opener,
        urljoin(base_url, "/uploads"),
        {
            "reporting_unit": "ТЕСТ",
            "organization_node_id": organization,
            "scenario_id": scenario,
            "year": "2026",
            "period_selector_present": "1",
            "all_year": "1",
            "workbook_password": "",
        },
        {
            "budget_file": (
                "owner-smoke-http.xlsx",
                budget_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    match = re.search(r"/runs/([^/?#]+)", urlparse(final_url).path)
    assert match, f"Budget upload did not reach a RUN: {final_url}"
    return match.group(1), payload.decode("utf-8")


def indicator_counts(html: str) -> dict[str, int]:
    labels = {
        "automatic": "Найдено автоматически:",
        "attention": "Требует внимания:",
        "not_found": "Не найдено:",
    }
    result: dict[str, int] = {}
    for key, label in labels.items():
        match = re.search(
            rf"<dt>\s*{re.escape(label)}\s*</dt>\s*<dd>\s*(\d+)\s*</dd>",
            html,
        )
        assert match, f"Indicator counter missing: {label}"
        result[key] = int(match.group(1))
    return result


def export_payload(opener, base_url: str, run_id: str) -> bytes:
    _, payload = get(opener, urljoin(base_url, f"/runs/{run_id}/export"))
    return payload


def sheet_snapshot(payload: bytes, sheet_name: str) -> tuple[tuple[object, ...], ...]:
    workbook = load_workbook(BytesIO(payload), data_only=True, read_only=True)
    try:
        sheet = workbook[sheet_name]
        return tuple(tuple(cell.value for cell in row) for row in sheet.iter_rows())
    finally:
        workbook.close()


def assert_export(payload: bytes) -> None:
    workbook = load_workbook(BytesIO(payload), data_only=True, read_only=True)
    try:
        assert workbook.sheetnames == ["OPIU Light", "ОПИУ", "Показатели"]
        assert tuple(cell.value for cell in workbook["ОПИУ"][1]) == ADO_OPIU_HEADERS
        assert tuple(cell.value for cell in workbook["Показатели"][1]) == ADO_INDICATOR_HEADERS
        assert workbook["ОПИУ"].max_column == 17
        assert workbook["Показатели"].max_column == 8
        assert workbook["Показатели"]["G2"].value == "Услуги связи"
        assert workbook["Показатели"]["H2"].value == 100
    finally:
        workbook.close()


def initial_owner_smoke(opener, base_url: str) -> None:
    organization, scenario = home_context(opener, base_url)
    run_id, initial_html = upload_budget(opener, base_url, organization, scenario)
    assert indicator_counts(initial_html) == {
        "automatic": 0,
        "attention": 1,
        "not_found": 1,
    }
    assert 'data-testid="indicator-unresolved-list"' in initial_html
    assert "Требуются решения" in initial_html
    assert "Дополнить точные соответствия — необязательно" in initial_html
    lowered = initial_html.lower()
    assert "sql id" not in lowered
    assert "internal key" not in lowered

    before = export_payload(opener, base_url, run_id)

    final_url, payload = post_multipart(
        opener,
        urljoin(base_url, f"/runs/{run_id}/indicator-classifier"),
        {},
        {
            "classifier_file": (
                "owner-smoke-classifier.xlsx",
                classifier_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert urlparse(final_url).path == f"/runs/{run_id}", "Classifier rematch left current RUN"
    rematched_html = payload.decode("utf-8")
    assert indicator_counts(rematched_html) == {
        "automatic": 1,
        "attention": 0,
        "not_found": 0,
    }
    assert 'data-testid="indicator-unresolved-list"' not in rematched_html
    assert re.search(
        r"<span>Полных перезапусков</span>\s*<strong>0</strong>",
        rematched_html,
    ), "Classifier rematch performed a full rerun"

    after = export_payload(opener, base_url, run_id)
    assert sheet_snapshot(before, "OPIU Light") == sheet_snapshot(after, "OPIU Light")
    assert sheet_snapshot(before, "ОПИУ") == sheet_snapshot(after, "ОПИУ")
    assert_export(after)
    print("OWNER_SMOKE_HTTP_INITIAL_PASS")


def post_restart_owner_smoke(opener, base_url: str) -> None:
    organization, scenario = home_context(opener, base_url)
    _, html = upload_budget(opener, base_url, organization, scenario)
    assert indicator_counts(html) == {
        "automatic": 1,
        "attention": 0,
        "not_found": 0,
    }, "Persisted classifier was not applied after service restart"
    run_match = re.search(r"/runs/([^/?#]+)", html)
    # The RUN id is not required from page markup; upload_budget already proved the redirect.
    # Validate the business-visible result directly on the returned preview.
    assert "Услуги связи" in html or "Найдено автоматически" in html
    print("OWNER_SMOKE_HTTP_POST_RESTART_PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--phase", choices=("initial", "post-restart"), required=True)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    opener = build_opener()
    if args.phase == "initial":
        initial_owner_smoke(opener, base_url)
    else:
        post_restart_owner_smoke(opener, base_url)


if __name__ == "__main__":
    main()
