# workday-prep

Generate a prioritized morning workday report with GitHub PRs and Jira issues grouped by priority. Outputs a Bootstrap HTML report at `/tmp/workday.html`.

## Prerequisites

### GitHub CLI (`gh`)

Install and authenticate:

```bash
brew install gh
gh auth login
```

Verify with `gh auth status`.

### Atlassian CLI (`acli`)

Install from https://developer.atlassian.com/cloud/acli/guides/introduction/.

```bash
brew tap atlassian/acli
brew install acli
```

### Jira credentials

The Jira scripts need three values. You can provide them in **either** of two ways:

#### Option A: Environment variables

Set these in your shell profile (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
export JIRA_URL="https://your-org.atlassian.net"
export JIRA_USERNAME="you@example.com"
export JIRA_API_TOKEN="your-api-token"
```

`JIRA_USERNAME` can also be provided as `EMAIL`.

#### Option B: Claude MCP config (automatic)

If you have the `rh-jira` MCP server configured in `~/.claude.json`, the script reads credentials from there automatically — no extra env vars needed:

```json
{
  "mcpServers": {
    "rh-jira": {
      "env": {
        "JIRA_URL": "https://your-org.atlassian.net",
        "JIRA_USERNAME": "you@example.com",
        "JIRA_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

### Generating a Jira API token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Give it a label (e.g. "claude workday-prep") and copy the token
4. Store it in one of the locations above

## Usage

In Claude Code:

```
/workday-prep
```

This fetches your GitHub PRs and Jira issues, cross-references them, generates an HTML report, and opens it in your browser.
