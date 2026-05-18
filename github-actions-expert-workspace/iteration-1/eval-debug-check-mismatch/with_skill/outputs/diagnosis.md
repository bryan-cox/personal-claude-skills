# Diagnosis: Lint Check Stuck at "Expected -- Waiting for status to be reported"

## Root Cause

The required status check name in branch protection does not match the check name that GitHub Actions actually reports.

GitHub Actions constructs the status check name from the **workflow `name`** and the **job `name`** (or job key), not from either one alone. Given the workflow configuration described:

```yaml
name: Lint

jobs:
  lint:
    name: Run Linters
    steps: ...
```

GitHub Actions reports the status check as: **`Lint / Run Linters`**

Branch protection is configured to require a check called: **`Lint`**

Since no check named exactly `Lint` is ever reported, GitHub shows it as "Expected -- Waiting for status to be reported" indefinitely. The workflow itself runs fine and the `Lint / Run Linters` check passes, but branch protection keeps waiting for a check that will never arrive.

## How GitHub Actions Names Status Checks

The format is: `<workflow name> / <job name> (<optional matrix info>)`

- If a job has a `name:` field, that is used as the job portion.
- If a job has no `name:` field, the job mapping key (e.g., `lint`) is used.
- The workflow-level `name:` is always the prefix.

So:
| Workflow `name` | Job key | Job `name` | Reported check name |
|---|---|---|---|
| `Lint` | `lint` | `Run Linters` | `Lint / Run Linters` |
| `Lint` | `lint` | *(none)* | `Lint / lint` |
| *(none)* | `lint` | `Run Linters` | `<filename> / Run Linters` |

## Fix

You have two options. Choose one:

### Option A: Update Branch Protection to Match the Actual Check Name (Recommended)

Change the required status check in branch protection settings from `Lint` to `Lint / Run Linters`.

1. Go to **Settings > Branches > Branch protection rules** for the relevant branch.
2. Edit the rule and under **Require status checks to pass before merging**, remove `Lint`.
3. Search for and add `Lint / Run Linters` (it will appear in the autocomplete once the workflow has run at least once).
4. Save.

This is the recommended approach because it requires no workflow file changes and won't disrupt in-flight PRs.

### Option B: Change the Workflow So the Check Name Matches "Lint"

Remove the job-level `name:` field so the check is reported as `Lint / lint`, or restructure so the reported name matches exactly what branch protection expects. However, there is no way to make GitHub Actions report just `Lint` without the slash and job portion -- the format is always `<workflow name> / <job identifier>`.

If you want the shortest possible check name, remove the workflow-level `name:` and remove the job-level `name:`, then the check name becomes the workflow filename and job key (e.g., `lint.yml / lint`). This is usually less readable, so Option A is preferred.

A practical Option B variant:

```yaml
name: Lint

jobs:
  lint:
    # Remove the "name: Run Linters" line so the check becomes "Lint / lint"
    runs-on: arc-runner-set
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v6
      - run: make lint
```

Then update branch protection to require `Lint / lint`.

**In all cases, the branch protection check name must exactly match what GitHub Actions reports, including the `<workflow name> / <job name>` format with the slash separator.**

## Verification

After applying the fix, verify the check name matches by running:

```bash
gh pr checks <PR_NUMBER>
```

This lists all checks and their names as GitHub sees them, which is what branch protection matches against.
