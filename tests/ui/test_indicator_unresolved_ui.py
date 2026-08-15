from pathlib import Path


def test_indicator_attention_blocks_completed_stage_and_shows_business_list():
    template = Path("src/excel_transform_1c/ui/templates/run.html").read_text(encoding="utf-8")
    assert "unresolved or indicator_counts.attention > 0" in template
    assert 'data-testid="indicator-unresolved-list"' in template
    assert "Загрузить / дополнить классификатор" in template
    assert "Исходный ЦФО → ЦФО Инталев → узел 1С" in template
    assert "internal key" not in template.lower()
    assert "sql id" not in template.lower()
