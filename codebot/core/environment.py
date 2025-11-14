"""Environment manager for isolated development environments."""

from pathlib import Path
from typing import Optional

from codebot.core.github_app import GitHubAppAuth
from codebot.core.git_ops import GitOps
from codebot.core.models import TaskPrompt
from codebot.core.utils import (
    generate_branch_name, 
    generate_directory_name, 
    generate_short_uuid
)


class EnvironmentManager:
    """Manages isolated development environments for codebot tasks."""
    
    def __init__(self, base_dir: Path, task: TaskPrompt, github_app_auth: Optional[GitHubAppAuth] = None):
        """
        Initialize the environment manager.
        
        Args:
            base_dir: Base directory for creating temporary workspaces
            task: Task prompt containing repository and task details
            github_app_auth: GitHub App authentication instance (optional)
        """
        self.base_dir = base_dir
        self.task = task
        self.github_app_auth = github_app_auth
        self.work_dir: Optional[Path] = None
        self.branch_name: Optional[str] = None
        self.default_branch: Optional[str] = None
        self._git_ops: Optional[GitOps] = None
    
    def setup_environment(self) -> Path:
        """
        Setup the isolated environment by creating directory, cloning repo, and checking out branch.
        
        Returns:
            Path to the working directory
        """
        uuid_part = generate_short_uuid()
        
        dir_name = generate_directory_name(self.task.ticket_id, uuid_part)
        self.work_dir = self.base_dir / dir_name
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Created work directory: {self.work_dir}")
        
        GitOps.clone_repository(self.task.repository_url, self.work_dir, self.github_app_auth)
        
        self.git_ops.configure_git_author()
        
        self.default_branch = self.git_ops.detect_default_branch()
        print(f"Detected default branch: {self.default_branch}")
        
        base_branch = self.task.base_branch or self.default_branch
        self.git_ops.checkout_branch(base_branch)
        
        self.branch_name = generate_branch_name(
            ticket_id=self.task.ticket_id,
            short_name=self.task.ticket_summary,
            uuid_part=uuid_part,
        )
        print(f"Creating branch: {self.branch_name}")
        self.git_ops.create_branch(self.branch_name)
        
        return self.work_dir
    
    def reuse_workspace(self, work_dir: Path, branch_name: str, repo_url: str) -> Path:
        """
        Reuse an existing workspace and update it to latest remote state.
        
        Args:
            work_dir: Path to existing workspace
            branch_name: Branch name to checkout
            repo_url: Repository URL for authentication
            
        Returns:
            Path to the working directory
        """
        self.work_dir = work_dir
        self.branch_name = branch_name
        self.task.repository_url = repo_url
        
        print(f"Reusing workspace: {self.work_dir}")
        print(f"Updating branch: {branch_name}")
        
        self._git_ops = None
        
        self._update_workspace()
        
        self.git_ops.configure_git_author()
        
        return self.work_dir
    
    @property
    def git_ops(self) -> GitOps:
        """Get GitOps instance for the current workspace."""
        if self._git_ops is None:
            if not self.work_dir:
                raise RuntimeError("Cannot create GitOps: work_dir is not set")
            self._git_ops = GitOps(self.work_dir, self.github_app_auth)
        return self._git_ops
    
    def _update_workspace(self) -> None:
        """Update workspace to latest remote state."""
        if not self.work_dir:
            return
        
        if not self.git_ops.fetch_from_remote():
            return
        
        print(f"Checking out branch: {self.branch_name}")
        self.git_ops.checkout_branch(self.branch_name)
        
        self.git_ops.pull_latest_changes(self.branch_name)
        
        print("Workspace updated successfully")
    
