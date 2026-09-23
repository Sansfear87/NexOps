# Review Contract Specification

**Document Version:** 1.0.0  
**Status:** Canonical Interface Definition  
**Last Updated:** Phase 0 (Foundation)

---

## 1. Overview & Objectives

The Code Review subsystem automates the inspection of pull request diffs, code additions, dependencies, and configurations. It produces a deterministic, machine-readable `ReviewResult` that can be directly mapped to GitHub PR comments, risk gates, and automated deployment blocks.

### Review Principles:
- **Zero Free-Form Unstructured Outputs:** The AI review agent must emit data conforming strictly to this schema.
- **Actionable Recommendations:** Every issue identified must include concrete guidance or fix suggestions.
- **Severity-Driven Gates:** Critical or high-severity findings directly block automated staging or production deployments.

---

## 2. Structured AI Review Result Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ReviewResult",
  "type": "object",
  "required": [
    "review_id",
    "pull_number",
    "head_sha",
    "summary",
    "overall_risk",
    "confidence",
    "verdict",
    "findings"
  ],
  "properties": {
    "review_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for this review execution."
    },
    "pull_number": {
      "type": "integer",
      "description": "Target GitHub pull request number."
    },
    "head_sha": {
      "type": "string",
      "description": "Git commit SHA evaluated."
    },
    "summary": {
      "type": "string",
      "description": "Executive summary of the changes, architectural impact, and major concerns."
    },
    "overall_risk": {
      "type": "string",
      "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
      "description": "Calculated risk score assessing probability and impact of production regression."
    },
    "risk_rationale": {
      "type": "string",
      "description": "Justification for the assigned overall_risk."
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Confidence score of the review evaluation (0.0 to 1.0)."
    },
    "verdict": {
      "type": "string",
      "enum": ["APPROVE", "REQUEST_CHANGES", "COMMENT"],
      "description": "GitHub review verdict to apply."
    },
    "findings": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/ReviewFinding"
      },
      "description": "List of granular, file-and-line-anchored code findings."
    },
    "metadata": {
      "type": "object",
      "properties": {
        "files_analyzed_count": { "type": "integer" },
        "lines_added_count": { "type": "integer" },
        "lines_deleted_count": { "type": "integer" },
        "duration_ms": { "type": "integer" },
        "model_used": { "type": "string" }
      }
    }
  },
  "definitions": {
    "ReviewFinding": {
      "type": "object",
      "required": [
        "finding_id",
        "file",
        "line",
        "category",
        "severity",
        "description",
        "recommendation",
        "confidence"
      ],
      "properties": {
        "finding_id": {
          "type": "string",
          "format": "uuid"
        },
        "file": {
          "type": "string",
          "description": "Relative file path within the repository."
        },
        "line": {
          "type": "integer",
          "description": "Target line number in the diff/head commit (1-indexed)."
        },
        "end_line": {
          "type": ["integer", "null"],
          "description": "Optional end line for multi-line findings."
        },
        "category": {
          "type": "string",
          "enum": [
            "SECURITY",
            "BUG",
            "PERFORMANCE",
            "ARCHITECTURE",
            "STYLE",
            "TESTING",
            "DEVOPS"
          ],
          "description": "Taxonomy category of the finding."
        },
        "severity": {
          "type": "string",
          "enum": ["INFO", "WARNING", "ERROR", "BLOCKER"],
          "description": "Impact severity. ERROR and BLOCKER trigger change requests."
        },
        "description": {
          "type": "string",
          "description": "Detailed explanation of the flaw, bug, or vulnerability."
        },
        "recommendation": {
          "type": "string",
          "description": "Actionable instructions or suggested code diff to resolve the finding."
        },
        "suggested_diff": {
          "type": ["string", "null"],
          "description": "Unified diff snippet representing the proposed fix."
        },
        "confidence": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Confidence level in this specific finding."
        }
      }
    }
  }
}
```

---

## 3. Severity & Risk Matrix

| Finding Severity | Definition | Impact on Verdict |
|---|---|---|
| `INFO` | Stylistic, readability, or non-critical improvement | `COMMENT` (unless other issues exist) |
| `WARNING` | Potential edge case, missing test, minor performance drain | `COMMENT` or `APPROVE` with caution |
| `ERROR` | Logic bug, memory leak, unhandled exception, syntax error | `REQUEST_CHANGES` (Blocks staging deploy) |
| `BLOCKER` | Critical security flaw (SQLi, RCE, secret exposure), breaking schema | `REQUEST_CHANGES` (Immediate gate fail) |

### Overall Risk Derivation:
- `LOW`: Zero findings above `INFO`, or low-complexity documentation/styling updates.
- `MEDIUM`: Contained `WARNING` findings; standard business logic additions with test coverage.
- `HIGH`: Unhandled errors, missing critical tests, or breaking changes in staging paths.
- `CRITICAL`: Any `BLOCKER` finding; direct danger to data integrity or security.
