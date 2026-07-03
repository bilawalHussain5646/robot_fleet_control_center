from fastapi.testclient import TestClient
from app.main import app


def test_health():
    with TestClient(app) as client:
        assert client.get('/api/v1/health').status_code == 200


def test_login_and_robots():
    with TestClient(app) as client:
        r = client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'Admin123!'})
        assert r.status_code == 200
        t = r.json()['access_token']
        robots = client.get('/api/v1/robots', headers={'Authorization': f'Bearer {t}'})
        assert robots.status_code == 200
        assert len(robots.json()) >= 10


def test_command_audited():
    with TestClient(app) as client:
        login = client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'Admin123!'})
        t = login.json()['access_token']
        rid = client.get('/api/v1/robots', headers={'Authorization': f'Bearer {t}'}).json()[0]['id']
        r = client.post(f'/api/v1/robots/{rid}/commands', json={'command': 'stop', 'parameters': {}}, headers={'Authorization': f'Bearer {t}'})
        assert r.status_code == 200