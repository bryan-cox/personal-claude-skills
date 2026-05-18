# Diagnosis: GitHub Actions Check Name Mismatch

## Problem

Branch protection requires a status check called **"Lint"**, but that check perpetually shows as **"Expected -- Waiting for status to be reported"** on PRs, even though the workflow runs successfully.

## Root Cause

GitHub Actions reports status checks using the **job name**, not the **workflow name**. The check name that GitHub reports follows this format:

```
<workflow name> / <job name>
```

Given this workflow configuration:

```yaml
name: Lint          # workflow-level name

jobs:
  lint:             # job key
    name: Run Linters   # job-level display name
    ...
```

The actual status check reported to GitHub is: **"Lint / Run Linters"**

Branch protection is configured to require a check called **"Lint"**, but no check with that exact name is ever reported. GitHub sees the workflow run complete successfully under the name "Lint / Run Linters", while it keeps waiting forever for a check literally called "Lint" -- which never arrives.

## Fix Options

### Option A: Update branch protection to match the actual check name (Recommended)

Change the required status check in branch protection settings from `Lint` to `Lint / Run Linters`.

Steps:
1. Go to **Settings > Branches > Branch protection rules** for your branch (e.g., `main`).
2. Edit the rule.
3. In **Require status checks to pass before merging**, remove `Lint`.
4. Search for and add `Lint / Run Linters`.
5. Save changes.

Note: The correct check name will only appear in the search dropdown after the workflow has run at least once on the repository. If it does not appear, push a commit or manually trigger the workflow first.

### Option B: Remove the job-level `name` so the job key is used directly

Change the workflow so the job does not have a `name:` field:

```yaml
name: Lint

jobs:
  lint:
    # name: Run Linters   <-- remove this line
    runs-on: ubuntu-latest
    steps:
      ...
```

This causes GitHub to report the check as **"Lint / lint"** (workflow name / job key). You would then set branch protection to require `Lint / lint`.

### Option C: Rename to produce the desired check name

If you specifically want the check to appear as just `Lint`, you need the workflow name and job name to align in a way that GitHub reports it as such. However, GitHub Actions always uses the `<workflow> / <job>` format, so a single-word check name like `Lint` is not achievable with GitHub Actions alone. You would need to use a separate commit status API call or a third-party action to post a status check with that exact name.

## Key Takeaway

GitHub Actions status check names always follow the pattern **"Workflow Name / Job Name"**. When configuring branch protection required checks, you must use this full compound name, not just the workflow name or the job name alone.

## Quick Reference

| Workflow `name:` | Job key | Job `name:` | Reported Check Name     |
|------------------|---------|-------------|-------------------------|
| Lint             | lint    | Run Linters | Lint / Run Linters      |
| Lint             | lint    | *(omitted)* | Lint / lint             |
| CI               | test    | Unit Tests  | CI / Unit Tests         |
| CI               | test    | *(omitted)* | CI / test               |
