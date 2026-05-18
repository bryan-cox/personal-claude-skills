# Jira Pointer -- Dry Run

**Mode:** `--dry-run` (no points written to Jira)

## Flagged Issues

No issues flagged for splitting.

## Proposal Table

| Issue Key | Type | Summary | Proposed Points | Rationale |
|-----------|------|---------|-----------------|-----------|
| CNTRLPLANE-3070 | Story | Support KMS on self-managed Azure without affecting ARO HCP | 5 | Requires investigation to identify all affected code paths; moderate risk due to the constraint of not regressing the ARO HCP / managed Azure KMS path; involves cross-path testing (self-managed vs managed Azure) and documentation of configuration differences; partially exploratory since the first AC is to discover the full scope of changes needed. |

## Detailed Rationale

**CNTRLPLANE-3070 -- 5 points**

| Dimension | Assessment |
|-----------|------------|
| Investigation / design | Moderate. First acceptance criterion is to "identify all code paths that need modification," which signals the full scope is not yet mapped. |
| Files / components touched | Multiple. KMS encryption spans etcd encryption configuration, Azure Key Vault integration, and HyperShift control plane operator logic. |
| Dependencies / collaboration | Yes. Part of epic CNTRLPLANE-1350. Must coordinate with managed Azure path to avoid regressions. |
| Risk | Moderate. Explicit AC: "does not alter or break existing ARO HCP / managed Azure KMS behavior." Regression risk is real and must be verified across both paths. |
| Clarity | Partially exploratory. Well-written ACs, but the work starts with discovery before implementation. |

**Why not 3?** A 3-pointer is "fairly straightforward" with only "minor risks." This story involves genuine investigation (discovering code paths), dual-path regression risk, and cross-path testing -- more complexity and risk than a 3 warrants.

**Why not 8?** An 8 is a "big task" requiring a design doc. While there is investigation, the scope is constrained to a single platform variant (self-managed Azure) and the work is bounded by the existing KMS architecture. No design doc is called for.

## Summary

- **Issues assessed:** 1
- **Total proposed points:** 5
- **Flagged for splitting:** 0

This is a dry run. No story points were written to Jira.
