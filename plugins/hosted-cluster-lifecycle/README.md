# Hosted Cluster Lifecycle Plugin

Guide HyperShift HostedCluster setup and diagnose why an existing cluster has not reached its requested readiness target, on AWS or self-managed Azure.

## Usage

Use `/hosted-cluster-lifecycle` or ask why a HostedCluster is not ready, which startup stage it reached, or what to inspect next. The skill loads only the provider and lifecycle references needed for the current gate.

- Routes intake, setup, and P0–P9 startup diagnosis across the control-plane, worker, and guest-convergence workstreams.
- Adds focused AWS, self-managed Azure, evidence-capture, observation, and teardown references.
- Distinguishes historical first success from current readiness, and reports unknown evidence as unknown instead of inferring failure.
- Covers the normal AWS teardown path and the checks that verify Kubernetes and cloud-resource cleanup.

## References

The merged HyperShift documentation carries the deeper visual material this skill links to:

- [Hosted cluster startup roadmap](https://hypershift.pages.dev/reference/cluster-startup-roadmap/)
- [AWS hosted cluster teardown roadmap](https://hypershift.pages.dev/reference/cluster-teardown-roadmap/)

## Requirements

- `oc` and a kubeconfig for the target management cluster (and a guest kubeconfig for guest-convergence checks)
- `jq` for the example object queries
- Optional: a HyperShift source checkout containing the timeline collectors, used only when the current task calls for continuous capture
