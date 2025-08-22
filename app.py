from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
import itertools
import ast
import operator
import json
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# ---------- App Setup ----------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# ---------- Data ----------
DATA_FILE = "data.json"
_id_counter = itertools.count(1)

tasks = []
diary_entries = []
budget_items = []
routines = []


def save_data():
    """Save all app data to JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "tasks": tasks,
                "diary_entries": diary_entries,
                "budget_items": budget_items,
                "routines": routines,
            },
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def load_data():
    """Load data from JSON file if exists, else start fresh."""
    global _id_counter

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
            tasks[:] = data.get("tasks", [])
            diary_entries[:] = data.get("diary_entries", [])
            budget_items[:] = data.get("budget_items", [])
            routines[:] = data.get("routines", [])

        # Reset ID counter based on max existing ID
        all_ids = [
            item["id"]
            for lst in (tasks, diary_entries, budget_items, routines)
            for item in lst
            if "id" in item
        ]
        start_id = max(all_ids, default=0) + 1
        _id_counter = itertools.count(start_id)
    else:
        save_data()


# Load data at startup
load_data()

# ---------- Users ----------
users = {"demo@example.com": generate_password_hash("demo123")}


# ---------- Auth Helpers ----------
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_email" not in session:
            flash("Please login first 🔐", "warning")
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)

    return wrapped


# ---------- Helpers ----------
def parse_datetime_local(value):
    """Parse datetime from HTML5 input-local string."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except Exception:
        return None


# Safe calculator using AST
_ALLOWED_NODES = {
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Num,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Constant,
}
_ALLOWED_OPS = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.UAdd,
    ast.USub,
)


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numbers allowed.")
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_OPS):
        return _apply_unary(node.op, _eval_node(node.operand))
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_OPS):
        return _apply_bin(node.op, _eval_node(node.left), _eval_node(node.right))
    raise ValueError("Invalid expression.")


def _apply_unary(op, val):
    return +val if isinstance(op, ast.UAdd) else -val


def _apply_bin(op, a, b):
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    fn = ops.get(type(op))
    if not fn:
        raise ValueError("Operator not allowed.")
    return fn(a, b)


def safe_calc(expr: str):
    """Safely evaluate arithmetic expression string."""
    if not expr.strip():
        raise ValueError("Expression is empty.")
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, tuple(_ALLOWED_NODES)):
            raise ValueError("Unsupported syntax.")
    return _eval_node(tree)


def upcoming_tasks_within(minutes=10):
    """Return tasks due within X minutes."""
    now = datetime.now()
    soon = now + timedelta(minutes=minutes)
    return [
        t
        for t in tasks
        if not t["done"]
        and t.get("due_at")
        and now <= datetime.fromisoformat(t["due_at"]) <= soon
    ]


