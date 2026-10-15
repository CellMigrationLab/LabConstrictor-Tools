#!/usr/bin/env bash
# Push the text results of the one-off run to the text-only branch `test-results` every INTERVAL seconds (default 600) and once more on exit.
# usage: push_results.sh RESULTS_DIR REPO_WORKTREE [INTERVAL]   (REPO_WORKTREE: a git worktree checked out on test-results)
# Only .json .md .txt .log files are copied (never screenshots); only the branch test-results is ever pushed.
set -u
src=${1:?results dir}; repo=${2:?worktree on test-results}; interval=${3:-600}
sync_once() {
  mkdir -p "$repo/results"
  (cd "$src" && find . -type f \( -name '*.json' -o -name '*.md' -o -name '*.txt' -o -name '*.log' -o -name '*.out' \) -size -2M -print0 | xargs -0 -I{} cp --parents {} "$repo/results/")
  python3 "$(dirname "$0")/collect_results.py" "$repo/results" > /dev/null 2>&1 || true
  cd "$repo" || return
  [ "$(git rev-parse --abbrev-ref HEAD)" = test-results ] || { echo "refusing: worktree is not on test-results"; return; }
  git add -A results >/dev/null 2>&1
  git diff --cached --quiet && return
  git commit -q -m "results $(date -u +%FT%TZ)" && for i in 1 2 3 4; do git push -q origin test-results && return; sleep $((2**i)); done
  echo "push failed after 4 tries at $(date -u +%T)"
}
trap 'sync_once; exit 0' INT TERM
while true; do sync_once; sleep "$interval" & wait $!; done
