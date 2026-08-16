from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.ui


def test_checkbox_enables_confirm_button() -> None:
    node = shutil.which("node")
    assert node, "Node.js is required for the run.js behavior check"
    root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [
            node,
            str(Path(__file__).with_name("run_js_checkbox_harness.cjs")),
            str(root / "src/excel_transform_1c/ui/static/run.js"),
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"erp": True, "tax": True, "cfo": True}
