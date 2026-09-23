#!/usr/bin/env python3
"""Contract consistency and boundary verification script for Phase 0."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

REQUIRED_CONTRACTS = [
    "agent_contract.md",
    "tool_contract.md",
    "event_contract.md",
    "deployment_contract.md",
    "memory_contract.md",
    "review_contract.md",
]

REQUIRED_DOCS = [
    "architecture.md",
    "development-workflow.md",
]

CANONICAL_STATES = [
    "PENDING",
    "BUILDING",
    "TESTING",
    "APPROVED",
    "DEPLOYING",
    "HEALTH_CHECK",
    "SUCCESS",
    "FAILED",
    "ROLLING_BACK",
    "ROLLED_BACK",
]

CANONICAL_EVENTS = [
    "PR_OPENED",
    "PR_UPDATED",
    "REVIEW_STARTED",
    "REVIEW_COMPLETED",
    "TEST_STARTED",
    "TEST_COMPLETED",
    "DEPLOYMENT_STARTED",
    "DEPLOYMENT_COMPLETED",
    "DEPLOYMENT_FAILED",
    "HEALTH_CHECK_FAILED",
    "INCIDENT_CREATED",
    "DIAGNOSIS_STARTED",
    "DIAGNOSIS_COMPLETED",
    "ROLLBACK_STARTED",
    "ROLLBACK_COMPLETED",
    "RECOVERY_COMPLETED",
]

CANONICAL_TOOLS = [
    "github.get_repository",
    "github.get_pull_request",
    "github.get_diff",
    "tests.run",
    "deployment.deploy",
    "deployment.status",
    "deployment.logs",
    "deployment.rollback",
]


def verify_files_exist():
    contracts_dir = ROOT_DIR / "contracts"
    for contract in REQUIRED_CONTRACTS:
        p = contracts_dir / contract
        if not p.is_file():
            print(f"[FAIL] Missing contract file: {p}")
            return False
        print(f"[OK] Found contract: {contract}")

    docs_dir = ROOT_DIR / "docs"
    for doc in REQUIRED_DOCS:
        p = docs_dir / doc
        if not p.is_file():
            print(f"[FAIL] Missing doc file: {p}")
            return False
        print(f"[OK] Found doc: {doc}")

    return True


def verify_deployment_states():
    deploy_contract = (ROOT_DIR / "contracts" / "deployment_contract.md").read_text(encoding="utf-8")
    for state in CANONICAL_STATES:
        if state not in deploy_contract:
            print(f"[FAIL] State {state} not found in deployment_contract.md")
            return False
    print(f"[OK] All {len(CANONICAL_STATES)} canonical deployment states verified in deployment_contract.md")
    return True


def verify_events():
    event_contract = (ROOT_DIR / "contracts" / "event_contract.md").read_text(encoding="utf-8")
    for ev in CANONICAL_EVENTS:
        if ev not in event_contract:
            print(f"[FAIL] Event {ev} not found in event_contract.md")
            return False
    print(f"[OK] All {len(CANONICAL_EVENTS)} canonical lifecycle events verified in event_contract.md")
    return True


def verify_tools():
    tool_contract = (ROOT_DIR / "contracts" / "tool_contract.md").read_text(encoding="utf-8")
    for tool in CANONICAL_TOOLS:
        if tool not in tool_contract:
            print(f"[FAIL] Tool {tool} not found in tool_contract.md")
            return False
    print(f"[OK] All {len(CANONICAL_TOOLS)} canonical tools verified in tool_contract.md")
    return True


def main():
    print("=== AI DevOps Assistant: Contract Consistency Verification ===")
    checks = [
        verify_files_exist(),
        verify_deployment_states(),
        verify_events(),
        verify_tools(),
    ]
    if all(checks):
        print("\nAll Phase 0 contract and boundary checks PASSED.")
        sys.exit(0)
    else:
        print("\nSome checks FAILED. Review errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
