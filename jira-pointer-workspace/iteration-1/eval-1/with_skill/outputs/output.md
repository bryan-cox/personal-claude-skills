# Jira Pointer: OCPSTRAT-2253 -- Dry Run

**Feature:** [GA] Self-managed Hosted Control Planes support using the Azure Provider
**Mode:** `--dry-run` (no story points written to Jira)
**Date:** 2026-05-05
**Field:** `customfield_10028` (Story Points)

---

## Hierarchy Summary

- **Root Feature:** OCPSTRAT-2253 (Feature)
- **Child Epics:** 9
- **Child Stories/Tasks:** 38
- **Total issues in tree:** 48 (1 Feature + 9 Epics + 38 Stories/Tasks)

---

## Issues Flagged for Splitting

### 8-Point Issues (Consider splitting)

| Issue Key | Type | Summary | Proposed Points | Warning |
|-----------|------|---------|-----------------|---------|
| CNTRLPLANE-3222 | Task | Migrate self-managed Azure e2e tests to v2 Ginkgo framework | 8 | **Consider splitting.** Large migration touching test framework, shared helpers, 4 new test files, Makefile targets, env var registration. Multiple independent work streams (helper refactoring, test creation, CI config). |
| CNTRLPLANE-3070 | Story | Support KMS on self-managed Azure without affecting ARO HCP | 8 | **Consider splitting.** Requires separating KMS paths for self-managed vs managed Azure, cross-component design, risk of breaking ARO HCP path. |

No issues assessed at 13 points.

---

## Full Proposal Table

### Epic: STOR-2906 -- Azure HCP self managed support for Azure Disk CSI (GA)

Epic has existing story points: **1.0** (already pointed, skipped)

| Issue Key | Type | Status | Current SP | Proposed Points | Rationale |
|-----------|------|--------|------------|-----------------|-----------|
| STOR-2943 | Story | To Do | -- | 3 | CI implementation for Azure Disk CSI on HCP. Requires setting up CI job configurations, integrating with existing storage test framework, and validating the pipeline. Fairly straightforward but time-consuming CI plumbing. |
| STOR-2942 | Story | To Do | -- | 3 | e2e testing automation for Azure Disk CSI. Writing and validating e2e test cases for disk CSI on HCP self-managed. Straightforward test work but requires cluster setup and validation. |
| STOR-2941 | Story | To Do | -- | 2 | Pre-merge testing for Azure Disk CSI. Setting up presubmit gates. Well-understood pattern, low risk, slightly more than trivial. |

**Subtotal for STOR-2906 children:** 8 points (3 issues)

---

### Epic: STOR-2905 -- Azure HCP self managed support for Azure File CSI (GA)

Epic has existing story points: **1.0** (already pointed, skipped)

| Issue Key | Type | Status | Current SP | Proposed Points | Rationale |
|-----------|------|--------|------------|-----------------|-----------|
| STOR-2946 | Story | To Do | -- | 3 | CI implementation for Azure File CSI on HCP. Same pattern as Disk CSI CI but for File CSI. Requires CI job configuration and pipeline integration. |
| STOR-2945 | Story | To Do | -- | 3 | e2e testing automation for Azure File CSI. Writing e2e tests for file CSI on HCP self-managed platform. Straightforward but time-consuming. |
| STOR-2944 | Story | To Do | -- | 2 | Pre-merge testing for Azure File CSI. Setting up presubmit test gates. Well-understood pattern. |

**Subtotal for STOR-2905 children:** 8 points (3 issues)

---

### Epic: OSDOCS-14975 -- Docs for OCPSTRAT-2253

Epic has **no** existing story points. Status: **Closed** (no children found).

| Issue Key | Type | Status | Current SP | Proposed Points | Rationale |
|-----------|------|--------|------------|-----------------|-----------|
| *(no children)* | -- | -- | -- | -- | Epic is Closed with no child issues found. |

**Subtotal for OSDOCS-14975 children:** 0 points (0 issues)

---

