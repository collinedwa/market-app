import json
import pytest
import app
from flask import request


@pytest.fixture
def client():
    return app.app.test_client()


def test_register(client):
    '''Registration'''
    response = client.post("/api/register", data=json.dumps({"username": "test_user",
                                                             "password": "testpass", "name": "Test"}), content_type='application/json')
    assert response.status_code == 200
    false_response = client.post("/api/register", data={"username": "test_user",
                                                        "password": "testpass"}, content_type='application/json')
    assert false_response.status_code == 400


def test_cant_access(client):
    '''Requires user to be logged in'''
    client.get("/")
    response = client.get("/api/user")
    assert response.status_code == 401


def test_login(client):
    '''User log in'''
    response = client.post("/api/login", data=json.dumps({"username": "test_user",
                                                          "password": "testpass"}), content_type='application/json')
    assert response.status_code == 200
    false_response = client.post("/api/login", data=json.dumps({"username": "fake_user",
                                                                "password": "testpass"}), content_type='application/json')
    assert false_response.status_code == 400


def test_user_data(client):
    '''User data'''
    client.post("/api/login", data=json.dumps({"username": "test_user",
                                               "password": "testpass"}), content_type='application/json')
    response = client.get("/api/user")
    res = json.loads(response.data.decode('utf-8'))
    assert "user" in res and "current balance" in res and "holdings value" in res


def test_user_edit(client):
    '''Edit user credentials'''
    client.post("/api/login", data=json.dumps({"username": "test_user",
                                               "password": "testpass"}), content_type='application/json')
    false_response = client.put("/api/user/edit", data=json.dumps({"username": "t",
                                                                   "password": "p"}), content_type='application/json')
    assert false_response.status_code == 400

    response = client.put("/api/user/edit", data=json.dumps({"username": "testuser",
                                                             "password": "passtest"}), content_type='application/json',
                          follow_redirects=True)
    assert response.request.path == '/api/user/logout'


def test_money(client):
    '''Adding and removing money'''
    client.post("/api/login", data=json.dumps({"username": "testuser",
                                               "password": "passtest"}), content_type='application/json')
    response = client.post(
        "/api/user", data=json.dumps({"add money": 10001}), content_type='application/json')
    assert response.status_code == 200

    response = client.post(
        "/api/user", data=json.dumps({"remove money": 1}), content_type='application/json')
    assert response.status_code == 200

    false_response = client.post(
        "/api/user", data=json.dumps({"remove money": 50000}), content_type='application/json')
    assert false_response.status_code == 400


def test_stocks(client):
    '''Stock data; buying and selling stocks'''
    client.post("/api/login", data=json.dumps({"username": "testuser",
                                               "password": "passtest"}), content_type='application/json')
    response = client.post(
        "/api/stocks", data=json.dumps({"ticker": "MSFT"}), content_type='application/json')
    res = json.loads(response.data.decode('utf-8'))
    assert "ticker" in res and "name" in res and "current price" in res

    response = client.post("/api/stocks/buy", data=json.dumps(
        {"ticker": "MSFT", "amount": 1}), content_type='application/json')
    assert response.status_code == 200

    response = client.post("/api/stocks/sell", data=json.dumps(
        {"ticker": "MSFT", "amount": 1}), content_type='application/json')
    assert response.status_code == 200

    false_response = client.post("/api/stocks/sell", data=json.dumps(
        {"ticker": "MSFT", "amount": 1}), content_type='application/json')
    assert false_response.status_code == 400

    false_response = client.post("/api/stocks/buy", data=json.dumps(
        {"ticker": "MSFT", "amount": 1000}), content_type='application/json')
    assert false_response.status_code == 400

    response = client.get("/api/user/transactions")
    res = json.loads(response.data.decode('utf-8'))
    assert len(res) > 1


def test_analysis_invest(client):
    '''Market analysis and investment'''
    client.post("/api/login", data=json.dumps({"username": "testuser",
                                               "password": "passtest"}), content_type='application/json')
    false_response = client.post("/api/user/analysis", data=json.dumps(
        {"budget": 100000, "aggressive": True}), content_type='application/json')
    assert false_response.status_code == 400

    false_response = client.get("/api/user/invest")
    assert false_response.status_code == 400

    response = client.post("/api/user/analysis", data=json.dumps(
        {"market": "sp500", "budget": 10000, "results num": 10, "aggressive": True}), content_type='application/json')
    res = json.loads(response.data.decode('utf-8'))
    assert len(res) == 13
    assert len(res['1m percentile']) == 10

    response = client.get("/api/user/invest")
    res = json.loads(response.data.decode('utf-8'))
    assert len(res) == 3
    assert len(res['Name']) == 10


def test_delete(client):
    '''Delete user account'''
    client.post("/api/login", data=json.dumps({"username": "testuser",
                                               "password": "passtest"}), content_type='application/json')
    response = client.delete("/api/user/edit")
    assert response.status_code == 200