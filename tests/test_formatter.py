"""Tests unitaires pour app.formatter."""
import pytest

from app.formatter import format_metrics


def test_format_metrics_valid_payload():
    metrics = {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "hostname": "test-host",
        "cpu": {"percent": 10.0, "logical_cores": 4},
        "memory": {
            "total_bytes": 1000,
            "available_bytes": 500,
            "used_bytes": 500,
            "percent": 50.0,
        },
        "system": {"load_1m": 0.1, "load_5m": 0.2, "load_15m": 0.3},
    }

    result = format_metrics(metrics, agent_name="test-agent")

    assert result["agent"] == "test-agent"
    assert result["event_type"] == "system_metrics"
    assert result["data"] == metrics


def test_format_metrics_default_agent_name():
    metrics = {
        "timestamp": "t",
        "hostname": "h",
        "cpu": {},
        "memory": {},
        "system": {},
    }
    result = format_metrics(metrics)
    assert result["agent"] == "system-metrics-agent"


def test_format_metrics_missing_keys_raises_value_error():
    with pytest.raises(ValueError):
        format_metrics({"timestamp": "now"})
