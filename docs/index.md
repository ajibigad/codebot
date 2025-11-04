# Codebot Documentation

Welcome to the Codebot documentation! Codebot is a CLI tool that automates development tasks using AI agents like Claude Code CLI. It can execute tasks from the command line, accept HTTP API requests, and automatically respond to PR review comments.

## Table of Contents

### Getting Started

- [Installation](installation.md) - Prerequisites, setup, and installation steps
- [Quick Start](#quick-start) - Get up and running in minutes

### Usage Guides

- [CLI Usage](cli-usage.md) - Running tasks from the command line
- [HTTP API](http-api.md) - Programmatic task submission via REST API
- [Webhooks](webhooks.md) - Automated PR review comment handling

### Configuration

- [Configuration Guide](configuration.md) - Environment variables, API keys, and settings

### Advanced

- [Architecture](architecture.md) - How codebot works internally
- [Examples](examples.md) - Common use cases and practical recipes

---

## Quick Start

### 1. Install Codebot

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install codebot
git clone https://github.com/yourusername/codebot.git
cd codebot
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### 2. Set Up GitHub Token

```bash
export GITHUB_TOKEN="your_github_token_here"
```

### 3. Run Your First Task

```bash
codebot run --task-prompt '{"repository_url": "https://github.com/user/repo.git", "description": "Add README file"}'
```

That's it! Codebot will:
- Clone the repository
- Run Claude Code CLI to make changes
- Create a pull request with the changes

---

## What Can Codebot Do?

### 🤖 CLI Task Execution
Run development tasks from the command line with simple YAML or JSON prompts.

[Learn more →](cli-usage.md)

### 🌐 HTTP API
Submit tasks programmatically via REST API with async execution and status tracking.

[Learn more →](http-api.md)

### 🔄 PR Review Automation
Automatically respond to PR review comments with code changes or answers.

[Learn more →](webhooks.md)

---

## Need Help?

- **Installation issues?** See [Installation Guide](installation.md)
- **Configuration questions?** Check [Configuration Guide](configuration.md)
- **Want examples?** Browse [Examples](examples.md)
- **Curious how it works?** Read [Architecture](architecture.md)

---

## Contributing

Codebot is open source! Contributions are welcome. See the main [README](../README.md) for development setup instructions.

