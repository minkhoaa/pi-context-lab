#!/usr/bin/env bash
# scripts/preflight.sh
# Runs all preflight verifications in sequence and outputs clear colorized PASS/FAIL indicators.

set -o pipefail

# ANSI color codes
BOLD="\033[1m"
GREEN="\033[1;32m"
RED="\033[1;31m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
RESET="\033[0m"

echo -e "${BOLD}${CYAN}======================================================================${RESET}"
echo -e "${BOLD}${CYAN}      PI CONTEXT OPTIMIZATION BENCHMARK - PREFLIGHT VERIFICATION      ${RESET}"
echo -e "${BOLD}${CYAN}======================================================================${RESET}"

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${BASE_DIR}:${PYTHONPATH}"

FAILED_STEPS=()
PASSED_STEPS=()

run_verification() {
    local name="$1"
    local script="$2"

    echo ""
    echo -e "${BOLD}--> Running [${name}] ...${RESET}"
    if python3 "${BASE_DIR}/scripts/${script}"; then
        echo -e "${GREEN}[ PASS ] ${name} succeeded.${RESET}"
        PASSED_STEPS+=("${name}")
    else
        echo -e "${RED}[ FAIL ] ${name} failed!${RESET}"
        FAILED_STEPS+=("${name}")
    fi
}

run_verification "Profiles Validation" "verify-profiles.py"
run_verification "Shared Authentication Wiring" "verify-shared-auth.py"
run_verification "Isolation Checks" "verify-isolation.py"
run_verification "Fixtures & Evaluators" "verify-fixtures.py"
run_verification "Telemetry Smoke Test" "smoke-local.py"

echo ""
echo -e "${BOLD}${CYAN}======================================================================${RESET}"
echo -e "${BOLD}PREFLIGHT SUMMARY:${RESET}"
echo -e "  Passed: ${GREEN}${#PASSED_STEPS[@]}${RESET}"
echo -e "  Failed: ${RED}${#FAILED_STEPS[@]}${RESET}"

if [ ${#FAILED_STEPS[@]} -eq 0 ]; then
    echo -e "${BOLD}${GREEN}==> ALL PREFLIGHT VERIFICATIONS PASSED SUCCESSFULLY.${RESET}"
    echo -e "${BOLD}${CYAN}======================================================================${RESET}"
    exit 0
else
    echo -e "${BOLD}${RED}==> PREFLIGHT FAILED on: ${FAILED_STEPS[*]}${RESET}"
    echo -e "${BOLD}${CYAN}======================================================================${RESET}"
    exit 1
fi
