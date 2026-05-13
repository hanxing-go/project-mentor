#!/usr/bin/env bash
# git_archaeology.sh — Analyze full Git history and output a project growth timeline
# Usage: ./git_archaeology.sh <repo-path> [--max-commits <N>] [--recent-days <N>]
# Output: JSON to stdout

set -o pipefail

REPO_PATH=""
MAX_COMMITS=2000
RECENT_DAYS=90
TIMEOUT_SEC=60

while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-commits) MAX_COMMITS="$2"; shift 2 ;;
    --recent-days) RECENT_DAYS="$2"; shift 2 ;;
    --timeout) TIMEOUT_SEC="$2"; shift 2 ;;
    *) REPO_PATH="$1"; shift ;;
  esac
done

if [ -z "$REPO_PATH" ] || [ ! -d "$REPO_PATH/.git" ]; then
  cat <<'EOF'
{"status":"error","error":"No Git repository found at the given path. Provide a path to a cloned repo with .git history."}
EOF
  exit 1
fi

cd "$REPO_PATH" || exit 1

# Check for shallow clone
COMMIT_COUNT=$(git rev-list --count HEAD 2>/dev/null || echo "0")
if [ "$COMMIT_COUNT" = "1" ] && git rev-parse --is-shallow-repository 2>/dev/null | grep -q "true"; then
  cat <<'EOF'
{"status":"error","error":"Repository is a shallow clone (--depth=1). Git archaeology requires full history. Re-clone without --depth."}
EOF
  exit 1
fi

# Escape helper
escape_json() {
  local s="${1//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  echo "$s"
}

# ── First Commit ──
FIRST_HASH=$(git rev-list --max-parents=0 HEAD 2>/dev/null | tail -1)
if [ -z "$FIRST_HASH" ]; then
  FIRST_HASH=$(git log --reverse --format="%H" 2>/dev/null | head -1)
fi

FIRST_DATE=$(git show -s --format="%ai" "$FIRST_HASH" 2>/dev/null | cut -d' ' -f1)
FIRST_AUTHOR=$(git show -s --format="%an" "$FIRST_HASH" 2>/dev/null)
FIRST_MSG=$(git show -s --format="%s" "$FIRST_HASH" 2>/dev/null)
FIRST_MSG_ESC=$(escape_json "$FIRST_MSG")
FIRST_FILES=$(git show --stat --format="" "$FIRST_HASH" 2>/dev/null | tail -1 | grep -oE '[0-9]+ file' | grep -oE '[0-9]+')
FIRST_FILES="${FIRST_FILES:-0}"
FIRST_INSERTIONS=$(git show --stat --format="" "$FIRST_HASH" 2>/dev/null | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+')
FIRST_INSERTIONS="${FIRST_INSERTIONS:-0}"

# ── Milestone Detection ──
MILESTONES_JSON="["

# Method A: Directory birth — first commit touching each top-level directory
DIR_INDEX=0
for dir in $(ls -d */ 2>/dev/null | grep -v 'node_modules\|vendor\|.git\|venv\|target\|__pycache__\|dist\|build\|.next' | head -10); do
  dirname="${dir%/}"
  first_touch=$(git log --reverse --format="%H|%ai|%s" -- "$dir" 2>/dev/null | head -1)
  if [ -n "$first_touch" ]; then
    hash=$(echo "$first_touch" | cut -d'|' -f1)
    date=$(echo "$first_touch" | cut -d'|' -f2 | cut -d' ' -f1)
    msg=$(echo "$first_touch" | cut -d'|' -f3-)
    msg_esc=$(escape_json "$msg")
    [ $DIR_INDEX -gt 0 ] && MILESTONES_JSON+=","
    MILESTONES_JSON+="{\"hash\":\"$hash\",\"date\":\"$date\",\"description\":\"Directory \`$dirname/\` created\",\"significance\":\"New subsystem: $dirname\",\"detected_by\":\"directory_birth\"}"
    ((DIR_INDEX++))
  fi
done

# Method B: Tag-based milestones (major versions only)
TAG_INDEX=0
git tag --sort=creatordate --format="%(creatordate:short)|%(refname:short)" 2>/dev/null | \
  grep -iE 'v?[0-9]+\.[0-9]+' | head -10 | while IFS='|' read -r tagdate tagname; do
  taghash=$(git rev-list -1 "$tagname" 2>/dev/null | head -1)
  if [ -n "$taghash" ]; then
    TAG_MSG=$(git show -s --format="%s" "$taghash" 2>/dev/null)
    TAG_MSG_ESC=$(escape_json "$TAG_MSG")
    echo "{\"hash\":\"$taghash\",\"date\":\"$tagdate\",\"description\":\"Release: $tagname\",\"significance\":\"Version release — $TAG_MSG_ESC\",\"detected_by\":\"tag\"}" >> /tmp/milestone_tags_$$
  fi
done

if [ -f /tmp/milestone_tags_$$ ]; then
  while IFS= read -r tagline; do
    [ $((DIR_INDEX + TAG_INDEX)) -gt 0 ] && MILESTONES_JSON+=","
    MILESTONES_JSON+="$tagline"
    ((TAG_INDEX++))
  done < /tmp/milestone_tags_$$
  rm -f /tmp/milestone_tags_$$
fi

MILESTONES_JSON+="]"

# ── Recent Activity ──
RECENT_COMMITS=$(git log --after="$RECENT_DAYS days ago" --oneline 2>/dev/null | wc -l | tr -d ' ')

# Active branches (top 5)
ACTIVE_BRANCHES=$(git branch -r --sort=-committerdate 2>/dev/null | head -10 | \
  grep -v 'HEAD ->' | \
  sed 's/^[ *]*//' | sed 's/origin\///' | \
  head -5 | \
  awk 'BEGIN{printf "["} {printf "%s\"%s\"", (NR>1?",":""), $0} END{printf "]"}')
ACTIVE_BRANCHES="${ACTIVE_BRANCHES:-[]}"

# Top contributors in recent period
TOP_CONTRIBUTORS_JSON=$(
  git shortlog -sn --after="$RECENT_DAYS days ago" 2>/dev/null | head -5 | \
  awk 'BEGIN{printf "["} {
    commits=$1; $1=""; name=substr($0,2);
    gsub(/"/, "\\\"", name);
    printf "%s{\"name\":\"%s\",\"commits\":%d}", (NR>1?",":""), name, commits
  } END{printf "]"}'
)
TOP_CONTRIBUTORS_JSON="${TOP_CONTRIBUTORS_JSON:-[]}"

