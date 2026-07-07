#!/usr/bin/env sh
set -eu

CONFIG_FILE="wrangler.jsonc"

if [ -f "wrangler.cloudflare.jsonc" ]; then
  CONFIG_FILE="wrangler.cloudflare.jsonc"
fi

exec uv run pywrangler "$@" --config "$CONFIG_FILE"
