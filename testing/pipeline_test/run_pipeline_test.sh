#!/bin/bash
# Run doc_refresh pipeline on test documents
# Usage: ./run_pipeline_test.sh [--dry-run] [--force]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_DIR"

# Load .env
set -a
source .env
set +a

# Override for pipeline test
export BASE_PATH="$SCRIPT_DIR"
export DATABASE_NAMES="test_docs"
export FILE_SOURCE_MODE="local"
export IRIS_LOG_LEVEL="INFO"

# Verify OPENAI_API_KEY is set
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "ERROR: OPENAI_API_KEY not set. Export it before running."
    exit 1
fi

echo "=== Doc Refresh Pipeline Test ==="
echo "BASE_PATH: $BASE_PATH"
echo "DATABASE_NAMES: $DATABASE_NAMES"
echo "Test docs:"
ls -1 "$BASE_PATH/test_docs/"
echo ""

# Activate venv and run
source venv/bin/activate
python -m doc_refresh.main "$@"
