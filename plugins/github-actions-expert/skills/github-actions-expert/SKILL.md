---
name: github-actions-expert
description: "Expert guidance for writing, reviewing, debugging, and securing GitHub Actions workflows. Use this skill whenever working with .github/workflows/ YAML files, GitHub Actions configuration, CI pipeline design, self-hosted runner setup (ARC/actions-runner-controller), reusable workflows, composite actions, or GitHub Actions security hardening. Also use when the user mentions GitHub Actions, GHA, workflow files, action pinning, runner configuration, or asks about CI that runs on GitHub — even if they don't say 'GitHub Actions' explicitly. This skill understands Prow-based merge queues (not GitHub merge queue) and self-hosted runners on Kubernetes clusters, which is the pattern used in OpenShift and HyperShift projects."
---

# GitHub Actions Expert

You are an expert in GitHub Actions with deep knowledge of workflow authoring, security hardening, self-hosted runner infrastructure, and how GitHub Actions coexists with Prow in OpenShift/HyperShift projects.

## Context: HyperShift CI Architecture

HyperShift uses a hybrid CI system:

- **GitHub Actions** handles pre-merge checks: unit tests, linting, verification, codespell, envtest, docs preview. These run on every PR and push to protected branches.
- **Prow** (operated by OpenShift CI) is the merge queue manager. Prow runs the heavyweight E2E tests, manages the merge queue via Tide, and handles `/lgtm`, `/approve`, and other chatops commands. Prow is **not** GitHub merge queue — it's a separate system.
- **All GHA runners are self-hosted** via Actions Runner Controller (ARC) on a Kubernetes cluster, using the runner set label `arc-runner-set`. The runners run on **ARM (aarch64) nodes**, not x86. This matters when selecting actions, container images, or installing tools — always use ARM-compatible variants.

The boundary is clear: GitHub Actions handles fast, lightweight checks that give quick PR feedback. Prow handles integration/E2E testing and merge gating. Never design GHA workflows that duplicate Prow's responsibilities or attempt to manage the merge queue.

## Workflow Authoring

### Structure and Syntax

When writing workflows, follow these patterns:

**Triggers** — Be explicit about which branches workflows apply to. In HyperShift, workflows target `main` and active release branches:

```yaml
on:
  push:
    branches: [main, release-4.22]
  pull_request:
    branches: [main, release-4.22]
```

Use `workflow_dispatch: {}` on workflows that should support manual triggering.

**Jobs** — Each job should have a descriptive `name`, a `timeout-minutes` (always set one — never leave jobs unbounded), and use the correct runner label:

```yaml
jobs:
  test:
    name: Unit Tests
    runs-on: arc-runner-set
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v6
```

**Skip logic** — For PRs that only touch non-essential paths (docs, contrib/), use a changes-detection step early to skip expensive work:

```yaml
- name: Check for relevant changes
  id: changes
  run: |
    FILES=$(git diff --name-only origin/${{ github.base_ref }}...HEAD)
    if echo "$FILES" | grep -qvE '^(contrib|\.github)/'; then
      echo "run=true" >> "$GITHUB_OUTPUT"
    else
      echo "run=false" >> "$GITHUB_OUTPUT"
    fi
- if: steps.changes.outputs.run == 'true'
  run: make test
```

**Outputs** — Use `$GITHUB_OUTPUT` (not the deprecated `set-output` command). Use `$GITHUB_ENV` for environment variables needed by subsequent steps.

### Reusable Workflows

Use reusable workflows (`workflow_call` trigger) to share common job definitions across workflows. Keep them in `.github/workflows/` with clear names.

```yaml
# .github/workflows/reusable-go-test.yaml
on:
  workflow_call:
    inputs:
      go-version:
        type: string
        default: '1.22'
      make-target:
        required: true
        type: string

jobs:
  test:
    runs-on: arc-runner-set
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v6
      - run: make ${{ inputs.make-target }}
```

Call it from other workflows:

```yaml
jobs:
  unit-tests:
    uses: ./.github/workflows/reusable-go-test.yaml
    with:
      make-target: test
```

### Composite Actions

For reusable step sequences (not full jobs), use composite actions in `.github/actions/`:

```yaml
# .github/actions/setup-go-env/action.yaml
name: Setup Go Environment
description: Sets up Go with caching
inputs:
  go-version:
    default: '1.22'
runs:
  using: composite
  steps:
    - uses: actions/setup-go@v5
      with:
        go-version: ${{ inputs.go-version }}
    - uses: actions/cache@v4
      with:
        path: ~/go/pkg/mod
        key: ${{ runner.os }}-go-${{ hashFiles('go.sum') }}
```

## Security

### Action Pinning

Pin third-party actions to a full commit SHA, not a tag. Tags are mutable — an attacker who compromises an action repo can move a tag to point to malicious code:

```yaml
# Bad — tag can be moved
- uses: actions/checkout@v6

# Good — immutable SHA
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
```

For actions maintained by GitHub (`actions/*`), version tags are acceptable because GitHub signs and protects them. For everything else, pin to SHA and add a comment with the version for readability.

### Secrets Management

- Never echo, log, or interpolate secrets into shell commands where they could appear in logs.
- Use `secrets: inherit` in reusable workflow calls only when the called workflow actually needs secrets. Prefer passing specific secrets explicitly.
- Use environment-level secrets for deployment workflows, not repository-level, to limit blast radius.
- For OIDC-based authentication (e.g., cloud provider access), use `permissions: id-token: write` and avoid storing long-lived credentials as secrets.

### Permissions (Least Privilege)

Every workflow should declare the minimum `permissions` it needs. Default permissions are overly broad:

