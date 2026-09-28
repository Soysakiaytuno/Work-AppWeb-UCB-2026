from flask import Blueprint, flash, redirect, render_template, request, url_for
from .extensions import db
from .models import Todo

bp = Blueprint("todos", __name__)

@bp.route("/")
def index():
    todos = Todo.query.order_by(Todo.completed.asc(), Todo.created_at.desc()).all()
    return render_template("index.html", todos=todos)

@bp.route("/todos", methods=["POST"])
def create():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("todos.index"))
    
    todo = Todo(title=title, description=description)
    db.session.add(todo)
    db.session.commit()
    flash("Todo created.", "success")
    return redirect(url_for("todos.index"))

@bp.route("/todos/<int:todo_id>/edit", methods=["GET", "POST"])
def edit(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        completed = True if request.form.get("completed") else False
        
        if not title:
            flash("Title is required.", "error")
            return redirect(url_for("todos.edit", todo_id=todo.id))
            
        todo.title = title
        todo.description = description
        todo.completed = completed
        db.session.commit()
        flash("Todo updated.", "success")
        return redirect(url_for("todos.index"))
        
    return render_template("edit.html", todo=todo)

@bp.route("/todos/<int:todo_id>/toggle", methods=["POST"])
def toggle(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    todo.completed = not todo.completed
    db.session.commit()
    return redirect(url_for("todos.index"))

@bp.route("/todos/<int:todo_id>/delete", methods=["POST"])
def delete(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    db.session.delete(todo)
    db.session.commit()
    flash("Todo deleted.", "success")
    return redirect(url_for("todos.index"))
