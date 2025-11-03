"""Utility functions for codebot."""

import hashlib
import os
import uuid
from pathlib import Path
from typing import Dict, Optional


def validate_github_token(token: str) -> bool:
    """
    Validate a GitHub token by making a simple API call.
    
    Args:
        token: GitHub personal access token
        
    Returns:
        True if token is valid, False otherwise
    """
    import requests
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    try:
        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_git_env() -> Dict[str, str]:
    """
    Get git environment variables for non-interactive operation.
    
    Returns:
        Dictionary of environment variables for git operations
    """
    return {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",  # Disable terminal prompts
        "GIT_ASKPASS": "echo",       # Use echo as askpass (returns empty)
    }


def generate_short_uuid() -> str:
    """Generate a short UUID (7 characters) for use in branch names and directory names."""
    uuid_str = str(uuid.uuid4())
    sha256_hash = hashlib.sha256(uuid_str.encode()).hexdigest()
    return sha256_hash[:7]


def generate_branch_name(
    ticket_id: Optional[str] = None,
    short_name: Optional[str] = None,
    uuid_part: Optional[str] = None,
) -> str:
    """
    Generate a branch name in the format: u/codebot/[TICKET-ID/]<uuid>/<short-name>
    
    Args:
        ticket_id: Optional ticket ID (e.g., "PROJ-123")
        short_name: Short descriptive name for the task
        uuid_part: Optional UUID to use (generates new one if not provided)
        
    Returns:
        Branch name string
    """
    if uuid_part is None:
        uuid_part = generate_short_uuid()
    
    parts = ["u", "codebot"]
    
    if ticket_id:
        parts.append(ticket_id)
    
    parts.append(uuid_part)
    
    if short_name:
        parts.append(short_name)
    
    return "/".join(parts)


def generate_directory_name(ticket_id: Optional[str] = None, uuid_part: Optional[str] = None) -> str:
    """
    Generate a directory name in the format: task_[TICKET-ID_]uuid
    
    Args:
        ticket_id: Optional ticket ID (e.g., "PROJ-123")
        uuid_part: Optional UUID to use (generates new one if not provided)
        
    Returns:
        Directory name string
    """
    if uuid_part is None:
        uuid_part = generate_short_uuid()
    
    if ticket_id:
        return f"task_{ticket_id}_{uuid_part}"
    else:
        return f"task_{uuid_part}"


def extract_uuid_from_branch(branch_name: str) -> Optional[str]:
    """
    Extract UUID from a codebot branch name.
    
    Branch format: u/codebot/[TICKET-ID/]UUID[/name]
    
    Args:
        branch_name: Branch name (e.g., "u/codebot/TASK-123/abc1234/feature")
        
    Returns:
        UUID string or None if not found
    """
    parts = branch_name.split("/")
    
    # Branch should start with u/codebot
    if len(parts) < 3 or parts[0] != "u" or parts[1] != "codebot":
        return None
    
    # Find the UUID part (7-character hash)
    for part in parts[2:]:
        if len(part) == 7 and all(c in "0123456789abcdef" for c in part):
            return part
    
    return None


def find_workspace_by_uuid(base_dir: Path, uuid: str) -> Optional[Path]:
    """
    Find a workspace directory by UUID.
    
    Workspace format: task_[TICKET-ID_]uuid
    
    Args:
        base_dir: Base directory containing workspaces
        uuid: UUID to search for
        
    Returns:
        Path to workspace or None if not found
    """
    if not base_dir.exists():
        return None
    
    # Search for directories matching the pattern
    for item in base_dir.iterdir():
        if item.is_dir() and item.name.endswith(f"_{uuid}"):
            return item
        elif item.is_dir() and item.name == f"task_{uuid}":
            return item
    
    return None