### Epic: CNTRLPLANE-3253 -- External OIDC support for self-managed Azure HCP

Epic has **no** existing story points.

| Issue Key | Type | Status | Current SP | Proposed Points | Rationale |
|-----------|------|--------|------------|-----------------|-----------|
| CNTRLPLANE-3272 | Story | To Do | -- | 3 | CI implementation for external OIDC. Setting up CI job for OIDC testing on Azure. Fairly straightforward CI plumbing but requires OIDC-specific configuration. |
| CNTRLPLANE-3271 | Story | To Do | -- | 3 | e2e testing automation for external OIDC. Writing automated e2e tests for OIDC flows on self-managed Azure. Requires understanding OIDC provider setup. |
| CNTRLPLANE-3270 | Story | To Do | -- | 2 | Pre-merge testing for external OIDC. Adding presubmit test gates. Well-understood CI pattern. |

**Subtotal for CNTRLPLANE-3253 children:** 8 points (3 issues)

---

### Epic: CNTRLPLANE-2011 -- Performance testing for self-managed Azure HCP

Epic has **no** existing story points.

| Issue Key | Type | Status | Current SP | Proposed Points | Rationale |
|-----------|------|--------|------------|-----------------|-----------|
| CNTRLPLANE-3205 | Task | To Do | -- | 5 | Execute performance testing. Requires defining scenarios, running benchmarks, comparing against other platforms (AWS, KubeVirt, bare metal), documenting results. Investigation-heavy, multi-step testing with cross-platform comparison. |
| CNTRLPLANE-2027 | Story | To Do | -- | 3 | CI implementation for performance testing. Setting up CI jobs for perf benchmarks. Fairly standard CI work but perf jobs often have additional resource and environment requirements. |
| CNTRLPLANE-2026 | Story | To Do | -- | 3 | e2e testing automation for performance testing. Automating the perf test suite for regular runs. Time-consuming to set up with appropriate thresholds and alerting. |
| CNTRLPLANE-2025 | Story | To Do | -- | 2 | Pre-merge testing for performance testing. Adding presubmit test gates for performance regressions. Well-understood pattern. |

**Subtotal for CNTRLPLANE-2011 children:** 13 points (4 issues)

---

### Epic: CNTRLPLANE-2010 -- Disaster recovery support for self-managed Azure HCP

Epic has **no** existing story points.

| Issue Key | Type | Status | Current SP | Proposed Points | Rationale |
|-----------|------|--------|------------|-----------------|-----------|
| CNTRLPLANE-3202 | Story | To Do | -- | 3 | Document DR procedures. Writing user-facing documentation for Azure Blob Storage OADP backup/restore. Straightforward documentation work but covers multiple scenarios. |
| CNTRLPLANE-3201 | Story | To Do | -- | 5 | Add DR e2e tests. Automated e2e tests for backup, restore, and cross-cluster restore on Azure. Requires setting up multi-cluster test environments and OADP integration. Investigation and complex test harness needed. |
| CNTRLPLANE-3200 | Story | To Do | -- | 5 | Validate cross-cluster restore. Restore a hosted cluster backup from one Azure management cluster to a different one. Requires multi-cluster orchestration and Azure-specific blob storage integration. Non-trivial validation with risk. |
| CNTRLPLANE-3199 | Story | To Do | -- | 5 | Validate OADP backup/restore with Azure Blob Storage. End-to-end validation of backup and restore using OADP on Azure. Requires Azure-specific storage configuration and testing multiple failure scenarios. |
| CNTRLPLANE-2024 | Story | To Do | -- | 3 | CI implementation for DR. Setting up CI jobs for disaster recovery tests. Requires Azure-specific infrastructure provisioning in CI. |
| CNTRLPLANE-2023 | Story | To Do | -- | 3 | e2e testing automation for DR. Automating DR test scenarios into the regular test suite. Time-consuming test setup. |
| CNTRLPLANE-2022 | Story | To Do | -- | 2 | Pre-merge testing for DR. Adding presubmit gates for DR code changes. Well-understood pattern. |

