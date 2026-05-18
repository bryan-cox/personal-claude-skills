# Jira Pointer -- Dry Run Proposal

**Epic:** [CNTRLPLANE-1350](https://redhat.atlassian.net/browse/CNTRLPLANE-1350) -- Implement KMSv2 in self-managed Azure
**Status:** In Progress
**Child Issues Found:** 6
**Unpointed Issues:** 6
**Mode:** `--dry-run` (no points will be written)

---

## Flagged Issues

No issues were assessed at 8 or 13 points. No splitting recommendations.

---

## Proposal Table

| Issue Key | Type | Summary | Status | Proposed Points | Rationale |
|-----------|------|---------|--------|-----------------|-----------|
| CNTRLPLANE-3358 | Task | Sync openshift/azure-kubernetes-kms fork with upstream Azure/kubernetes-kms | Code Review | **3** | Cherry-picking upstream commits, bumping deps for CVE fixes, updating Go version, and adjusting otel API usage. Straightforward but time-consuming fork-sync work touching multiple files (go.mod, Dockerfile, source files for otel changes). Low risk since it follows upstream, but requires care with dependency compatibility. |
| CNTRLPLANE-3070 | Story | Support KMS on self-managed Azure without affecting ARO HCP | In Progress | **5** | Requires investigation to identify all code paths needing modification, careful scoping to avoid regressing ARO HCP / managed Azure KMS behavior, and cross-path testing. Involves collaboration with KMS and platform teams. Multiple acceptance criteria spanning code changes, testing, and documentation of config differences. Moderate risk -- changes to shared encryption code paths could affect the managed path. |
| CNTRLPLANE-3204 | Story | Add workload identity support to the Azure KMS plugin provider | To Do | **5** | Requires investigation and design -- must evaluate whether to update Azure SDK (azidentity) vs. manually plumbing workload identity tokens/OIDC. Touches authentication code in the KMS plugin provider, needs unit tests for the new auth path, and must not regress existing service principal authentication. Moderate complexity and risk. |
| CNTRLPLANE-1357 | Story | CI implementation: Implement KMSv2 in self-managed Azure | To Do | **3** | Configuring the periodic CI job to include TestCreateClusterCustomConfig, setting up Azure KMS credentials and encryption key parameters in the job config. Work is fairly well-defined (CI YAML configuration, credential wiring to vault) but time-consuming to validate end-to-end. Minor risks around credential and secret management in CI. |
| CNTRLPLANE-1356 | Story | e2e testing automation: Implement KMSv2 in self-managed Azure | To Do | **3** | Similar to CNTRLPLANE-1357 but for presubmit jobs. Configuring the presubmit CI job, wiring credentials, and ensuring KMSv2 validation runs before merge. Straightforward CI config work with known patterns, but time-consuming to get the credential plumbing and job configuration right. |
| CNTRLPLANE-1355 | Story | pre-merge testing: Implement KMSv2 in self-managed Azure | Closed (Done) | **1** | Already closed as "No need pre-merge test" per comments. Was resolved without actual work being done -- trivially closed. Minimal effort, no code changes. |

---

## Summary

```
Proposed points for 6 issues:

- CNTRLPLANE-3358:  3 pts (Task  -- Sync openshift/azure-kubernetes-kms fork with upstream)
- CNTRLPLANE-3070:  5 pts (Story -- Support KMS on self-managed Azure without affecting ARO HCP)
- CNTRLPLANE-3204:  5 pts (Story -- Add workload identity support to the Azure KMS plugin provider)
- CNTRLPLANE-1357:  3 pts (Story -- CI implementation: Implement KMSv2 in self-managed Azure)
- CNTRLPLANE-1356:  3 pts (Story -- e2e testing automation: Implement KMSv2 in self-managed Azure)
- CNTRLPLANE-1355:  1 pt  (Story -- pre-merge testing: Implement KMSv2 in self-managed Azure) [CLOSED]

Total proposed points: 20
Flagged for splitting: 0
Already pointed (skipped): 0
```

---

**DRY RUN -- No points were written to Jira.**
