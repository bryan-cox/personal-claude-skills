# HyperShift Presubmit Report Plugin

Generate pass/fail health reports for `openshift/hypershift` presubmit CI jobs using the Prow API.

## Usage

Use `/hypershift-presubmit-report` or ask about HyperShift presubmit health, pass rates, or failures. The skill generates an HTML report by default and also supports Markdown and JSON output over a configurable time range.

## Requirements

- Python 3
- Network access to the public Prow API; no authentication or third-party Python packages are required