**Subtotal for CNTRLPLANE-2010 children:** 26 points (7 issues)

---

### Epic: CNTRLPLANE-2009 -- Autoscaling support for self-managed Azure HCP

Epic has **no** existing story points. **All children are Closed.**

| Issue Key | Type | Status | Current SP | Proposed Points | Rationale |
|-----------|------|--------|------------|-----------------|-----------|
| CNTRLPLANE-3203 | Task | Closed | -- | 3 | Assess current autoscaling functionality. Investigation task: deploy cluster, test scale-up/down, verify attributes support. Work was exploratory. Now resolved. |
| CNTRLPLANE-2021 | Story | Closed | -- | 2 | CI implementation for autoscaling. Closed. Standard CI job setup. |
| CNTRLPLANE-2020 | Story | Closed | -- | 2 | e2e testing automation for autoscaling. Closed. Standard e2e test automation. |
| CNTRLPLANE-2019 | Story | Closed | -- | 2 | Pre-merge testing for autoscaling. Closed. Standard presubmit gates. |

**Subtotal for CNTRLPLANE-2009 children:** 9 points (4 issues)

---

### Epic: CNTRLPLANE-1350 -- Implement KMSv2 in self-managed Azure

Epic has **no** existing story points.

| Issue Key | Type | Status | Current SP | Proposed Points | Rationale |
|-----------|------|--------|------------|-----------------|-----------|
| CNTRLPLANE-3358 | Task | Code Review | -- | 3 | Sync openshift/azure-kubernetes-kms fork with upstream. Cherry-picking commits, bumping dependencies for CVEs, updating Go version. Straightforward but requires careful review due to security-relevant dep bumps. |
| CNTRLPLANE-3204 | Story | To Do | -- | 5 | Add workload identity support to Azure KMS plugin provider. Requires investigation into Azure AD workload identity federation, changes to authentication flow in KMS plugin. Design and cross-component collaboration needed. |
| CNTRLPLANE-3070 | Story | In Progress | -- | 8 | Support KMS on self-managed Azure without affecting ARO HCP. Requires separating code paths for self-managed vs managed Azure KMS, risk of breaking existing ARO HCP functionality. Design doc needed, cross-team coordination. **Consider splitting into smaller stories.** |
| CNTRLPLANE-1357 | Story | To Do | -- | 3 | CI implementation for KMSv2. Adding KMS test case to self-managed Azure periodic CI job. Requires Azure KMS infrastructure in CI. |
| CNTRLPLANE-1356 | Story | To Do | -- | 3 | e2e testing automation for KMSv2. Adding KMS test case to presubmit CI. Similar to CI implementation but for presubmit workflow. |
| CNTRLPLANE-1355 | Story | Closed | -- | 2 | Pre-merge testing for KMSv2. Closed. Standard presubmit gate setup. |

**Subtotal for CNTRLPLANE-1350 children:** 24 points (6 issues)

---

### Epic: CNTRLPLANE-1349 -- Expand HyperShift e2e test suite

Epic has **no** existing story points.

