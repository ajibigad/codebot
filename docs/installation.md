# Installation Guide

This guide will help you install and set up Codebot on your system.

## Prerequisites

Before installing Codebot, ensure you have the following:

### Required

- **Python 3.11+** - Codebot requires Python 3.11 or higher
- **uv package manager** - For dependency management
- **Claude Code CLI** - The AI agent that performs code changes
- **Git** - Configured with authentication for cloning repositories
- **GitHub Personal Access Token** - For creating pull requests and API access

### System Requirements

- macOS or Linux
- At least 2GB of free disk space
- Internet connection for API calls and repository access

## Step 1: Install uv Package Manager

If you don't have `uv` installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify installation:

```bash
uv --version
```

## Step 2: Install Claude Code CLI

Follow the official instructions at [Anthropic's Claude Code Documentation](https://www.anthropic.com/claude/docs/claude-code) to install Claude Code CLI.

Verify installation:

```bash
claude --version
```

## Step 3: Install Codebot

```bash
# Clone the repository
git clone https://github.com/yourusername/codebot.git
cd codebot

# Install dependencies
uv sync

# For corporate environments with restricted PyPI access:
# uv sync --index-url https://pypi.company.com/simple

# Activate the virtual environment
source .venv/bin/activate

# Verify installation
codebot --help
```

**Note:** You need to activate the virtual environment each time you open a new terminal, or use `uv run codebot` as a shortcut without activation.

## Step 4: Configure GitHub Token

Codebot needs a GitHub Personal Access Token to create pull requests and interact with the GitHub API.

### Create a GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token" (classic or fine-grained)

### Required Permissions

**For Classic Tokens:**
- ✅ `repo` (full repository access)

**For Fine-Grained Tokens:**
- ✅ **Pull requests**: Read and Write
- ✅ **Contents**: Read and Write
- ✅ **Metadata**: Read (automatic)

### Set the Token

**Option 1: Environment Variable**

```bash
export GITHUB_TOKEN="your_github_token_here"
```

**Option 2: .env File**

Create a `.env` file in your project directory:

```bash
GITHUB_TOKEN=your_github_token_here
```

## Step 5: Verify Installation

Test that everything is working:

```bash
# Check codebot command
uv run codebot --help

# Verify GitHub token
uv run codebot run --help
```

You should see the help output for the codebot CLI.

## Optional: Webhook Server Setup

If you plan to use the webhook server for PR review automation:

### 1. Set Webhook Secret

```bash
export GITHUB_WEBHOOK_SECRET="your_webhook_secret_here"
```

### 2. Set API Keys (for HTTP API)

```bash
export CODEBOT_API_KEYS="secret-key-1,secret-key-2"
```

### 3. Configure GitHub Webhook

See the [Webhooks Guide](webhooks.md) for detailed webhook configuration.

## Corporate Environment Setup

If you're in a corporate environment where PyPI access is restricted, you may need to use an internal PyPI mirror.

### Using Internal PyPI Mirror

```bash
# Install with custom index URL
uv sync --index-url https://pypi.company.com/simple

# Or set it permanently in .uv.toml
echo '[index]' > .uv.toml
echo 'url = "https://pypi.company.com/simple"' >> .uv.toml
```

### Managing uv.lock Changes

The `uv.lock` file may be updated when using different index URLs. This is normal and ensures reproducible builds in your environment. You have two options:

**Option 1: Commit the updated lock file** (recommended for teams using the same corporate environment)
```bash
git add uv.lock
git commit -m "Update uv.lock for corporate PyPI mirror"
```

**Option 2: Keep local changes only** (if working in mixed environments)
```bash
# Reset the lock file to avoid committing corporate-specific changes
git checkout HEAD -- uv.lock
```

### Environment-Specific Configuration

Create a `.uv.toml` file that can be customized per environment without affecting the repository:

```toml
# .uv.toml (add to .gitignore if needed)
[index]
url = "https://pypi.company.com/simple"
```

## Troubleshooting

For installation issues and common problems, see the [Troubleshooting Guide](troubleshooting.md).

## Next Steps

- [CLI Usage Guide](cli-usage.md) - Learn how to run tasks
- [Configuration Guide](configuration.md) - Customize codebot settings
- [Examples](examples.md) - See practical use cases

---

[← Back to Documentation](index.md)

