"""GitHub webhook server for handling PR review comments."""

import hashlib
import hmac
import os
import threading
from queue import Queue
from typing import Optional

from flask import Flask, request, jsonify


# Global FIFO queue for review comments
review_queue: Queue = Queue()

# Flask app
app = Flask(__name__)


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature.
    
    Args:
        payload: Request payload bytes
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret
        
    Returns:
        True if signature is valid
    """
    if not signature or not secret:
        return False
    
    # GitHub sends signature as "sha256=<hash>"
    if not signature.startswith("sha256="):
        return False
    
    expected_signature = signature[7:]  # Remove "sha256=" prefix
    
    # Compute HMAC
    mac = hmac.new(secret.encode(), payload, hashlib.sha256)
    computed_signature = mac.hexdigest()
    
    # Constant-time comparison
    return hmac.compare_digest(computed_signature, expected_signature)


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """Handle incoming GitHub webhook events."""
    # Get webhook secret from environment
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    
    if not webhook_secret:
        app.logger.error("GITHUB_WEBHOOK_SECRET not set")
        return jsonify({"error": "Webhook secret not configured"}), 500
    
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(request.data, signature, webhook_secret):
        app.logger.warning("Invalid webhook signature")
        return jsonify({"error": "Invalid signature"}), 401
    
    # Get event type
    event_type = request.headers.get("X-GitHub-Event", "")
    
    # Parse payload
    payload = request.json
    
    if not payload:
        return jsonify({"error": "Invalid payload"}), 400
    
    # Handle pull request comment events
    if event_type == "pull_request_review_comment":
        return handle_review_comment(payload)
    elif event_type == "pull_request_review":
        return handle_review(payload)
    elif event_type == "issue_comment":
        return handle_issue_comment(payload)
    else:
        app.logger.info(f"Ignoring event type: {event_type}")
        return jsonify({"message": "Event type not handled"}), 200


def handle_review_comment(payload: dict) -> tuple:
    """
    Handle pull_request_review_comment event.
    
    Args:
        payload: GitHub webhook payload
        
    Returns:
        Response tuple (data, status_code)
    """
    action = payload.get("action")
    
    # Only handle created comments
    if action != "created":
        return jsonify({"message": f"Ignoring action: {action}"}), 200
    
    comment = payload.get("comment", {})
    pull_request = payload.get("pull_request", {})
    repository = payload.get("repository", {})
    
    # Extract relevant information
    comment_data = {
        "type": "review_comment",
        "comment_id": comment.get("id"),
        "comment_body": comment.get("body", ""),
        "pr_number": pull_request.get("number"),
        "pr_title": pull_request.get("title"),
        "pr_body": pull_request.get("body", ""),
        "branch_name": pull_request.get("head", {}).get("ref"),
        "repo_url": repository.get("clone_url"),
        "repo_owner": repository.get("owner", {}).get("login"),
        "repo_name": repository.get("name"),
        "comment_path": comment.get("path"),  # File being commented on
        "comment_line": comment.get("line"),  # Line number
    }
    
    # Add to queue
    review_queue.put(comment_data)
    
    app.logger.info(f"Queued review comment for PR #{comment_data['pr_number']}")
    
    return jsonify({"message": "Comment queued for processing"}), 200


def handle_review(payload: dict) -> tuple:
    """
    Handle pull_request_review event (review submitted with comments).
    
    Args:
        payload: GitHub webhook payload
        
    Returns:
        Response tuple (data, status_code)
    """
    action = payload.get("action")
    
    # Only handle submitted reviews
    if action != "submitted":
        return jsonify({"message": f"Ignoring action: {action}"}), 200
    
    review = payload.get("review", {})
    pull_request = payload.get("pull_request", {})
    repository = payload.get("repository", {})
    
    # Extract relevant information
    review_body = review.get("body") or ""
    
    # Skip if review has no body (only inline comments)
    if not review_body.strip():
        return jsonify({"message": "Review has no body, skipping"}), 200
    
    comment_data = {
        "type": "review",
        "comment_id": review.get("id"),
        "comment_body": review_body,
        "pr_number": pull_request.get("number"),
        "pr_title": pull_request.get("title"),
        "pr_body": pull_request.get("body", ""),
        "branch_name": pull_request.get("head", {}).get("ref"),
        "repo_url": repository.get("clone_url"),
        "repo_owner": repository.get("owner", {}).get("login"),
        "repo_name": repository.get("name"),
        "review_state": review.get("state"),  # APPROVED, CHANGES_REQUESTED, COMMENTED
    }
    
    # Add to queue
    review_queue.put(comment_data)
    
    app.logger.info(f"Queued review for PR #{comment_data['pr_number']}")
    
    return jsonify({"message": "Review queued for processing"}), 200


def handle_issue_comment(payload: dict) -> tuple:
    """
    Handle issue_comment event (comments on PRs).
    
    GitHub treats PR comments as issue comments, so we need to check if this
    is actually a PR comment and not just a regular issue comment.
    
    Args:
        payload: GitHub webhook payload
        
    Returns:
        Response tuple (data, status_code)
    """
    action = payload.get("action")
    
    # Only handle created comments
    if action != "created":
        return jsonify({"message": f"Ignoring action: {action}"}), 200
    
    # Check if this is a PR comment (not a regular issue comment)
    issue = payload.get("issue", {})
    if not issue.get("pull_request"):
        app.logger.info("Ignoring non-PR issue comment")
        return jsonify({"message": "Not a PR comment"}), 200
    
    comment = payload.get("comment", {})
    repository = payload.get("repository", {})
    
    # Extract PR number from issue
    pr_number = issue.get("number")
    
    # Extract relevant information
    comment_data = {
        "type": "issue_comment",
        "comment_id": comment.get("id"),
        "comment_body": comment.get("body", ""),
        "pr_number": pr_number,
        "pr_title": issue.get("title"),
        "pr_body": issue.get("body", ""),
        "branch_name": None,  # Will be fetched from PR details
        "repo_url": repository.get("clone_url"),
        "repo_owner": repository.get("owner", {}).get("login"),
        "repo_name": repository.get("name"),
    }
    
    # Add to queue
    review_queue.put(comment_data)
    
    app.logger.info(f"Queued issue comment for PR #{comment_data['pr_number']}")
    
    return jsonify({"message": "Comment queued for processing"}), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "queue_size": review_queue.qsize()
    }), 200


def start_server(port: int = 5000, debug: bool = False):
    """
    Start the webhook server.
    
    Args:
        port: Port to listen on
        debug: Enable debug mode
    """
    app.run(host="0.0.0.0", port=port, debug=debug)

