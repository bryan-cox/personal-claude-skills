# Actions Runner Controller (ARC) Reference

ARC deploys GitHub Actions self-hosted runners as Kubernetes pods. HyperShift uses ARC to run all GitHub Actions workflows on a shared cluster. The runner nodes are **ARM (aarch64)** architecture, not x86.

## Architecture

ARC consists of:
- **Controller** — watches for workflow jobs and scales runner pods
- **Runner Scale Set** — defines a pool of runners with a specific label (e.g., `arc-runner-set`)
- **Listener** — receives webhook events from GitHub and informs the controller

Runner pods are ephemeral by default — they run a single job and are destroyed. This prevents state leakage between runs.

## Runner Set Configuration

Key settings to tune:

```yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerSet
metadata:
  name: arc-runner-set
spec:
  ephemeral: true
  maxRunners: 10
  minRunners: 1
  template:
    spec:
      containers:
        - name: runner
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
            limits:
              cpu: "4"
              memory: "8Gi"
```

### Scaling

- `minRunners` — keep at least 1 warm runner for fast job pickup
- `maxRunners` — cap total runners to prevent resource exhaustion
- Scale-to-zero is possible but adds cold-start latency

### Runner Images

Use a custom runner image with pre-installed tools (Go, make, golangci-lint) to avoid downloading them on every run. The HyperShift lint workflow demonstrates this — it checks for pre-built tools at `/opt/lint-tools/` before building from source.

Since runners are ARM, all pre-built binaries and container images must be ARM-compatible (linux/arm64). When installing tools at runtime (e.g., `go install`, downloading binaries), ensure the ARM variant is selected. Many GitHub Actions that download pre-built binaries default to x86 — verify they support ARM or provide a fallback.

### Networking

Runner pods need egress access to:
- `github.com` and `api.github.com` (Actions API, code checkout)
- Container registries (quay.io, ghcr.io, docker.io)
- Go module proxy (proxy.golang.org)
- Any internal services the build needs

Lock down egress with NetworkPolicies. Deny all by default, allow specific destinations.

### Secrets

Options for providing secrets to runner pods:
1. **GitHub Actions secrets** — encrypted at rest, injected as environment variables by the runner. Preferred for CI secrets.
2. **Kubernetes secrets** — mounted as volumes or env vars in the runner pod spec. Use for cluster-level credentials that shouldn't be in GitHub.
3. **OIDC** — for cloud provider authentication. The runner requests a short-lived token from GitHub's OIDC provider, exchanges it with the cloud provider. No stored credentials.

### Monitoring

Watch for:
- Runner pod crash loops (OOM, image pull failures)
- Queue depth exceeding max runners (jobs waiting too long)
- Runner registration failures (GitHub API rate limiting)
- Disk pressure on runner pods (large checkouts, build artifacts)

Use `kubectl get runners` and `kubectl describe runnerreplicaset` to inspect ARC state.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Jobs pending forever | Runner label mismatch or no runners available | Check `runs-on` matches runner set label; check runner pod status |
| Jobs fail immediately | Runner pod OOM or crash | Increase resource limits; check runner image |
| Intermittent failures | State leakage between runs | Ensure `ephemeral: true`; check for shared volumes |
| Slow job pickup | Min runners at 0, cold start | Set `minRunners: 1` for warm pool |
| Permission denied in job | RBAC or filesystem permissions | Check runner pod service account; check workspace permissions |
| "exec format error" or binary won't run | x86 binary on ARM runner | Use ARM (linux/arm64) binaries; check action supports ARM |
