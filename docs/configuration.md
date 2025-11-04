# Configuration Guide

Configure Codebot using environment variables and command-line options.

## Environment Variables

### Core Configuration

#### GITHUB_TOKEN

**Required**: Yes  
**Description**: GitHub Personal Access Token for API access  
**Example**: `ghp_xxxxxxxxxxxxxxxxxxxx`

```bash
export GITHUB_TOKEN="your_github_token_here"
```

Or in `.env` file:

```
GITHUB_TOKEN=your_github_token_here
```

**Required Permissions:**

Classic Token:
- ✅ `repo` (full repository access)

Fine-Grained Token:
- ✅ Pull requests: Read and Write
- ✅ Contents: Read and Write
- ✅ Metadata: Read (automatic)

#### GITHUB_WEBHOOK_SECRET

**Required**: For webhook server  
**Description**: Secret for verifying GitHub webhook signatures  
**Example**: Any secure random string

```bash
export GITHUB_WEBHOOK_SECRET="your_webhook_secret_here"
```

### HTTP API Configuration

#### CODEBOT_API_KEYS

**Required**: For HTTP API  
**Description**: Comma-separated list of valid API keys  
**Example**: `secret-key-1,secret-key-2`

```bash
export CODEBOT_API_KEYS="secret-key-1,secret-key-2"
```

#### CODEBOT_MAX_WORKERS

**Default**: 1  
**Description**: Maximum number of task processor worker threads  
**Range**: 1-10 (recommended)

```bash
export CODEBOT_MAX_WORKERS=4
```

#### CODEBOT_MAX_QUEUE_SIZE

**Default**: 100  
**Description**: Maximum number of tasks in queue  
**Range**: 1-1000

```bash
export CODEBOT_MAX_QUEUE_SIZE=200
```

#### CODEBOT_TASK_RETENTION

**Default**: 86400 (24 hours)  
**Description**: Task data retention period in seconds  

```bash
export CODEBOT_TASK_RETENTION=172800  # 48 hours
```

## .env File Support

Create a `.env` file in your project directory:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# HTTP API Configuration
CODEBOT_API_KEYS=secret-key-1,secret-key-2
CODEBOT_MAX_WORKERS=2
CODEBOT_MAX_QUEUE_SIZE=100
CODEBOT_TASK_RETENTION=86400
```

Codebot automatically loads `.env` files on startup.

## Command-Line Options

### codebot run

```bash
codebot run [OPTIONS]
```

**Options:**

- `--task-prompt TEXT` - Task prompt as JSON or YAML string
- `--task-prompt-file PATH` - Path to task prompt file
- `--work-dir PATH` - Base directory for workspaces (default: `./codebot_workspace`)
- `--github-token TEXT` - GitHub token (overrides env var)
- `--verbose` - Enable verbose output

### codebot serve

```bash
codebot serve [OPTIONS]
```

**Options:**

- `--port INTEGER` - Server port (default: 5000)
- `--work-dir PATH` - Base directory for workspaces
- `--github-token TEXT` - GitHub token (overrides env var)
- `--webhook-secret TEXT` - Webhook secret (overrides env var)
- `--api-key TEXT` - API key (overrides env var)
- `--workers INTEGER` - Number of worker threads (default: 1)
- `--debug` - Enable debug mode with auto-reload

## GitHub Token Scopes

### For CLI Usage

Minimum required:
- Create pull requests
- Push to repositories
- Read repository contents

### For Webhook Server

Additional requirements:
- Read PR details and comments
- Post comments on PRs
- Update PR descriptions

### Creating a Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic or fine-grained)
3. Select required scopes
4. Copy token and store securely

**Security Tips:**
- Never commit tokens to code
- Use environment variables or `.env` files
- Rotate tokens periodically
- Use fine-grained tokens when possible
- Limit token scope to specific repositories

## Workspace Configuration

### Work Directory Structure

```
codebot_workspace/
├── task_abc1234/          # Task workspace
│   └── repo/              # Cloned repository
├── task_PROJ-123_def5678/ # Task with ticket ID
│   └── repo/
└── ...
```

### Custom Work Directory

```bash
# CLI
codebot run --work-dir /tmp/codebot_tasks --task-prompt-file task.yaml

# Server
codebot serve --work-dir /var/codebot/workspaces
```

## Server Configuration

### Production Recommendations

```bash
# Use production WSGI server (not Flask dev server)
export CODEBOT_MAX_WORKERS=4
export CODEBOT_MAX_QUEUE_SIZE=200

# Don't use --debug in production
codebot serve --port 8000 --workers 4
```

### Development Setup

```bash
# Enable auto-reload and detailed errors
codebot serve --port 5000 --debug
```

## Security Best Practices

1. **Protect API Keys**
   - Use strong, random keys
   - Store in environment variables
   - Never log or expose in responses

2. **Secure Webhook Secret**
   - Use cryptographically random string
   - Match exactly in GitHub webhook config
   - Rotate periodically

3. **GitHub Token Security**
   - Use fine-grained tokens when possible
   - Limit to specific repositories
   - Set expiration dates
   - Revoke if compromised

4. **Network Security**
   - Use HTTPS in production
   - Configure firewall rules
   - Use reverse proxy (nginx, caddy)
   - Enable rate limiting

5. **Workspace Isolation**
   - Use dedicated work directory
   - Clean up old workspaces
   - Set appropriate file permissions

## Troubleshooting

### Token validation failed

- Check token hasn't expired
- Verify token has required scopes
- Test token with GitHub API:
  ```bash
  curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
  ```

### Webhook signature verification failed

- Ensure `GITHUB_WEBHOOK_SECRET` matches GitHub config
- Check webhook is using `application/json` content type
- Verify secret has no extra whitespace

### API key not working

- Check `CODEBOT_API_KEYS` is set
- Verify key matches exactly (no extra spaces)
- Ensure server was restarted after changing keys

### Worker threads not starting

- Check `CODEBOT_MAX_WORKERS` value
- Verify sufficient system resources
- Check server logs for errors

## Next Steps

- [CLI Usage Guide](cli-usage.md) - Run tasks from command line
- [HTTP API Guide](http-api.md) - Programmatic task submission
- [Webhooks Guide](webhooks.md) - PR review automation

---

[← Back to Documentation](index.md)
