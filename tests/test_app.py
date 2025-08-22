import pytest
from app import app

@pytest.fixture()
def client():
    app.testing = True
    with app.test_client() as c:
        yield c


def test_root(client):
    """Test the root endpoint (/)"""
    r = client.get("/")
    assert r.status_code == 200
    data = r.get_json()
    assert "message" in data
    # Adjust according to your root message
    assert data["message"].startswith("Welcome") or "To-Do" in data["message"]


def test_status(client):
    """Test the /status endpoint"""
    r = client.get("/status")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("status") == "ok"
    assert "uptime" in data  # If you added uptime info
    assert "tasks_count" in data  # If you added count of todos


def test_health(client):
    """Test the /healthz endpoint"""
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.data == b"ok"


def test_create_task(client):
    """Test creating a new task"""
    r = client.post("/tasks", json={"title": "Test Task"})
    assert r.status_code == 201
    data = r.get_json()
    assert "id" in data
    assert data["title"] == "Test Task"
    assert data["completed"] is False


def test_get_tasks(client):
    """Test fetching all tasks"""
    # First create one
    client.post("/tasks", json={"title": "Another Task"})
    r = client.get("/tasks")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    assert any(task["title"] == "Another Task" for task in data)


def test_update_task(client):
    """Test updating a task"""
    # Create
    create_res = client.post("/tasks", json={"title": "Update Me"})
    task_id = create_res.get_json()["id"]

    # Update
    r = client.put(f"/tasks/{task_id}", json={"completed": True})
    assert r.status_code == 200
    updated = r.get_json()
    assert updated["completed"] is True


def test_delete_task(client):
    """Test deleting a task"""
    # Create
    create_res = client.post("/tasks", json={"title": "Delete Me"})
    task_id = create_res.get_json()["id"]

    # Delete
    r = client.delete(f"/tasks/{task_id}")
    assert r.status_code == 204

    # Ensure gone
    get_res = client.get("/tasks")
    assert all(task["id"] != task_id for task in get_res.get_json())
