"""Git operations for committing and pushing changes."""

import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from codebot.core.github_app import GitHubAppAuth
from codebot.core.utils import get_codebot_git_author_info, get_git_env, is_github_url


class GitOps:
    """Git operations for codebot."""
    
    def __init__(self, work_dir: Path, github_app_auth: Optional[GitHubAppAuth] = None):
        """
        Initialize git operations.
        
        Args:
            work_dir: Working directory with git repository
            github_app_auth: Optional GitHub App authentication instance
        """
        self.work_dir = work_dir
        self.github_app_auth = github_app_auth
    
    def _get_git_env(self) -> dict:
        bot_user_id = None
        bot_name = None
        api_url = None
        if self.github_app_auth:
            bot_user_id = self.github_app_auth.bot_user_id
            bot_name = self.github_app_auth.get_bot_login()
            api_url = self.github_app_auth.api_url
            if not bot_user_id:
                bot_user_id = self.github_app_auth.app_id
        return get_git_env(bot_user_id=bot_user_id, bot_name=bot_name, api_url=api_url)
    
    def _create_authenticated_url(self, repository_url: str) -> str:
        """
        Create authenticated URL for GitHub repository.
        
        Args:
            repository_url: Original repository URL
            
        Returns:
            Authenticated URL with embedded token
        """
        if not self.github_app_auth or not is_github_url(repository_url):
            return repository_url
        
        parsed = urlparse(repository_url)
        if not parsed.netloc:
            return repository_url
        
        path = parsed.path
        if not path.endswith(".git"):
            path += ".git"
        
        token = self.github_app_auth.get_installation_token()
        auth_url = f"https://oauth2:{token}@{parsed.netloc}{path}"
        return auth_url
    
    def _get_remote_url(self) -> Optional[str]:
        env = self._get_git_env()
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    
    def _set_remote_url(self, url: str) -> None:
        env = self._get_git_env()
        result = subprocess.run(
            ["git", "remote", "set-url", "origin", url],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to set remote URL: {result.stderr}")
    
    def commit_changes(self, message: str) -> None:
        """
        Commit all changes with the given message.
        
        Args:
            message: Commit message
        """
        env = self._get_git_env()
        
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to stage changes: {result.stderr}")
        
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to commit: {result.stderr}")
        
        print(f"Committed changes: {message}")
    
    def push_branch(self, branch_name: str) -> None:
        """
        Push the branch to remote origin.
        
        Args:
            branch_name: Name of the branch to push
        """
        env = self._get_git_env()
        
        original_url = None
        if self.github_app_auth:
            original_url = self._get_remote_url()
            if original_url:
                auth_url = self._create_authenticated_url(original_url)
                if auth_url != original_url:
                    print("Setting up authenticated remote for push...")
                    self._set_remote_url(auth_url)
        
        try:
            result = subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                env=env,
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Failed to push branch: {result.stderr}")
            
            print(f"Pushed branch {branch_name} to remote")
            
        finally:
            if original_url and self.github_app_auth:
                print("Restoring clean remote URL...")
                self._set_remote_url(original_url)
    
    def has_uncommitted_changes(self) -> bool:
        """
        Check if there are uncommitted changes.
        
        Returns:
            True if there are uncommitted changes, False otherwise
        """
        env = self._get_git_env()
        
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        return result.stdout.strip() != ""
    
    def get_latest_commit_hash(self) -> Optional[str]:
        """
        Get the hash of the latest commit.
        
        Returns:
            Commit hash or None if no commits exist
        """
        env = self._get_git_env()
        
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        
        return None
    
    def get_current_branch(self) -> Optional[str]:
        """
        Get the name of the current branch.
        
        Returns:
            Branch name or None if no branch is checked out
        """
        env = self._get_git_env()
        
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        
        return None
    
    def get_commit_message(self, commit_hash: str) -> str:
        """
        Get the commit message for a specific commit.
        
        Args:
            commit_hash: Commit hash
            
        Returns:
            Commit message
        """
        env = self._get_git_env()
        
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", commit_hash],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get commit message: {result.stderr}")
        
        return result.stdout.strip()
    
    def remove_co_author_trailers(self) -> None:
        """
        Remove Co-Authored-By trailers and unwanted text from the latest commit.
        
        Claude Code CLI adds "Co-Authored-By: Claude" trailers and "🤖 Generated with Claude Code"
        text to commits. This method rewrites the commit to remove those.
        """
        env = self._get_git_env()
        
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%B"],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            print(f"Warning: Failed to get commit message: {result.stderr}")
            return
        
        commit_message = result.stdout
        
        lines = commit_message.split("\n")
        cleaned_lines = []
        has_unwanted = False
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Co-Authored-By:"):
                has_unwanted = True
                continue
            if stripped == "🤖 Generated with Claude Code" or "🤖 Generated with Claude Code" in stripped:
                has_unwanted = True
                continue
            cleaned_lines.append(line)
        
        if not has_unwanted:
            return
        
        cleaned_message = "\n".join(cleaned_lines).strip()
        while cleaned_message.endswith("\n\n"):
            cleaned_message = cleaned_message[:-1]
        
        result = subprocess.run(
            ["git", "commit", "--amend", "-m", cleaned_message],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            print(f"Warning: Failed to clean commit message: {result.stderr}")
        else:
            print("Cleaned commit message (removed Co-Authored-By trailers and unwanted text)")
    
    def _is_authenticated_url(self, url: str) -> bool:
        """Check if URL contains authentication token."""
        return "oauth2:" in url or "@" in url and "token" in url
    
    def fetch_from_remote(self) -> bool:
        """
        Fetch latest changes from remote with proper authentication.
        
        Returns:
            True if fetch was successful, False otherwise
        """
        print("Fetching latest changes from remote...")
        
        original_url = None
        
        if self.github_app_auth:
            original_url = self._get_remote_url()
            if original_url and not self._is_authenticated_url(original_url):
                auth_url = self._create_authenticated_url(original_url)
                print("Setting up authenticated remote URL for fetch...")
                self._set_remote_url(auth_url)
        
        try:
            env = self._get_git_env()
            result = subprocess.run(
                ["git", "fetch", "origin"],
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                env=env,
            )
            
            if result.returncode != 0:
                print(f"Warning: Failed to fetch from remote: {result.stderr.strip()}")
                return False
            
            print("Successfully fetched from remote")
            return True
            
        finally:
            if self.github_app_auth and original_url:
                print("Restoring clean remote URL...")
                self._set_remote_url(original_url)
    
    def pull_latest_changes(self, branch_name: str) -> bool:
        """
        Pull latest changes from the specified branch with proper authentication.
        
        Args:
            branch_name: Name of the branch to pull from
            
        Returns:
            True if pull was successful, False otherwise
        """
        print(f"Pulling latest changes from branch: {branch_name}")
        
        original_url = None
        
        if self.github_app_auth:
            original_url = self._get_remote_url()
            if original_url and not self._is_authenticated_url(original_url):
                auth_url = self._create_authenticated_url(original_url)
                print("Setting up authenticated remote URL for pull...")
                self._set_remote_url(auth_url)
        
        try:
            env = self._get_git_env()
            result = subprocess.run(
                ["git", "pull", "origin", branch_name],
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                env=env,
            )
            
            if result.returncode != 0:
                print(f"Warning: Failed to pull latest changes: {result.stderr.strip()}")
                return False
            
            print("Successfully pulled latest changes")
            return True
            
        finally:
            if self.github_app_auth and original_url:
                print("Restoring clean remote URL...")
                self._set_remote_url(original_url)
    
    @staticmethod
    def clone_repository(repo_url: str, target_dir: Path, github_app_auth: Optional[GitHubAppAuth] = None) -> None:
        """
        Clone a repository into the target directory with optional authentication.
        
        Args:
            repo_url: Repository URL to clone
            target_dir: Target directory to clone into
            github_app_auth: Optional GitHub App authentication instance
        """
        auth_repo_url = repo_url
        
        if github_app_auth and is_github_url(repo_url):
            temp_git_ops = GitOps(target_dir, github_app_auth)
            auth_repo_url = temp_git_ops._create_authenticated_url(repo_url)
            print(f"Cloning repository with authentication")
        else:
            print(f"Cloning repository: {repo_url}")
        
        env = get_git_env()
        
        result = subprocess.run(
            ["git", "clone", auth_repo_url, str(target_dir)],
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.lower()
            if "authentication failed" in error_msg or "401" in error_msg:
                raise RuntimeError(
                    f"Authentication failed. Please check your GitHub App configuration and permissions.\n"
                    f"Error: {result.stderr}"
                )
            elif "not found" in error_msg or "404" in error_msg:
                raise RuntimeError(
                    f"Repository not found or access denied. Please check the repository URL and GitHub App permissions.\n"
                    f"Error: {result.stderr}"
                )
            else:
                raise RuntimeError(f"Failed to clone repository: {result.stderr}")
        
        if github_app_auth and is_github_url(repo_url):
            git_ops = GitOps(target_dir, github_app_auth)
            git_ops.reset_remote_url(repo_url)
    
    def reset_remote_url(self, clean_url: str) -> None:
        """
        Reset remote URL to clean format (remove embedded credentials).
        
        Args:
            clean_url: Clean repository URL without credentials
        """
        parsed = urlparse(clean_url)
        
        path = parsed.path
        if not path.endswith(".git"):
            path += ".git"
        
        clean_remote_url = f"https://{parsed.netloc}{path}"
        
        env = self._get_git_env()
        result = subprocess.run(
            ["git", "remote", "set-url", "origin", clean_remote_url],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            print(f"Warning: Failed to reset remote URL: {result.stderr}")
        else:
            print(f"Reset remote URL to clean format: {clean_remote_url}")
    
    def detect_default_branch(self) -> str:
        """
        Detect the default branch of the repository.
        
        Returns:
            Name of the default branch (main or master)
        """
        env = self._get_git_env()
        
        result = subprocess.run(
            ["git", "remote", "show", "origin"],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "HEAD branch:" in line:
                    return line.split("HEAD branch:")[1].strip()
        
        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode == 0:
            branches = result.stdout
            if "main" in branches:
                return "main"
            elif "master" in branches:
                return "master"
        
        return "main"
    
    def checkout_branch(self, branch_name: str) -> None:
        """
        Checkout the specified branch.
        
        Args:
            branch_name: Name of the branch to checkout
        """
        env = self._get_git_env()
        
        result = subprocess.run(
            ["git", "checkout", branch_name],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to checkout branch {branch_name}: {result.stderr}"
            )
    
    def create_branch(self, branch_name: str) -> None:
        """
        Create and checkout a new branch.
        
        Args:
            branch_name: Name of the branch to create
        """
        env = self._get_git_env()
        
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to create branch {branch_name}: {result.stderr}"
            )
    
    def configure_git_author(self) -> None:
        """Configure git author and committer information for codebot."""
        if not self.github_app_auth or not self.work_dir:
            return
        
        bot_user_id = self.github_app_auth.bot_user_id
        if not bot_user_id:
            app_id = self.github_app_auth.app_id
            if app_id:
                print(f"Warning: Could not retrieve bot user ID, using app ID as fallback: {app_id}")
                bot_user_id = app_id
            else:
                return
        
        bot_name = self.github_app_auth.get_bot_login()
        api_url = self.github_app_auth.api_url
        author_info = get_codebot_git_author_info(bot_user_id, bot_name, api_url)
        env = self._get_git_env()
        
        result = subprocess.run(
            ["git", "config", "user.name", author_info["author_name"]],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            print(f"Warning: Failed to set git user.name: {result.stderr}")
        
        result = subprocess.run(
            ["git", "config", "user.email", author_info["author_email"]],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            print(f"Warning: Failed to set git user.email: {result.stderr}")
        else:
            print(f"Configured git author: {author_info['author_name']} <{author_info['author_email']}>")

