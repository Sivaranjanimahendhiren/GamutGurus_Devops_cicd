import os
import sys
import re
import pytest

# Ensure project root is in sys.path (works in CI and locally)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app  # noqa: E402


@pytest.fixture()
def client():
    """Create a test client for the Flask app."""
    app.testing = True
    with app.test_client() as c:
        yield c


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/")
    assert response.status_code == 302  # Redirect
    assert "/login" in response.headers["Location"]


def test_login_logout_flow(client):
    response = client.post(
        "/login",
        data={"email": "demo@example.com", "password": "demo123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome" in response.data

    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Logged out" in response.data


def test_add_task(client):
    client.post(
        "/login",
        data={"email": "demo@example.com", "password": "demo123"},
        follow_redirects=True,
    )

    response = client.post(
        "/tasks/add",
        data={"title": "Test Task", "priority": "High"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Task added" in response.data
    assert b"Test Task" in response.data


def test_mark_task_done(client):
    client.post(
        "/login",
        data={"email": "demo@example.com", "password": "demo123"},
        follow_redirects=True,
    )
    client.post(
        "/tasks/add",
        data={"title": "Complete Me", "priority": "Medium"},
        follow_redirects=True,
    )

    response = client.get("/tasks")
    html = response.data.decode()
    match = re.search(r"/tasks/done/(\d+)", html)
    assert match
    task_id = int(match.group(1))

    response = client.get(f"/tasks/done/{task_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Marked done" in response.data


def test_delete_task(client):
    client.post(
        "/login",
        data={"email": "demo@example.com", "password": "demo123"},
        follow_redirects=True,
    )
    client.post(
        "/tasks/add",
        data={"title": "Delete Me", "priority": "Low"},
        follow_redirects=True,
    )

    response = client.get("/tasks")
    html = response.data.decode()
    match = re.search(r"/tasks/delete/(\d+)", html)
    assert match
    task_id = int(match.group(1))

    response = client.get(f"/tasks/delete/{task_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Task deleted" in response.data
