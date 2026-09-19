from datetime import UTC, datetime

from nse_lake.site_data import build_demo_payload


def test_demo_payload_is_complete_and_explicitly_labelled() -> None:
    payload = build_demo_payload(datetime(2026, 9, 19, tzinfo=UTC))

    assert payload["meta"]["is_demo"] is True
    assert payload["meta"]["generated_at"] == "2026-09-19T00:00:00Z"
    assert payload["kpis"]["symbols_audited"] == 50
    assert payload["kpis"]["flags"] == len(payload["flags"])
    assert len(payload["survivorship"]) > 250
    assert {row["series"] for row in payload["survivorship"]} == {
        "Today's constituents",
        "Point-in-time",
    }
