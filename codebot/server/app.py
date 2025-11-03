"""Server app for handling webhooks and HTTP requests."""

import os
import sys
import threading
from pathlib import Path

import click
from dotenv import load_dotenv

from codebot.core.utils import validate_github_token


@click.command(name="serve")
@click.option(
    "--port",
    type=int,
    default=5000,
    help="Port to run webhook server on (default: 5000)",
)
@click.option(
    "--work-dir",
    type=click.Path(),
    default=None,
    help="Base directory for work spaces (defaults to ./codebot_workspace)",
)
@click.option(
    "--github-token",
    type=str,
    default=None,
    help="GitHub token (defaults to GITHUB_TOKEN env var or .env file)",
)
@click.option(
    "--webhook-secret",
    type=str,
    default=None,
    help="GitHub webhook secret (defaults to GITHUB_WEBHOOK_SECRET env var or .env file)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode (auto-reload on code changes, detailed errors)",
)
def serve(
    port: int,
    work_dir: str,
    github_token: str,
    webhook_secret: str,
    debug: bool,
) -> None:
    """
    Start webhook server to handle PR review comments.
    
    This command starts a Flask server that listens for GitHub webhook events
    for PR review comments. When a comment is received, it queues it for
    processing by Claude Code.
    
    Example:
        codebot serve --port 5000
    
    Before running, configure a GitHub webhook:
    1. Go to repository Settings > Webhooks
    2. Add webhook URL: https://your-server.com/webhook
    3. Content type: application/json
    4. Secret: Set GITHUB_WEBHOOK_SECRET env var
    5. Events: Select "Issue comments", "Pull request reviews", and "Pull request review comments"
    """
    load_dotenv()
    
    # Get GitHub token
    effective_token = github_token or os.getenv("GITHUB_TOKEN")
    
    if not effective_token:
        click.echo("Error: GitHub token is required. Set GITHUB_TOKEN env var or use --github-token", err=True)
        sys.exit(1)
    
    # Validate GitHub token
    print("Validating GitHub token...")
    if not validate_github_token(effective_token):
        click.echo("Error: Invalid GitHub token. Please check your token and try again.", err=True)
        sys.exit(1)
    print("GitHub token validated successfully")
    
    # Get webhook secret
    effective_secret = webhook_secret or os.getenv("GITHUB_WEBHOOK_SECRET")
    
    if not effective_secret:
        click.echo("Error: Webhook secret is required. Set GITHUB_WEBHOOK_SECRET env var or use --webhook-secret", err=True)
        sys.exit(1)
    
    # Set webhook secret in environment for the server
    os.environ["GITHUB_WEBHOOK_SECRET"] = effective_secret
    
    # Determine work directory
    if work_dir:
        work_base_dir = Path(work_dir)
    else:
        work_base_dir = Path.cwd() / "codebot_workspace"
    
    work_base_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Starting webhook server on port {port}...")
    print(f"Work directory: {work_base_dir}")
    print(f"Health check: http://localhost:{port}/health")
    print(f"Webhook endpoint: http://localhost:{port}/webhook")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Import here to avoid loading Flask unless needed
    from codebot.server.webhook_server import app, review_queue, start_server
    from codebot.server.review_processor import ReviewProcessor
    
    # Create and start review processor in background thread
    processor = ReviewProcessor(
        review_queue=review_queue,
        workspace_base_dir=work_base_dir,
        github_token=effective_token,
    )
    
    processor_thread = threading.Thread(target=processor.start, daemon=True)
    processor_thread.start()
    
    # Start Flask server (blocking)
    try:
        start_server(port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        processor.stop()
        sys.exit(0)