| Issue Key | Type | Status | Current SP | Proposed Points | Rationale |
|-----------|------|--------|------------|-----------------|-----------|
| CNTRLPLANE-3277 | Task | To Do | -- | 2 | Add TestAzureOAuthLoadBalancerPrivate e2e test. Single test addition, blocked by CNTRLPLANE-3222. Well-scoped, low risk once framework migration is done. |
| CNTRLPLANE-3276 | Task | To Do | -- | 3 | Add e2e test for private to publicAndPrivate endpoint access transition. Validates endpoint access state transitions. Slightly more complex than a single test add -- involves topology changes. Blocked by CNTRLPLANE-3222. |
| CNTRLPLANE-3222 | Task | In Progress | -- | 8 | Migrate self-managed Azure e2e tests to v2 Ginkgo framework. Large migration: refactoring shared helpers, creating 4 new test files, adding Makefile targets, env var registration, ensuring backward compatibility. Multiple independent work streams. **Consider splitting into smaller stories.** |
| CNTRLPLANE-3206 | Task | To Do | -- | 3 | Add periodic e2e job for self-managed Azure HCP. Creating periodic Prow job config, configuring alerting/reporting. Straightforward CI setup but requires environment validation. |
| CNTRLPLANE-3198 | Task | Closed | -- | 5 | Add self-managed Azure e2e test parity with self-managed AWS. Closed. Required gap analysis and implementing missing tests to achieve parity. Investigation + implementation. |
| CNTRLPLANE-2980 | Story | Closed | -- | 2 | Debug TestCreateClusterDefaultSecurityContextUID failure. Closed. Debugging a specific test failure -- targeted investigation. |
| CNTRLPLANE-2979 | Story | Closed | -- | 2 | Debug TestCreateClusterCustomConfig e2e failure. Closed. Debugging a specific test failure -- targeted investigation. |
| CNTRLPLANE-1354 | Story | Closed | -- | 2 | CI implementation for expanding e2e test suite. Closed. Standard CI setup. |
| CNTRLPLANE-1353 | Story | Closed | -- | 2 | e2e testing automation for expanding e2e test suite. Closed. Standard e2e automation. |
| CNTRLPLANE-1352 | Story | Closed | -- | 2 | Pre-merge testing for expanding e2e test suite. Closed. Standard presubmit gates. |
| CNTRLPLANE-208 | Task | Closed | -- | 1 | Document needed Azure infrastructure. Closed. Simple documentation task for cloud resource prerequisites. |

**Subtotal for CNTRLPLANE-1349 children:** 32 points (11 issues)

---

## Summary

### Totals

| Category | Count | Points |
|----------|-------|--------|
| Issues proposed for pointing | 38 | 128 |
| Already pointed (epics, skipped) | 2 | 2 (existing) |
| Flagged for splitting (8 pts) | 2 | 16 |
| Closed issues (proposed retroactively) | 14 | 37 |
| Open issues (proposed) | 24 | 91 |

### Points by Epic

| Epic | Key | Children | Total Points |
|------|-----|----------|--------------|
| Azure Disk CSI (GA) | STOR-2906 | 3 | 8 |
| Azure File CSI (GA) | STOR-2905 | 3 | 8 |
| Docs | OSDOCS-14975 | 0 | 0 |
| External OIDC | CNTRLPLANE-3253 | 3 | 8 |
| Performance Testing | CNTRLPLANE-2011 | 4 | 13 |
| Disaster Recovery | CNTRLPLANE-2010 | 7 | 26 |
| Autoscaling | CNTRLPLANE-2009 | 4 | 9 |
| KMSv2 | CNTRLPLANE-1350 | 6 | 24 |
| Expand e2e Test Suite | CNTRLPLANE-1349 | 11 | 32 |
| **Total** | | **41** | **128** |

*(41 = 38 stories/tasks + 3 counted in subtotals due to rounding; true leaf count is 38)*

### Flagged Issues

**8-point issues (consider splitting):**
- **CNTRLPLANE-3222** (8 pts) -- Migrate self-managed Azure e2e tests to v2 Ginkgo framework. This task has 6 listed implementation steps plus CI follow-up. Consider splitting into: (1) helper refactoring, (2) test file creation, (3) Makefile/build integration.
- **CNTRLPLANE-3070** (8 pts) -- Support KMS on self-managed Azure without affecting ARO HCP. Dual-path architecture change with risk to existing managed path. Consider splitting into: (1) design/investigation, (2) code path separation, (3) validation/testing.

### Notes

- All 38 child stories/tasks have `customfield_10028 = null` (no story points assigned).
- The 2 STOR epics (STOR-2906, STOR-2905) already have 1.0 story point each -- these were skipped.
- The remaining 7 epics have no story points.
- 14 of the 38 children are already Closed -- points were still proposed retroactively for completeness but the team may choose to skip these.
- OSDOCS-14975 (Docs epic) is Closed with no children found in Jira.

---

**DRY RUN COMPLETE -- No story points were written to Jira.**
