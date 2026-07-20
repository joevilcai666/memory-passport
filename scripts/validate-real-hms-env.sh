#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env ]]; then
  set -a
  # The repository-owned .env is the same source Docker Compose reads.
  # shellcheck disable=SC1091
  source .env
  set +a
fi

required=(
  HMS_API_LLM_API_KEY
  HMS_API_RETAIN_LLM_API_KEY
  HMS_API_EMBEDDINGS_OPENAI_API_KEY
)

for name in "${required[@]}"; do
  value="${!name:-}"
  if [[ -z "$value" || "$value" == *_change_me ]]; then
    echo "real HMS mode requires a non-placeholder $name; see docs/real-hms.md" >&2
    exit 2
  fi
done

echo "real HMS credential configuration is present"
