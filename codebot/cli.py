"""CLI interface for codebot."""

import os
import sys
import threading
from pathlib import Path

import click
from dotenv import load_dotenv

from codebot.orchestrator import Orchestrator
from codebot.parser import parse_task_prompt, parse_task_prompt_file
from codebot.utils import validate_github_token


@click.group()
def cli():
    """Codebot CLI - AI-assisted development task automation."""
    pass


@cli.command(name="run")
@click.option(
    "--task-prompt",
    type=str,
    help="Task prompt as JSON or YAML string",
)
@click.option(
    "--task-prompt-file",
    type=click.Path(exists=True),
    help="Path to task prompt file (JSON or YAML)",
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
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def run(
    task_prompt: str,
    task_prompt_file: str,
    work_dir: str,
    github_token: str,
    verbose: bool,
) -> None:
    """
    Codebot CLI - AI-assisted development task automation.
    
    This tool accepts task prompts, clones repositories, runs Claude Code CLI,
    and creates GitHub pull requests.
    
    Example:
        codebot --task-prompt-file task.yaml
    
    Example task prompt (YAML):
        repository_url: https://github.com/user/repo.git
        ticket_id: PROJ-123
        ticket_summary: fix-login-bug
        description: |
          Fix the login authentication bug.
          Ensure all tests pass.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Parse task prompt
    try:
        if task_prompt:
            task = parse_task_prompt(task_prompt)
        elif task_prompt_file:
            task = parse_task_prompt_file(task_prompt_file)
        else:
            click.echo("Error: Either --task-prompt or --task-prompt-file must be provided", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error parsing task prompt: {e}", err=True)
        sys.exit(1)
    
    # Determine work directory
    if work_dir:
        work_base_dir = Path(work_dir)
    else:
        work_base_dir = Path.cwd() / "codebot_workspace"
    
    work_base_dir.mkdir(parents=True, exist_ok=True)
    
    # Get GitHub token from flag, environment variable, or .env file
    effective_token = github_token or os.getenv("GITHUB_TOKEN")
    
    # Validate GitHub token if available
    if effective_token:
        print("Validating GitHub token...")
        if not validate_github_token(effective_token):
            click.echo("Error: Invalid GitHub token. Please check your token and try again.", err=True)
            click.echo("Make sure your token has the correct permissions (repo access for private repos).", err=True)
            sys.exit(1)
        print("GitHub token validated successfully")
    else:
        print("Warning: No GitHub token found. This may cause issues with private repositories.")
    
    # Create and run orchestrator
    try:
        orchestrator = Orchestrator(
            task=task,
            work_base_dir=work_base_dir,
            github_token=effective_token,
        )
        orchestrator.run()
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        if verbose:
            import traceback
            click.echo(f"\nError details:", err=True)
            traceback.print_exc()
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command(name="serve")
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
    help="Enable debug mode",
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
    # Load environment variables from .env file
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
    from codebot.webhook_server import app, review_queue, start_server
    from codebot.review_processor import ReviewProcessor
    
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


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
