"""Tests unitaires pour app.sender.

Le module `requests` est mocké : aucun appel réseau réel n'est effectué,
ce qui rend le test rapide et exécutable dans le pipeline CI sans accès
à un service externe.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.sender import MetricsDeliveryError, send_metrics


def test_send_metrics_success():
    fake_response = MagicMock(status_code=201)
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {"status": "received"}

    with patch("app.sender.requests.post", return_value=fake_response) as mock_post:
        result = send_metrics("http://api/metrics", {"agent": "x"}, timeout=5)

    mock_post.assert_called_once_with(
        "http://api/metrics", json={"agent": "x"}, timeout=5
    )
    assert result == {"status_code": 201, "response": {"status": "received"}}


def test_send_metrics_falls_back_to_text_body_when_not_json():
    fake_response = MagicMock(status_code=200)
    fake_response.raise_for_status.return_value = None
    fake_response.json.side_effect = ValueError("not json")
    fake_response.text = "OK"

    with patch("app.sender.requests.post", return_value=fake_response):
        result = send_metrics("http://api/metrics", {"agent": "x"})

    assert result["response"] == "OK"


def test_send_metrics_raises_metrics_delivery_error_on_request_exception():
    with patch(
        "app.sender.requests.post",
        side_effect=requests.ConnectionError("connection refused"),
    ):
        with pytest.raises(MetricsDeliveryError):
            send_metrics("http://api/metrics", {"agent": "x"})


def test_send_metrics_raises_on_http_error_status():
    fake_response = MagicMock(status_code=500)
    fake_response.raise_for_status.side_effect = requests.HTTPError("server error")

    with patch("app.sender.requests.post", return_value=fake_response):
        with pytest.raises(MetricsDeliveryError):
            send_metrics("http://api/metrics", {"agent": "x"})
