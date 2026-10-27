#!/usr/bin/env bash
# scripts/setup-shared-auth.sh
# Safely create symbolic links from ready profiles (A, P1, P2, P3) to ~/.pi/agent/auth.json
# Strictly idempotent and safe: never overwrites real files or unexpected symlinks.
# Never reads, echoes, or logs credential secrets.

set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIN_AGENT_DIR="${HOME}/.pi/agent"
AUTH_SOURCE="${MAIN_AGENT_DIR}/auth.json"

echo "=== [setup-shared-auth] Initializing Shared Authentication Linker ==="

# 1. Verify main auth source exists and is a regular file
if [[ ! -e "${AUTH_SOURCE}" ]]; then
    echo "ERROR: Main authentication file not found at ${AUTH_SOURCE}" >&2
    exit 1
fi

if [[ ! -f "${AUTH_SOURCE}" ]]; then
    echo "ERROR: Main authentication source is not a regular file: ${AUTH_SOURCE}" >&2
    exit 1
fi

# 2. Verify canonical path resolution (prevent directory traversal/symlink evasion)
REAL_AUTH_SOURCE="$(realpath "${AUTH_SOURCE}")"
EXPECTED_REAL_SOURCE="$(realpath "${HOME}/.pi/agent/auth.json")"
if [[ "${REAL_AUTH_SOURCE}" != "${EXPECTED_REAL_SOURCE}" ]]; then
    echo "ERROR: Resolved auth path (${REAL_AUTH_SOURCE}) does not match expected canonical source (${EXPECTED_REAL_SOURCE})" >&2
    exit 1
fi

# 3. Check permissions on auth.json (must not be world-readable or world-writable)
PERMS=$(stat -c "%a" "${AUTH_SOURCE}")
if [[ "${PERMS: -1}" != "0" ]]; then
    echo "ERROR: Main authentication file has overly permissive permissions (${PERMS}). Must not be accessible by other users." >&2
    exit 1
fi
echo "Verified source: ${AUTH_SOURCE} (permissions: ${PERMS})"

# 4. Target profiles for shared authentication: A (baseline), P1 (sift), P2 (context-prune), P3 (dcp)
# Profile P4 (context-engine) is explicitly excluded until dependencies and provenance gates resolve.
PROFILES=("baseline" "sift" "context-prune" "dcp")

for prof in "${PROFILES[@]}"; do
    TARGET_DIR="${LAB_DIR}/agents/${prof}"
    TARGET_LINK="${TARGET_DIR}/auth.json"

    if [[ ! -d "${TARGET_DIR}" ]]; then
        echo "Creating agent directory: ${TARGET_DIR}"
        mkdir -p "${TARGET_DIR}"
    fi

    if [[ -L "${TARGET_LINK}" ]]; then
        CURRENT_TARGET="$(readlink "${TARGET_LINK}")"
        if [[ "${CURRENT_TARGET}" == "${AUTH_SOURCE}" || "${CURRENT_TARGET}" == "${REAL_AUTH_SOURCE}" ]]; then
            echo "Profile [${prof}]: Symlink already exists and correctly points to ${AUTH_SOURCE}"
            continue
        else
            echo "CONFLICT: Profile [${prof}] symlink points to unexpected destination: ${CURRENT_TARGET}" >&2
            echo "Safety abort: will not overwrite unexpected symlink automatically." >&2
            exit 2
        fi
    elif [[ -e "${TARGET_LINK}" ]]; then
        echo "CONFLICT: Profile [${prof}] contains an existing non-symlink file at ${TARGET_LINK}" >&2
        echo "Safety abort: will not overwrite existing file." >&2
        exit 3
    else
        # Create atomic relative or absolute symlink as specified
        ln -s "${AUTH_SOURCE}" "${TARGET_LINK}"
        echo "Profile [${prof}]: Successfully created symlink -> ${AUTH_SOURCE}"
    fi
done

echo "=== [setup-shared-auth] Shared Authentication Setup Complete ==="
exit 0
