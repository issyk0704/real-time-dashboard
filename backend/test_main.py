from unittest.mock import MagicMock, patch

import requests
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def mock_response(json_body):
    response = MagicMock()
    response.json.return_value = json_body
    return response


def test_root_returns_welcome_message():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Real-Time Dashboard API"}


@patch("main.requests.get")
def test_stock_price_is_extracted_from_global_quote(mock_get):
    mock_get.return_value = mock_response({"Global Quote": {"05. price": "189.5000"}})
    response = client.get("/stocks/AAPL")
    assert response.json() == {"symbol": "AAPL", "price": "189.5000"}


@patch("main.requests.get")
def test_stock_empty_global_quote_is_not_found(mock_get):
    # Alpha Vantage returns an empty quote for unknown symbols
    mock_get.return_value = mock_response({"Global Quote": {}})
    response = client.get("/stocks/NOTREAL")
    assert response.json() == {"error": "Stock data not found"}


@patch("main.requests.get")
def test_stock_rate_limit_message_is_not_found(mock_get):
    mock_get.return_value = mock_response({"Information": "API rate limit reached"})
    response = client.get("/stocks/AAPL")
    assert response.json() == {"error": "Stock data not found"}


@patch("main.requests.get")
def test_stock_network_failure_returns_error(mock_get):
    mock_get.side_effect = requests.Timeout()
    response = client.get("/stocks/AAPL")
    assert response.json() == {"error": "Failed to fetch stock data"}


@patch("main.requests.post")
def test_crypto_price_is_extracted_and_symbol_uppercased(mock_post):
    mock_post.return_value = mock_response({"name": "Bitcoin", "rate": 64000.12})
    response = client.get("/crypto/btc")
    assert response.json() == {"symbol": "BTC", "price": 64000.12}
    assert mock_post.call_args.kwargs["json"]["code"] == "BTC"


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