```yaml
permissions:
  contents: read

jobs:
  test:
    runs-on: arc-runner-set
    steps:
      - uses: actions/checkout@v6
      - run: make test
```

Common permission scopes:
- `contents: read` — checkout code (most workflows need only this)
- `pull-requests: write` — post PR comments (codecov, coverage reports)
- `checks: write` — create check runs
- `id-token: write` — OIDC token for cloud auth
- `packages: write` — push container images to GHCR

If a workflow doesn't declare `permissions`, it inherits the repository default (often `write-all`). Always be explicit.

### Self-Hosted Runner Security

Since HyperShift uses self-hosted runners on a shared cluster:

- **Ephemeral runners** — ARC runners should be configured as ephemeral (one job per runner pod). This prevents state leakage between workflow runs. The runner pod is created for a job and destroyed after.
- **Network policies** — Runners should have network policies restricting egress to only what's needed (GitHub API, package registries, internal services).
- **No secrets in runner images** — Runner container images should contain only the runtime. Secrets come from GitHub Actions secrets or Kubernetes secrets mounted at job time.
- **Resource limits** — Set CPU/memory requests and limits on runner pods. A runaway build shouldn't starve the cluster.
- **RBAC** — Runner pods should have minimal Kubernetes RBAC. They don't need cluster-admin or access to other namespaces.
- **Untrusted input** — Treat PR contents as untrusted. Never pass PR title, body, or branch names directly into shell commands without quoting. Use environment variables instead of inline expressions in `run:` blocks:

```yaml
# Bad — injection via PR title
- run: echo "PR: ${{ github.event.pull_request.title }}"

# Good — environment variable is not interpreted by the shell
- env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: echo "PR: $PR_TITLE"
```

### Supply Chain Considerations

- Audit third-party actions before adopting. Check the action's source, whether it's actively maintained, and what permissions it requests.
- Use Dependabot or Renovate to keep actions updated. Pin to SHA but automate the update process.
- For sensitive workflows (release, deploy), consider vendoring critical actions into the repository.

## Prow + GitHub Actions Coexistence

### Separation of Concerns

| Responsibility | System |
|---|---|
| Unit tests, linting, formatting, static analysis | GitHub Actions |
| E2E tests, integration tests | Prow |
| Merge queue management (Tide) | Prow |
| Chatops (`/lgtm`, `/approve`, `/retest`) | Prow |
| PR labeling, lifecycle management | Prow |
| Release/image builds | Prow (CI Operator) |

### Status Checks

Both Prow and GitHub Actions report status checks on PRs. Branch protection rules should require both:

- GHA checks (e.g., `Unit Tests`, `Lint`, `Verify`) — these are GitHub status checks created by GHA.
- Prow checks (e.g., `ci/prow/e2e-*`) — these are GitHub status checks created by Prow.

Prow's Tide component merges PRs when all required checks pass and the PR has the necessary labels. GHA checks are visible to Tide as regular GitHub status checks.

### What NOT to do in GitHub Actions

- Don't implement a merge queue or merge bot. Prow's Tide handles this.
- Don't duplicate Prow's E2E test execution. E2E tests require specific cloud credentials, test infrastructure, and cluster lifecycle management that Prow's CI Operator provides.
- Don't manage PR labels or approval workflows — Prow plugins handle this.
- Don't trigger on `pull_request_review` to implement approval gates — Prow's `/lgtm` and `/approve` commands are the source of truth.

### What TO do in GitHub Actions

- Fast feedback: unit tests, lint, verify, codespell, formatting checks.
- Lightweight validation: gitlint, doc previews, envtest-based controller tests.
- Container syncing or utility operations that don't need Prow's test infrastructure.
- Code coverage reporting (e.g., Codecov integration).

## Debugging Workflows

### Common Issues

**"This check is required but never reported"** — The job name in the workflow must exactly match the required status check name configured in branch protection. Check both the workflow `name` field and the job `name` field.

**Workflow not triggering** — Check the `on:` trigger configuration. Common causes:
- Branch name doesn't match the pattern
- Path filters exclude the changed files
- `pull_request` vs `pull_request_target` — use `pull_request` for PR checks; `pull_request_target` runs in the context of the base branch and has different security implications
- Workflow file itself was just added — the workflow must exist on the target branch to trigger on PRs to that branch

**Self-hosted runner not picking up jobs** — Check:
- The `runs-on` label matches the ARC runner set name
- Runner pods are healthy (`kubectl get pods -n <runner-namespace>`)
- Runner registration with GitHub is active
- Queue depth isn't exceeding the max runner count

**Permissions errors** — If a step fails with 403 or permission denied, add the specific permission scope to the workflow's `permissions` block. Check `GITHUB_TOKEN` permissions in the workflow run logs.

### Workflow Run Analysis

Use `gh run list`, `gh run view`, and `gh run view --log` to inspect workflow runs from the CLI. For failed runs:

```bash
gh run view <run-id> --log-failed
```

## Best Practices Checklist

When writing or reviewing a workflow:

- [ ] `timeout-minutes` set on every job
- [ ] `permissions` explicitly declared (not relying on defaults)
- [ ] Third-party actions pinned to SHA (or version tag for `actions/*`)
- [ ] `runs-on` uses the correct self-hosted runner label
- [ ] Secrets are not interpolated in `run:` blocks (use `env:` instead)
- [ ] PR-triggered workflows don't have write permissions they don't need
- [ ] Skip logic for irrelevant file changes where appropriate
- [ ] Job names match required status check names in branch protection
- [ ] No duplication of Prow's responsibilities
- [ ] `fetch-depth: 0` used when git history is needed (diff, blame, log)

## Reference

For ARC-specific configuration, runner set tuning, or advanced workflow patterns, read `references/arc-runners.md`.
