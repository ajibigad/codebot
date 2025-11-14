"""Web UI routes for task management."""

import json
import uuid
from datetime import datetime

import requests
from flask import Blueprint, Response, render_template, jsonify, request, current_app, stream_with_context

from codebot.core.models import Task, TaskPrompt
from codebot.core.task_store import global_task_store
from codebot.server.auth import require_basic_auth, require_auth
from codebot.server.log_capture import get_log_storage


def create_web_ui_blueprint() -> Blueprint:
    """
    Create web UI blueprint with task management routes.
    
    Returns:
        Flask Blueprint
    """
    web_ui = Blueprint("web_ui", __name__)
    
    @web_ui.route("/", methods=["GET"])
    @require_basic_auth
    def index():
        return render_template("tasks.html")
    
    @web_ui.route("/api/web/tasks", methods=["GET"])
    @require_basic_auth
    def list_tasks():
        status_filter = request.args.get("status")
        source_filter = request.args.get("source")
        limit = request.args.get("limit", 50, type=int)
        
        if limit < 1 or limit > 1000:
            return jsonify({
                "error": "Bad Request",
                "message": "limit must be between 1 and 1000"
            }), 400
        
        tasks = global_task_store.list_tasks(
            status_filter=status_filter,
            source_filter=source_filter,
            limit=limit
        )
        
        tasks = [t for t in tasks if t.source != "review"]
        
        def serialize_task(task: Task) -> dict:
            return {
                "id": task.id,
                "source": task.source,
                "status": task.status,
                "repository_url": task.prompt.repository_url,
                "description": task.prompt.description,
                "ticket_id": task.prompt.ticket_id,
                "ticket_summary": task.prompt.ticket_summary,
                "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "result": task.result,
                "error": task.error,
                "subtasks": [serialize_task(st) for st in task.subtasks] if task.subtasks else [],
            }
        
        return jsonify({
            "tasks": [serialize_task(task) for task in tasks],
            "count": len(tasks)
        }), 200
    
    @web_ui.route("/api/web/tasks/<task_id>", methods=["GET"])
    @require_basic_auth
    def get_task(task_id: str):
        task = global_task_store.get_task(task_id)
        
        if not task:
            return jsonify({
                "error": "Not Found",
                "message": f"Task {task_id} not found"
            }), 404
        
        def serialize_task(task: Task) -> dict:
            return {
                "id": task.id,
                "source": task.source,
                "status": task.status,
                "repository_url": task.prompt.repository_url,
                "description": task.prompt.description,
                "ticket_id": task.prompt.ticket_id,
                "ticket_summary": task.prompt.ticket_summary,
                "test_command": task.prompt.test_command,
                "base_branch": task.prompt.base_branch,
                "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "result": task.result,
                "error": task.error,
                "subtasks": [serialize_task(st) for st in task.subtasks] if task.subtasks else [],
            }
        
        return jsonify(serialize_task(task)), 200
    
    @web_ui.route("/api/web/tasks/<task_id>/retry", methods=["POST"])
    @require_basic_auth
    def retry_task(task_id: str):
        """Retry a failed task by creating a new task with the same prompt."""
        original_task = global_task_store.get_task(task_id)
        
        if not original_task:
            return jsonify({
                "error": "Not Found",
                "message": f"Task {task_id} not found"
            }), 404
        
        if original_task.status != "failed":
            return jsonify({
                "error": "Bad Request",
                "message": f"Task {task_id} is not in failed status. Only failed tasks can be retried."
            }), 400
        
        if original_task.source != "web":
            return jsonify({
                "error": "Bad Request",
                "message": "Only web-initiated tasks can be retried through the web interface."
            }), 400
        
        task_queue = getattr(current_app, "task_queue", None)
        if not task_queue:
            return jsonify({
                "error": "Service Unavailable",
                "message": "Task queue is not available. API may not be enabled."
            }), 503
        
        new_task_id = str(uuid.uuid4())
        new_task = Task(
            id=new_task_id,
            prompt=original_task.prompt,
            status="pending",
            submitted_at=datetime.utcnow(),
            source="web",
        )
        
        try:
            task_queue.enqueue(new_task)
        except Exception as e:
            return jsonify({
                "error": "Internal Server Error",
                "message": f"Failed to enqueue retry task: {str(e)}"
            }), 500
        
        return jsonify({
            "task_id": new_task_id,
            "original_task_id": task_id,
            "status": "pending",
            "message": "Task retry queued successfully"
        }), 202
    
    @web_ui.route("/api/web/repositories", methods=["GET"])
    @require_basic_auth
    def list_repositories():
        """List repositories accessible to the GitHub App installation."""
        github_app_auth = getattr(current_app, "github_app_auth", None)
        
        if not github_app_auth:
            return jsonify({
                "error": "Service Unavailable",
                "message": "GitHub App authentication not configured"
            }), 503
        
        try:
            api_url = github_app_auth.api_url
            headers = github_app_auth.get_auth_headers()
            
            url = f"{api_url}/installation/repositories"
            repositories = []
            page = 1
            per_page = 100
            
            while True:
                params = {"per_page": per_page, "page": page}
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                if response.status_code != 200:
                    if page == 1:
                        return jsonify({
                            "repositories": [],
                            "error": f"GitHub API error: {response.status_code}"
                        }), 200
                    break
                
                data = response.json()
                repos = data.get("repositories", [])
                
                if not repos:
                    break
                
                for repo in repos:
                    repositories.append({
                        "full_name": repo.get("full_name", ""),
                        "html_url": repo.get("html_url", ""),
                        "clone_url": repo.get("clone_url", ""),
                    })
                
                if len(repos) < per_page:
                    break
                
                page += 1
            
            return jsonify({
                "repositories": repositories,
                "count": len(repositories)
            }), 200
            
        except Exception as e:
            return jsonify({
                "repositories": [],
                "error": str(e)
            }), 200
    
    @web_ui.route("/api/web/tasks", methods=["POST"])
    @require_auth
    def submit_task():
        """Submit a new task for execution."""
        task_queue = getattr(current_app, "task_queue", None)
        if not task_queue:
            return jsonify({
                "error": "Service Unavailable",
                "message": "Task queue is not available. API may not be enabled."
            }), 503
        
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    "error": "Bad Request",
                    "message": "Request body must be JSON"
                }), 400
            
            if "repository_url" not in data:
                return jsonify({
                    "error": "Bad Request",
                    "message": "repository_url is required"
                }), 400
            
            if "description" not in data:
                return jsonify({
                    "error": "Bad Request",
                    "message": "description is required"
                }), 400
            
            try:
                prompt = TaskPrompt(
                    repository_url=data["repository_url"],
                    description=data["description"],
                    ticket_id=data.get("ticket_id"),
                    ticket_summary=data.get("ticket_summary"),
                    test_command=data.get("test_command"),
                    base_branch=data.get("base_branch"),
                )
            except ValueError as e:
                return jsonify({
                    "error": "Bad Request",
                    "message": str(e)
                }), 400
            
            task_id = str(uuid.uuid4())
            
            task = Task(
                id=task_id,
                prompt=prompt,
                status="pending",
                submitted_at=datetime.utcnow(),
                source="web",
            )
            
            try:
                task_queue.enqueue(task)
            except Exception as e:
                return jsonify({
                    "error": "Internal Server Error",
                    "message": f"Failed to enqueue task: {str(e)}"
                }), 500
            
            return jsonify({
                "task_id": task_id,
                "status": "pending",
                "message": "Task queued successfully"
            }), 202
        
        except Exception as e:
            return jsonify({
                "error": "Internal Server Error",
                "message": str(e)
            }), 500
    
    @web_ui.route("/api/web/tasks/<task_id>/logs", methods=["GET"])
    @require_basic_auth
    def stream_logs(task_id: str):
        """Stream logs for a task using Server-Sent Events."""
        task = global_task_store.get_task(task_id)
        
        if not task:
            return jsonify({
                "error": "Not Found",
                "message": f"Task {task_id} not found"
            }), 404
        
        source_filter = request.args.get("source")
        
        def generate():
            import time
            log_storage = get_log_storage(storage=global_task_store.storage)
            last_index = 0
            
            if task.status == "running":
                while True:
                    logs = log_storage.get_logs(task_id, source_filter=source_filter)
                    if len(logs) > last_index:
                        for log_entry in logs[last_index:]:
                            yield f"data: {json.dumps(log_entry)}\n\n"
                        last_index = len(logs)
                    
                    current_task = global_task_store.get_task(task_id)
                    if not current_task or current_task.status != "running":
                        break
                    
                    time.sleep(0.5)
            else:
                if task.logs:
                    logs = task.logs
                    if source_filter:
                        logs = [log for log in logs if log.get("source") == source_filter]
                    for log_entry in logs:
                        yield f"data: {json.dumps(log_entry)}\n\n"
                else:
                    logs = log_storage.get_logs(task_id, source_filter=source_filter)
                    for log_entry in logs:
                        yield f"data: {json.dumps(log_entry)}\n\n"
            
            yield "data: {\"type\": \"done\"}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    
    @web_ui.route("/api/web/tasks/<task_id>/logs/history", methods=["GET"])
    @require_basic_auth
    def get_log_history(task_id: str):
        """Get all logs for a completed task."""
        task = global_task_store.get_task(task_id)
        
        if not task:
            return jsonify({
                "error": "Not Found",
                "message": f"Task {task_id} not found"
            }), 404
        
        source_filter = request.args.get("source")
        
        if task.logs:
            logs = task.logs
        else:
            log_storage = get_log_storage(storage=global_task_store.storage)
            logs = log_storage.get_logs(task_id, source_filter=source_filter)
        
        if source_filter:
            logs = [log for log in logs if log.get("source") == source_filter]
        
        return jsonify({
            "task_id": task_id,
            "logs": logs,
            "count": len(logs)
        }), 200
    
    return web_ui

