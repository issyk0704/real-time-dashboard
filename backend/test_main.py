from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_stock_cache():
    main.stock_cache.clear()


def mock_response(json_body):
    response = MagicMock()
    response.json.return_value = json_body
    return response


def test_root_serves_dashboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Market dashboard" in response.text


def test_frontend_script_is_served():
    response = client.get("/app.js")
    assert response.status_code == 200


@patch("main.requests.get")
def test_stock_price_and_change_are_extracted(mock_get):
    mock_get.return_value = mock_response(
        {"Global Quote": {"05. price": "189.5000", "10. change percent": "-0.2397%"}}
    )
    response = client.get("/stocks/aapl")
    assert response.json() == {"symbol": "AAPL", "price": "189.5000", "change_percent": -0.2397}


@patch("main.requests.get")
def test_stock_quote_is_cached(mock_get):
    mock_get.return_value = mock_response({"Global Quote": {"05. price": "189.5000"}})
    client.get("/stocks/AAPL")
    client.get("/stocks/aapl")
    assert mock_get.call_count == 1


@patch("main.requests.get")
def test_stock_failures_are_not_cached(mock_get):
    mock_get.return_value = mock_response({"Global Quote": {}})
    client.get("/stocks/AAPL")
    client.get("/stocks/AAPL")
    assert mock_get.call_count == 2


@patch("main.requests.get")
def test_stock_empty_global_quote_is_not_found(mock_get):
    # Alpha Vantage returns an empty quote for unknown symbols
    mock_get.return_value = mock_response({"Global Quote": {}})
    response = client.get("/stocks/NOTREAL")
    assert response.json() == {"error": "Stock data not found"}


@patch("main.requests.get")
def test_stock_rate_limit_is_reported(mock_get):
    mock_get.return_value = mock_response({"Information": "API rate limit reached"})
    response = client.get("/stocks/AAPL")
    assert response.json() == {"error": "Stock API rate limit reached"}


@patch("main.requests.get")
def test_stock_network_failure_returns_error(mock_get):
    mock_get.side_effect = requests.Timeout()
    response = client.get("/stocks/AAPL")
    assert response.json() == {"error": "Failed to fetch stock data"}


@patch("main.requests.post")
def test_crypto_price_and_change_are_extracted(mock_post):
    mock_post.return_value = mock_response({"name": "Bitcoin", "rate": 64000.12, "delta": {"day": 1.0125}})
    response = client.get("/crypto/btc")
    body = response.json()
    assert body["symbol"] == "BTC"
    assert body["price"] == 64000.12
    assert body["change_percent"] == pytest.approx(1.25)
    assert mock_post.call_args.kwargs["json"]["code"] == "BTC"


@patch("main.requests.post")
def test_crypto_missing_delta_gives_no_change(mock_post):
    mock_post.return_value = mock_response({"rate": 64000.12})
    response = client.get("/crypto/BTC")
    assert response.json()["change_percent"] is None


@patch("main.requests.post")
def test_crypto_missing_rate_is_not_found(mock_post):
    mock_post.return_value = mock_response({"error": {"code": 404, "description": "Coin not found"}})
    response = client.get("/crypto/NOTREAL")
    assert response.json() == {"error": "Crypto data not found"}


@patch("main.requests.post")
def test_crypto_network_failure_returns_error(mock_post):
    mock_post.side_effect = requests.ConnectionError()
    response = client.get("/crypto/BTC")
    assert response.json() == {"error": "Failed to fetch crypto data"}
