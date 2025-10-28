"""Claude Code runner specialized for handling PR review comments."""

import subprocess
from pathlib import Path
from typing import Optional

from codebot.claude_runner import ClaudeRunner


class ReviewRunner:
    """Runner for Claude Code CLI specialized for PR review comments."""
    
    def __init__(self, work_dir: Path):
        """
        Initialize the review runner.
        
        Args:
            work_dir: Working directory where Claude Code should run
        """
        self.work_dir = work_dir
        self.claude_runner = ClaudeRunner(work_dir)
    
    def handle_review_comment(
        self,
        comment_body: str,
        pr_context: dict,
        is_change_request: bool = False,
    ) -> subprocess.CompletedProcess:
        """
        Handle a PR review comment using Claude Code.
        
        Args:
            comment_body: The review comment text
            pr_context: Dictionary with PR context (title, description, files_changed)
            is_change_request: Whether this is a change request or query
            
        Returns:
            CompletedProcess with the command result
        """
        # Build specialized system prompt for code reviews
        system_prompt = self._build_review_system_prompt(
            comment_body,
            pr_context,
            is_change_request
        )
        
        # Build task description
        if is_change_request:
            task_description = (
                f"Code Review Change Request:\n\n"
                f"{comment_body}\n\n"
                f"Please make the requested changes, test them, and commit with a clear message."
            )
        else:
            task_description = (
                f"Code Review Query:\n\n"
                f"{comment_body}\n\n"
                f"Please provide a clear, helpful answer. Do not make any code changes."
            )
        
        # Run Claude Code
        return self.claude_runner.run_task(
            description=task_description,
            append_system_prompt=system_prompt,
        )
    
    def _build_review_system_prompt(
        self,
        comment_body: str,
        pr_context: dict,
        is_change_request: bool,
    ) -> str:
        """
        Build a specialized system prompt for code review responses.
        
        Args:
            comment_body: The review comment
            pr_context: PR context information
            is_change_request: Whether this is a change request
            
        Returns:
            System prompt string
        """
        prompt_parts = []
        
        # Context about the review
        prompt_parts.append("=" * 80)
        prompt_parts.append("CODE REVIEW CONTEXT")
        prompt_parts.append("=" * 80)
        prompt_parts.append("")
        prompt_parts.append("You are responding to a code review comment on a pull request.")
        prompt_parts.append("")
        
        # PR information
        if pr_context.get("pr_title"):
            prompt_parts.append(f"PR Title: {pr_context['pr_title']}")
        
        if pr_context.get("pr_body"):
            prompt_parts.append(f"\nOriginal Task Description:")
            prompt_parts.append(pr_context['pr_body'])
        
        if pr_context.get("files_changed"):
            prompt_parts.append(f"\nFiles Changed in This PR:")
            prompt_parts.append("```")
            prompt_parts.append(pr_context['files_changed'])
            prompt_parts.append("```")
        
        prompt_parts.append("")
        prompt_parts.append("=" * 80)
        prompt_parts.append("REVIEW COMMENT")
        prompt_parts.append("=" * 80)
        prompt_parts.append("")
        prompt_parts.append(comment_body)
        prompt_parts.append("")
        prompt_parts.append("=" * 80)
        
        # Instructions based on comment type
        if is_change_request:
            prompt_parts.append("")
            prompt_parts.append("This is a CHANGE REQUEST. You should:")
            prompt_parts.append("1. Understand what changes are being requested")
            prompt_parts.append("2. Make the necessary code changes")
            prompt_parts.append("3. Test the changes to ensure they work")
            prompt_parts.append("4. Run all tests to ensure nothing is broken")
            prompt_parts.append("5. Commit the changes with a clear message")
            prompt_parts.append("")
            prompt_parts.append("Your commit message should reference that this addresses a review comment.")
        else:
            prompt_parts.append("")
            prompt_parts.append("This is a QUERY/QUESTION. You should:")
            prompt_parts.append("1. Understand what is being asked")
            prompt_parts.append("2. Provide a clear, helpful answer")
            prompt_parts.append("3. Reference specific code or files if relevant")
            prompt_parts.append("4. DO NOT make any code changes")
            prompt_parts.append("")
            prompt_parts.append("Your response will be posted as a comment reply.")
        
        return "\n".join(prompt_parts)