# ── Growth Timeline (sampled at milestones + every N commits) ──
TOTAL_COMMITS=$(git rev-list --count HEAD 2>/dev/null || echo "0")
SAMPLE_INTERVAL=$(( TOTAL_COMMITS / 20 ))
[ "$SAMPLE_INTERVAL" -lt 1 ] && SAMPLE_INTERVAL=1

TIMELINE_JSON="["
TIMELINE_INDEX=0

# Sample total files at intervals
git log --reverse --format="%ai" 2>/dev/null | \
  awk -v interval="$SAMPLE_INTERVAL" 'NR % interval == 0 || NR == 1 {print NR, $0}' | \
  head -25 | while read -r line_num commit_date; do
  commit_hash=$(git rev-list --reverse HEAD 2>/dev/null | sed -n "${line_num}p")
  if [ -n "$commit_hash" ]; then
    total_files=$(git ls-tree -r --name-only "$commit_hash" 2>/dev/null | \
      grep -v 'node_modules/\|vendor/\|.git/\|venv/\|target/' | wc -l | tr -d ' ')
    total_files="${total_files:-0}"
    total_contributors=$(git shortlog -sn --before="$commit_date" 2>/dev/null | wc -l | tr -d ' ')
    total_contributors="${total_contributors:-0}"
    ym=$(echo "$commit_date" | cut -d'-' -f1,2)
    [ $TIMELINE_INDEX -gt 0 ] && TIMELINE_JSON+=","
    TIMELINE_JSON+="{\"date\":\"$ym\",\"total_commits\":$line_num,\"total_files\":$total_files,\"total_contributors\":$total_contributors}"
    ((TIMELINE_INDEX++))
  fi
done
TIMELINE_JSON+="]"

# ── Narrative Summary Generation ──
TOTAL_AUTHORS=$(git shortlog -sn 2>/dev/null | wc -l | tr -d ' ')
TOTAL_AUTHORS="${TOTAL_AUTHORS:-1}"

# Current file count (from project root)
FILE_COUNT_CURRENT=$(find . -type f \
  -not -path '*/node_modules/*' \
  -not -path '*/vendor/*' \
  -not -path '*/.git/*' \
  -not -path '*/venv/*' \
  -not -path '*/target/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/dist/*' \
  -not -path '*/build/*' \
  -not -path '*/.next/*' 2>/dev/null | wc -l | tr -d ' ')

NARRATIVE="This project began on $FIRST_DATE when $FIRST_AUTHOR made the first commit: \"$FIRST_MSG\" — just $FIRST_FILES file(s) and $FIRST_INSERTIONS line(s) of code. Over $TOTAL_COMMITS commits by $TOTAL_AUTHORS contributor(s), it grew to $FILE_COUNT_CURRENT files. In the last $RECENT_DAYS days, there have been $RECENT_COMMITS commits."

NARRATIVE_ESC=$(escape_json "$NARRATIVE")

# ── Assemble JSON Output ──
cat <<EOF
{
  "status": "success",
  "first_commit": {
    "hash": "$FIRST_HASH",
    "date": "$FIRST_DATE",
    "author": "$(escape_json "$FIRST_AUTHOR")",
    "message": "$FIRST_MSG_ESC",
    "files_changed": $FIRST_FILES,
    "lines_added": $FIRST_INSERTIONS
  },
  "milestones": $MILESTONES_JSON,
  "recent_activity": {
    "days_analyzed": $RECENT_DAYS,
    "commit_count": $RECENT_COMMITS,
    "active_branches": $ACTIVE_BRANCHES,
    "top_contributors": $TOP_CONTRIBUTORS_JSON
  },
  "stats": {
    "total_commits": $TOTAL_COMMITS,
    "total_contributors": $TOTAL_AUTHORS,
    "current_file_count": $FILE_COUNT_CURRENT
  },
  "growth_timeline": $TIMELINE_JSON,
  "narrative_summary": "$NARRATIVE_ESC"
}
EOF
