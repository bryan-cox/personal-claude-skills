# Benchmark Workflow Design Decisions

## Trigger strategy

The workflow triggers on `pull_request` only (not `push`) because benchmark comparisons are inherently PR-scoped -- they compare a PR branch against its base. It targets `main` and `release-4.22`, matching the branch pattern used by existing hypershift workflows. Path filters restrict triggering to Go source files, `go.mod`, `go.sum`, `Makefile`, and the vendor directory, so documentation-only or CI config changes do not waste runner time.

A secondary `changes` step performs a git-diff check against `.go`, `go.mod`, `go.sum`, and `Makefile` specifically. This catches the edge case where the path filter allowed the run (e.g., a vendor change) but no actual Go source was modified.

`workflow_dispatch` is included to allow manual runs for debugging or ad-hoc benchmarking.

## Runner and timeout

The workflow uses `arc-runner-set`, the self-hosted ARC runner label used by all hypershift GHA workflows. Timeout is set to 45 minutes -- longer than the 30-minute unit test timeout because benchmarks run twice (base and PR) and benchmark suites tend to take longer than unit tests.

## Comparative benchmarks with benchstat

Rather than just reporting raw numbers, the workflow runs benchmarks on both the PR head and the base branch, then uses `benchstat` to produce a statistical comparison. This makes it easy for reviewers to see whether a PR introduces regressions. `benchstat` is installed via `go install` so it always uses the latest version without adding a third-party action dependency.

## PR comment approach

Results are posted as a PR comment using the `gh` CLI and the GitHub API, avoiding the need for a third-party "comment" action. A comment marker (`<!-- benchmark-results -->`) enables idempotent updates -- re-running the workflow updates the existing comment instead of creating duplicates. All user-controlled input (PR number, results) flows through environment variables rather than inline shell interpolation, following the security guidance for self-hosted runners.

## Permissions

The workflow declares explicit least-privilege permissions: `contents: read` for checkout and `pull-requests: write` for posting the PR comment. No other scopes are granted.

## Alignment with HyperShift CI architecture

This workflow stays within the GitHub Actions boundary defined by the hybrid CI model: it provides fast, lightweight feedback on PRs. It does not duplicate Prow responsibilities (no E2E tests, no merge gating, no label management). Benchmarks are a natural fit for GHA since they give quick signal about performance changes without requiring the heavyweight test infrastructure that Prow manages.
