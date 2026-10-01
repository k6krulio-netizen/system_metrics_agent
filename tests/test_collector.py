"""Tests unitaires pour app.collector.

psutil et subprocess sont mockés afin que les tests soient rapides,
déterministes et exécutables dans n'importe quel environnement CI
(sans dépendre de la charge réelle de la machine).
"""
from unittest.mock import MagicMock, patch

import pytest

from app.collector import (
    MetricsCollectionError,
    collect_system_metrics,
    get_load_average,
)


def test_get_load_average_parses_uptime_output():
    fake_result = MagicMock(
        stdout="10:00:00 up 1 day,  2 users,  load average: 0.10, 0.20, 0.30"
    )
    with patch("app.collector.platform.system", return_value="Linux"), patch(
        "app.collector.subprocess.run", return_value=fake_result
    ):
        result = get_load_average()

    assert result == {"load_1m": 0.10, "load_5m": 0.20, "load_15m": 0.30}


def test_get_load_average_on_windows_returns_none_values():
    with patch("app.collector.platform.system", return_value="Windows"):
        result = get_load_average()

    assert result == {"load_1m": None, "load_5m": None, "load_15m": None}


def test_get_load_average_raises_when_marker_missing():
    fake_result = MagicMock(stdout="sortie inattendue sans marqueur")
    with patch("app.collector.platform.system", return_value="Linux"), patch(
        "app.collector.subprocess.run", return_value=fake_result
    ):
        with pytest.raises(MetricsCollectionError):
            get_load_average()


def test_collect_system_metrics_success():
    fake_memory = MagicMock(total=1000, available=500, used=500, percent=50.0)

    with patch("app.collector.psutil.virtual_memory", return_value=fake_memory), patch(
        "app.collector.psutil.cpu_percent", return_value=12.5
    ), patch("app.collector.psutil.cpu_count", return_value=4), patch(
        "app.collector.get_load_average",
        return_value={"load_1m": 0.1, "load_5m": 0.2, "load_15m": 0.3},
    ):
        metrics = collect_system_metrics()

    assert metrics["cpu"] == {"percent": 12.5, "logical_cores": 4}
    assert metrics["memory"]["percent"] == 50.0
    assert metrics["system"]["load_1m"] == 0.1
    assert "hostname" in metrics
    assert "timestamp" in metrics


def test_collect_system_metrics_wraps_unexpected_errors():
    with patch(
        "app.collector.psutil.virtual_memory", side_effect=RuntimeError("boom")
    ):
        with pytest.raises(MetricsCollectionError):
            collect_system_metrics()
