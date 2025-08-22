import re
import pytest
from app import app


@pytest.fixture()
def client():
    """Create a test client for the Flask app."""
    app.testing = True
    with app.test_client() as c:
        yield c


def test_login_page(client):
    """Test the login page loads correctly."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_dashboard_requires_login(client):
    """Accessing dashboard without login redirects to login."""
    response = client.get("/")
    assert response.status_code == 302  # Redirect
    assert "/login" in response.headers["Location"]


def test_login_logout_flow(client):
    """Test logging in and logging out."""
    # Login
    response = client.post(
        "/login",
        data={"email": "demo@example.com", "password": "demo123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome" in response.data

    # Logout
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Logged out" in response.data


def test_add_task(client):
    """Test adding a task."""
    # Login first
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
    """Test marking a task as done."""
    # Login first
    client.post(
        "/login",
        data={"email": "demo@example.com", "password": "demo123"},
        follow_redirects=True,
    )

    # Add a task
    client.post(
        "/tasks/add",
        data={"title": "Complete Me", "priority": "Medium"},
        follow_redirects=True,
    )

    # Find task ID from tasks page
    response = client.get("/tasks")
    html = response.data.decode()
    match = re.search(r"/tasks/done/(\d+)", html)
    assert match
    task_id = int(match.group(1))

    # Mark done
    response = client.get(f"/tasks/done/{task_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Marked done" in response.data


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
    response = client.get("/tasks")
    html = response.data.decode()
    match = re.search(r"/tasks/delete/(\d+)", html)
    assert match
    task_id = int(match.group(1))

    # Delete task
    response = client.get(f"/tasks/delete/{task_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Task deleted" in response.data
