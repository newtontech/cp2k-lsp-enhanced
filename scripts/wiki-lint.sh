#!/usr/bin/env bash
# wiki-lint.sh — lightweight LLM-wiki lint for cp2k-lsp-enhanced
# Checks for orphan pages, broken internal links, and missing index references.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
errors=0

echo "=== LLM Wiki Lint: cp2k-lsp-enhanced ==="

wiki_files=()
while IFS= read -r f; do
  wiki_files+=("$f")
done < <(find "$repo_root/wiki" -name "*.md" -type f 2>/dev/null | sort)

echo "Found ${#wiki_files[@]} wiki pages"

index="$repo_root/index.md"
wiki_index="$repo_root/wiki/index.md"
for f in "${wiki_files[@]}"; do
  basename_f="$(basename "$f" .md)"
  if ! grep -q "$basename_f" "$index" 2>/dev/null && ! grep -q "$basename_f" "$wiki_index" 2>/dev/null; then
    echo "WARN: $basename_f not referenced in index.md or wiki/index.md"
  fi
done

broken=0
for f in "${wiki_files[@]}"; do
  dir="$(dirname "$f")"
  while IFS= read -r link; do
    target="$dir/$link"
    if [ ! -f "$target" ]; then
      echo "BROKEN LINK: $f -> $link"
      broken=$((broken + 1))
      errors=$((errors + 1))
    fi
  done < <(grep -oP '\]\(\K[^)]+(?=\))' "$f" 2>/dev/null | grep '\.md' | head -20 || true)
done
echo "Internal link check: $broken broken links"

raw_count=$(find "$repo_root/raw/assets" -type f \( -name "*.md" -o -name "*.inp" \) 2>/dev/null | wc -l | tr -d ' ')
echo "Raw asset files (md/inp): $raw_count"

if [ "$errors" -gt 0 ]; then
  echo "RESULT: $errors issue(s) found"
  exit 1
else
  echo "RESULT: All checks passed"
  exit 0
fi
