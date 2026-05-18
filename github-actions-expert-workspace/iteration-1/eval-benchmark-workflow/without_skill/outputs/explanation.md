# Design Decisions for Go Benchmark Workflow

## Trigger Configuration

- **`pull_request` event on `main` and `release-*` branches**: Covers the primary development branch and release branches where performance regressions matter most.
- **`paths` filter on `**.go`, `go.mod`, `go.sum`, `Makefile`**: Avoids running expensive benchmarks when only docs, CI configs, or non-Go files change. The Makefile is included because changes to build/bench targets could affect benchmark behavior.
- **`draft == false` guard**: Skips benchmarks on draft PRs to conserve self-hosted runner capacity.

## Runner Selection

- **`runs-on: [self-hosted, linux, x64]`**: Uses self-hosted runners as requested. The `linux` and `x64` labels are standard qualifiers. Self-hosted runners provide more consistent benchmark results than GitHub-hosted runners because the hardware does not vary between runs.

## Concurrency Control

- **`concurrency` with `cancel-in-progress: true`**: Grouped by PR number so that pushing a new commit cancels any in-progress benchmark run for the same PR. This prevents wasted runner time on stale commits.

## Benchmark Comparison Strategy

- **Run PR benchmarks first, then base benchmarks**: The workflow checks out the PR commit, runs `make bench`, then checks out the base branch commit and runs `make bench` again. This provides a direct before/after comparison on the same runner and hardware.
- **`benchstat` for comparison**: The standard Go tool for statistically comparing benchmark results. It highlights regressions and improvements with significance indicators.

## PR Comment Approach

- **`actions/github-script` for comment management**: Finds and updates an existing benchmark comment rather than creating duplicates on each push. This keeps the PR conversation clean.
- **Collapsible sections**: Uses `<details>` tags so the benchmark output does not dominate the PR conversation. The benchstat comparison summary is the primary view; raw output is available on expand.

## Go Toolchain

- **`go-version-file: go.mod`**: Reads the Go version from the repository's `go.mod` to ensure benchmarks run against the same Go version the project targets.
- **`cache: true`**: Caches Go modules and build artifacts to speed up subsequent runs.

## Permissions

- **Minimal permissions**: Only `contents: read` (for checkout) and `pull-requests: write` (for posting comments) are requested, following the principle of least privilege.
