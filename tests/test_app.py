import pytest
from app import app


@pytest.fixture()
def client():
    app.testing = True
    with app.test_client() as c:
        yield c


def test_login_page(client):
    """Test the login page loads correctly."""
    r = client.get("/login")
    assert r.status_code == 200
    assert b"Login" in r.data  # Check HTML contains 'Login'


def test_dashboard_requires_login(client):
    """Accessing dashboard without login redirects to login."""
    r = client.get("/")
    assert r.status_code == 302  # redirect
    assert "/login" in r.headers["Location"]


def test_login_logout_flow(client):
    """Test logging in and logging out."""
    # Login with demo user
    r = client.post(
        "/login",
        data={"email": "demo@example.com", "password": "demo123"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"Welcome" in r.data

    # Logout
    r = client.get("/logout", follow_redirects=True)
    assert r.status_code == 200
    assert b"Logged out" in r.data


def test_add_task(client):
    """Test adding a task."""
    # Login first
    client.post(
        "/login",
        data={"email": "demo@example.com", "password": "demo123"},
        follow_redirects=True,
    )

    r = client.post(
        "/tasks/add",
        data={"title": "Test Task", "priority": "High"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"Task added" in r.data
    assert b"Test Task" in r.data


def test_mark_task_done(client):
    """Test marking a task as done."""
    # Login first
    client.post(
        "/login",
        data={"email": "demo@example.com", "password": "demo123"},
        follow_redirects=True,
    )

    # Add a task
    r = client.post(
        "/tasks/add",
        data={"title": "Complete Me", "priority": "Medium"},
        follow_redirects=True,
    )
    assert r.status_code == 200

    # Find task ID from the tasks page
    r = client.get("/tasks")
    html = r.data.decode()
    import re

    match = re.search(r"/tasks/done/(\d+)", html)
    assert match
    task_id = match.group(1)

    # Mark done
    r = client.get(f"/tasks/done/{task_id}", follow_redirects=True)
    assert r.status_code == 200
    assert b"Marked done" in r.data


def test_delete_task(client):
    """Test deleting a task."""
    # Login first
    client.post(
        "/login",
        data={"email": "demo@example.com", "password": "demo123"},
        follow_redirects=True,
    )

    # Add a task
    client.post(
        "/tasks/add",
        data={"title": "Delete Me", "priority": "Low"},
        follow_redirects=True,
    )

    # Get task ID
    r = client.get("/tasks")
    html = r.data.decode()
    import re

    match = re.search(r"/tasks/delete/(\d+)", html)
    assert match
    task_id = match.group(1)

    # Delete task
    r = client.get(f"/tasks/delete/{task_id}", follow_redirects=True)
    assert r.status_code == 200
    assert b"Task deleted" in r.data
