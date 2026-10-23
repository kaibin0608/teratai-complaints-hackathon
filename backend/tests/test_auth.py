"""Login, tokens and the AUTH_REQUIRED switch (offline)."""
import datetime as dt

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.auth.tokens import make_token
from backend.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "api.db")) as c:
        yield c


def login(client, username, password="teratai123"):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_officer_logs_in(client):
    r = login(client, "officer1")
    assert r.status_code == 200
    assert r.json()["user"] == {"username": "officer1", "full_name": "Aina Rahman", "role": "officer",
                                "approval_limit_myr": "2000.00"}
    me = client.get("/api/auth/me", headers=bearer(r.json()["token"]))
    assert me.status_code == 200 and me.json()["username"] == "officer1"


def test_manager_has_no_limit(client):
    assert login(client, "manager1").json()["user"]["approval_limit_myr"] is None


@pytest.mark.parametrize("username, password", [("officer1", "wrong"), ("nobody", "teratai123"), ("", "")])
def test_wrong_credentials_give_one_message(client, username, password):
    r = login(client, username, password)
    assert r.status_code == 401 and r.json()["detail"] == "wrong username or password"


@pytest.mark.parametrize("headers", [{}, bearer("not-a-token"), {"Authorization": "Basic abc"},
                                     bearer(make_token("officer1", "officer",
                                                       now=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=13))),
                                     bearer(make_token("ghost", "manager"))])
def test_me_needs_a_valid_token(client, headers):
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_token_signed_with_another_key_is_refused(client, monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "someone-else")
    forged = make_token("manager1", "manager")
    monkeypatch.undo()
    assert client.get("/api/auth/me", headers=bearer(forged)).status_code == 401


def test_users_list_is_manager_only(client):
    officer = login(client, "officer1").json()["token"]
    manager = login(client, "manager1").json()["token"]
    assert client.get("/api/users", headers=bearer(officer)).status_code == 403
    users = client.get("/api/users", headers=bearer(manager)).json()
    assert [u["username"] for u in users] == ["fraud1", "manager1", "officer1", "officer2"]
    assert all("password_hash" not in u for u in users)


def test_open_mode_serves_reads_without_a_token(client):
    assert client.get("/api/cases").status_code == 200
    assert client.get("/api/users").status_code == 200  # no token = the manager's view


def test_locked_mode_needs_a_token_but_contract_routes_stay_open(client, monkeypatch):
    monkeypatch.setattr(config, "AUTH_REQUIRED", True)
    for path in ("/api/cases", "/api/metrics", "/api/audit", "/api/users"):
        assert client.get(path).status_code == 401, path
    token = login(client, "manager1").json()["token"]
    assert client.get("/api/metrics", headers=bearer(token)).status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/cases/NO-SUCH-CASE").status_code == 404  # served, not 401


def test_a_bad_token_is_refused_even_in_open_mode(client):
    assert client.get("/api/cases", headers=bearer("garbage")).status_code == 401


def test_login_checks_run_on_the_event_loop():
    """Sync dependencies run in FastAPI's thread pool and share the store's one SQLite connection across threads;
    requests sent together then collided (InterfaceError, false 401). They must stay async."""
    import inspect
    from backend.auth import dependencies
    assert inspect.iscoroutinefunction(dependencies.viewer) and inspect.iscoroutinefunction(dependencies.actor)


def test_many_signed_in_requests_at_once(client):
    """The UI fires several requests together; none may fail with a false 401."""
    from concurrent.futures import ThreadPoolExecutor
    headers = bearer(login(client, "manager1").json()["token"])
    paths = ["/api/cases", "/api/metrics", "/api/audit", "/api/users", "/api/auth/me"] * 8
    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(lambda path: client.get(path, headers=headers).status_code, paths))
    assert codes == [200] * len(paths)