# ---------- Auth Routes ----------
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if not email or not password:
            flash("Please enter email and password.", "warning")
            return redirect(url_for("login_page"))

        pw_hash = users.get(email)
        if pw_hash and check_password_hash(pw_hash, password):
            session["user_email"] = email
            flash(f"Welcome! 🎉 {email}", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password ❌", "danger")
        return redirect(url_for("login_page"))

    return render_template("login.html")


@app.route("/logout")
def logout_page():
    session.pop("user_email", None)
    flash("Logged out 👋", "info")
    return redirect(url_for("login_page"))


# ---------- Dashboard ----------
@app.route("/")
@login_required
def dashboard():
    total_tasks = len(tasks)
    pending_tasks = sum(1 for t in tasks if not t["done"])
    done_tasks = total_tasks - pending_tasks
    income = sum(b["amount"] for b in budget_items if b["type"] == "income")
    expense = sum(b["amount"] for b in budget_items if b["type"] == "expense")
    net = income - expense
    upcoming = upcoming_tasks_within(60)
    return render_template(
        "index.html",
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        done_tasks=done_tasks,
        income=income,
        expense=expense,
        net=net,
        upcoming=upcoming,
    )


# ---------- Tasks ----------
@app.route("/tasks")
@login_required
def tasks_page():
    return render_template("tasks.html", tasks=tasks)


@app.route("/tasks/add", methods=["POST"])
@login_required
def task_add():
    title = request.form.get("title", "").strip()
    priority = request.form.get("priority", "Medium")
    due_raw = request.form.get("due_at")
    if not title:
        flash("Task title is required.", "warning")
        return redirect(url_for("tasks_page"))
    due_at = parse_datetime_local(due_raw)
    tasks.append(
        {
            "id": next(_id_counter),
            "title": title,
            "priority": priority,
            "due_at": due_at.isoformat() if due_at else None,
            "done": False,
        }
    )
    save_data()
    flash("Task added.", "success")
    return redirect(url_for("tasks_page"))


@app.route("/tasks/done/<int:item_id>")
@login_required
def task_done(item_id):
    for t in tasks:
        if t["id"] == item_id:
            t["done"] = True
            break
    save_data()
    flash("Marked done.", "info")
    return redirect(url_for("tasks_page"))


@app.route("/tasks/delete/<int:item_id>")
@login_required
def task_delete(item_id):
    global tasks
    tasks = [t for t in tasks if t["id"] != item_id]
    save_data()
    flash("Task deleted.", "danger")
    return redirect(url_for("tasks_page"))


# ---------- Diary ----------
@app.route("/diary")
@login_required
def diary_page():
    entries = sorted(diary_entries, key=lambda e: e["created_at"], reverse=True)
    return render_template("diary.html", entries=entries)


@app.route("/diary/add", methods=["POST"])
@login_required
def diary_add():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title and not content:
        flash("Write something for your diary entry.", "warning")
        return redirect(url_for("diary_page"))
    diary_entries.append(
        {
            "id": next(_id_counter),
            "title": title or "(Untitled)",
            "content": content,
            "created_at": datetime.now().isoformat(),
        }
    )
    save_data()
    flash("Diary entry saved.", "success")
    return redirect(url_for("diary_page"))


@app.route("/diary/delete/<int:item_id>")
@login_required
def diary_delete(item_id):
    global diary_entries
    diary_entries = [d for d in diary_entries if d["id"] != item_id]
    save_data()
    flash("Diary entry deleted.", "danger")
    return redirect(url_for("diary_page"))


# ---------- Calculator ----------
@app.route("/calculator", methods=["GET", "POST"])
@login_required
def calculator_page():
    result = None
    expr = ""
    if request.method == "POST":
        expr = request.form.get("expression", "").strip()
        if expr:
            try:
                result = safe_calc(expr)
            except Exception as e:
                flash(f"Invalid expression: {e}", "warning")
    return render_template("calculator.html", result=result, expr=expr)


# ---------- Budget ----------
@app.route("/budget")
@login_required
def budget_page():
    income_items = [b for b in budget_items if b["type"] == "income"]
    expense_items = [b for b in budget_items if b["type"] == "expense"]
    income_total = sum(b["amount"] for b in income_items)
    expense_total = sum(b["amount"] for b in expense_items)
    net = income_total - expense_total
    return render_template(
        "budget.html",
        income_items=income_items,
        expense_items=expense_items,
        income_total=income_total,
        expense_total=expense_total,
        net=net,
    )


@app.route("/budget/add", methods=["POST"])
@login_required
def budget_add():
    kind = request.form.get("type")
    label = request.form.get("label", "").strip()
    amount_raw = request.form.get("amount", "0").strip()
    try:
        amount = float(amount_raw)
    except ValueError:
        flash("Amount must be a number.", "warning")
        return redirect(url_for("budget_page"))
    if kind not in ("income", "expense"):
        flash("Select income or expense.", "warning")
        return redirect(url_for("budget_page"))
    if not label:
        flash("Label is required.", "warning")
        return redirect(url_for("budget_page"))
    budget_items.append(
        {
            "id": next(_id_counter),
            "type": kind,
            "label": label,
            "amount": amount,
            "created_at": datetime.now().isoformat(),
        }
    )
    save_data()
    flash("Budget item added.", "success")
    return redirect(url_for("budget_page"))


@app.route("/budget/delete/<int:item_id>")
@login_required
def budget_delete(item_id):
    global budget_items
    budget_items = [b for b in budget_items if b["id"] != item_id]
    save_data()
    flash("Budget item deleted.", "danger")
    return redirect(url_for("budget_page"))


# ---------- Routine ----------
@app.route("/routine")
@login_required
def routine_page():
    return render_template("routine.html", routines=routines)


@app.route("/routine/add", methods=["POST"])
@login_required
def routine_add():
    title = request.form.get("title", "").strip()
    time_of_day = request.form.get("time_of_day", "").strip()
    days = request.form.getlist("days")
    if not title or not time_of_day:
        flash("Routine title and time are required.", "warning")
        return redirect(url_for("routine_page"))
    routines.append(
        {
            "id": next(_id_counter),
            "title": title,
            "time_of_day": time_of_day,
            "days": days,
        }
    )
    save_data()
    flash("Routine added.", "success")
    return redirect(url_for("routine_page"))


@app.route("/routine/delete/<int:item_id>")
@login_required
def routine_delete(item_id):
    global routines
    routines = [r for r in routines if r["id"] != item_id]
    save_data()
    flash("Routine deleted.", "danger")
    return redirect(url_for("routine_page"))


# ---------- Drawing ----------
@app.route("/draw")
@login_required
def draw_page():
    return render_template("draw.html")


# ---------- Notifier API ----------
@app.route("/api/upcoming")
@login_required
def api_upcoming():
    soon = upcoming_tasks_within(10)
    payload = [{"id": t["id"], "title": t["title"], "due_at": t["due_at"]} for t in soon]
    return {"upcoming": payload}


# ---------- Entry ----------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
