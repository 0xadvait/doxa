from __future__ import annotations

from doxa.config import load_config
from doxa.eval import faithfulness_report


def test_demo_faithfulness_report_is_clean() -> None:
    report = faithfulness_report(load_config(None))
    assert report["beliefs"] == 8
    assert report["quotes"] == 8
    assert report["checked_quotes"] == 8
    assert report["quote_verbatim_percent"] == 100.0
    assert report["ok"] is True

