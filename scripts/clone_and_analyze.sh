#!/usr/bin/env bash
# clone_and_analyze.sh — Clone a GitHub repo and generate a structured project overview
# Usage: ./clone_and_analyze.sh <repo-url> [--deep] [--output-dir <dir>]
# Output: JSON to stdout

set -o pipefail

REPO_URL=""
DEEP=false
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --deep) DEEP=true; shift ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    *) REPO_URL="$1"; shift ;;
  esac
done

if [ -z "$REPO_URL" ]; then
  cat <<'EOF'
{"status":"error","error":"No repository URL provided. Usage: clone_and_analyze.sh <repo-url> [--deep] [--output-dir <dir>]"}
EOF
  exit 1
fi

# Extract project name from URL
# Handles: https://github.com/user/repo, git@github.com:user/repo.git, user/repo
PROJECT_NAME=$(echo "$REPO_URL" | sed -E 's|.*/([^/]+)(\.git)?$|\1|' | sed 's/\.git$//')
if [ -z "$PROJECT_NAME" ]; then
  cat <<'EOF'
{"status":"error","error":"Could not parse project name from URL."}
EOF
  exit 1
fi

CLONE_DIR="${OUTPUT_DIR:-/tmp/project-mentor-clones}/$PROJECT_NAME"

# Remove existing clone if present
rm -rf "$CLONE_DIR" 2>/dev/null

# Clone
CLONE_ARGS="--depth=1"
if $DEEP; then
  CLONE_ARGS=""
fi

CLONE_START=$(date +%s)
if ! git clone $CLONE_ARGS "$REPO_URL" "$CLONE_DIR" 2>/tmp/clone_stderr_$$; then
  CLONE_ERR=$(cat /tmp/clone_stderr_$$ 2>/dev/null | head -5)
  rm -f /tmp/clone_stderr_$$
  cat <<EOF
{"status":"error","error":"Failed to clone repository. ${CLONE_ERR}"}
EOF
  exit 1
fi
CLONE_END=$(date +%s)
CLONE_DURATION=$((CLONE_END - CLONE_START))
rm -f /tmp/clone_stderr_$$

cd "$CLONE_DIR" || exit 1

# ── Language Detection ──
detect_language() {
  local ext
  local counts
  # Count files by extension, exclude vendor/node_modules/.git
  counts=$(find . -type f \
    -not -path '*/node_modules/*' \
    -not -path '*/vendor/*' \
    -not -path '*/.git/*' \
    -not -path '*/venv/*' \
    -not -path '*/target/*' \
    -not -path '*/__pycache__/*' \
    -not -path '*/dist/*' \
    -not -path '*/build/*' \
    -not -path '*/.next/*' 2>/dev/null | \
    sed -n 's/.*\.\([a-zA-Z0-9]\+\)$/\1/p' | \
    sort | uniq -c | sort -rn | head -20)

  # Map extensions to languages using a temp file (macOS bash 3.2 compat: no declare -A)
  local scores_file
  scores_file=$(mktemp /tmp/pm_lang_scores.XXXXXX)

  while read -r count ext; do
    case "$ext" in
      go)           echo "Go $count" ;;
      rs)           echo "Rust $count" ;;
      py|pyx)       echo "Python $count" ;;
      ts|tsx)       echo "TypeScript $count" ;;
      js|jsx|mjs)   echo "JavaScript $count" ;;
      java)         echo "Java $count" ;;
      rb)           echo "Ruby $count" ;;
      php)          echo "PHP $count" ;;
      c|cpp|h|hpp)  echo "C/C++ $count" ;;
      swift)        echo "Swift $count" ;;
      kt|kts)       echo "Kotlin $count" ;;
      vue)          echo "Vue $count" ;;
      svelte)       echo "Svelte $count" ;;
      sh|bash|zsh)  echo "Shell $count" ;;
      sol)          echo "Solidity $count" ;;
      *)            ;; # unknown extension
    esac
  done <<< "$counts" >> "$scores_file"

  # Aggregate scores by language using awk (POSIX, works on macOS + Linux)
  local primary
  primary=$(awk '{scores[$1]+=$2} END {for(lang in scores) print scores[lang], lang}' "$scores_file" | sort -rn | head -n 1 | cut -d' ' -f2-)
  echo "${primary:-Unknown}"

  # Emit language breakdown as JSON object
  awk '{scores[$1]+=$2} END {
    first=1; printf "{";
    for(lang in scores) {
      if(!first) printf ","; first=0;
      printf "\"%s\":%d", lang, scores[lang];
    }
    printf "}";
  }' "$scores_file"

  rm -f "$scores_file"
}

LANG_OUTPUT=$(detect_language)
PRIMARY_LANGUAGE=$(echo "$LANG_OUTPUT" | head -1)
LANG_BREAKDOWN=$(echo "$LANG_OUTPUT" | tail -1)

# ── Framework Detection ──
detect_framework() {
  local framework="null"

  # Go
  if [ -f "go.mod" ]; then
    if grep -q 'gin-gonic/gin' go.mod 2>/dev/null; then framework='"Gin"'
    elif grep -q 'labstack/echo' go.mod 2>/dev/null; then framework='"Echo"'
    elif grep -q 'gofiber/fiber' go.mod 2>/dev/null; then framework='"Fiber"'
    elif grep -q 'gorilla/mux' go.mod 2>/dev/null; then framework='"Gorilla Mux"'
    elif grep -q 'spf13/cobra' go.mod 2>/dev/null; then framework='"Cobra (CLI)"'
    elif grep -q 'urfave/cli' go.mod 2>/dev/null; then framework='"urfave/cli (CLI)"'
    fi
  fi

  # Node
  if [ -f "package.json" ]; then
    if grep -q '"next"' package.json 2>/dev/null; then framework='"Next.js"'
    elif grep -q '"react"' package.json 2>/dev/null && ! grep -q '"next"' package.json 2>/dev/null; then framework='"React"'
    elif grep -q '"vue"' package.json 2>/dev/null; then framework='"Vue"'
    elif grep -q '"svelte"' package.json 2>/dev/null; then framework='"Svelte"'
    elif grep -q '"express"' package.json 2>/dev/null; then framework='"Express"'
    elif grep -q '"fastify"' package.json 2>/dev/null; then framework='"Fastify"'
    elif grep -q '"koa"' package.json 2>/dev/null; then framework='"Koa"'
    elif grep -q '"nestjs"' package.json 2>/dev/null; then framework='"NestJS"'
    elif grep -q '"astro"' package.json 2>/dev/null; then framework='"Astro"'
    fi
  fi

  # Python
  if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
    local py_deps=""
    [ -f "requirements.txt" ] && py_deps=$(cat requirements.txt 2>/dev/null)
    [ -f "pyproject.toml" ] && py_deps+=$(cat pyproject.toml 2>/dev/null)
    if echo "$py_deps" | grep -q 'fastapi'; then framework='"FastAPI"'
    elif echo "$py_deps" | grep -q 'django'; then framework='"Django"'
    elif echo "$py_deps" | grep -q 'flask'; then framework='"Flask"'
    elif echo "$py_deps" | grep -q 'typer\|click'; then framework='"Click/Typer (CLI)"'
    elif echo "$py_deps" | grep -q 'torch\|tensorflow\|jax'; then framework='"ML Framework"'
    fi
  fi

  # Rust
  if [ -f "Cargo.toml" ]; then
    if grep -q 'actix-web' Cargo.toml 2>/dev/null; then framework='"Actix Web"'
    elif grep -q 'axum' Cargo.toml 2>/dev/null; then framework='"Axum"'
    elif grep -q 'rocket' Cargo.toml 2>/dev/null; then framework='"Rocket"'
    elif grep -q 'clap' Cargo.toml 2>/dev/null; then framework='"Clap (CLI)"'
    fi
  fi

  echo "$framework"
}
FRAMEWORK=$(detect_framework)

# ── Build System Detection ──
detect_build() {
  [ -f "go.mod" ] && { echo '"go mod"'; return; }
  [ -f "go.sum" ] && { echo '"go mod"'; return; }
  [ -f "package.json" ] && { echo '"npm/yarn/pnpm"'; return; }
  [ -f "Cargo.toml" ] && { echo '"Cargo"'; return; }
  [ -f "Makefile" ] && { echo '"Make"'; return; }
  [ -f "CMakeLists.txt" ] && { echo '"CMake"'; return; }
  [ -f "pom.xml" ] && { echo '"Maven"'; return; }
  [ -f "build.gradle" ] && { echo '"Gradle"'; return; }
  [ -f "pyproject.toml" ] && { echo '"pip/setuptools"'; return; }
  [ -f "setup.py" ] && { echo '"setuptools"'; return; }
  echo "null"
}
BUILD_SYSTEM=$(detect_build)

# ── Test Framework Detection ──
detect_test() {
  [ -f "go.mod" ] && { echo '"go test"'; return; }
  [ -d "__tests__" ] || grep -q '"jest"' package.json 2>/dev/null && { echo '"Jest"'; return; }
  grep -q '"vitest"' package.json 2>/dev/null && { echo '"Vitest"'; return; }
  grep -q '"mocha"' package.json 2>/dev/null && { echo '"Mocha"'; return; }
  grep -q 'pytest' requirements.txt 2>/dev/null && { echo '"pytest"'; return; }
  [ -f "Cargo.toml" ] && { echo '"cargo test"'; return; }
  echo "null"
}
TEST_FRAMEWORK=$(detect_test)

# ── File Statistics ──
FILE_COUNT=$(find . -type f \
  -not -path '*/node_modules/*' \
  -not -path '*/vendor/*' \
  -not -path '*/.git/*' \
  -not -path '*/venv/*' \
  -not -path '*/target/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/dist/*' \
  -not -path '*/build/*' \
  -not -path '*/.next/*' \
  -not -path '*.lock' 2>/dev/null | wc -l | tr -d ' ')

# Count files by extension (top 10)
EXT_COUNTS=$(find . -type f \
  -not -path '*/node_modules/*' \
  -not -path '*/vendor/*' \
  -not -path '*/.git/*' \
  -not -path '*/venv/*' \
  -not -path '*/target/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/dist/*' \
  -not -path '*/build/*' \
  -not -path '*/.next/*' 2>/dev/null | \
  sed -n 's/.*\.\([a-zA-Z0-9]\+\)$/\1/p' | \
  sort | uniq -c | sort -rn | head -10 | \
  awk 'BEGIN{printf "{"} {printf "%s\"%s\":%d", (NR>1?",":""), $2, $1} END{printf "}"}')

# Count files in each top-level directory
DIR_COUNTS=$(for dir in */; do
  dirname="${dir%/}"
  count=$(find "$dir" -type f \
    -not -path '*/node_modules/*' \
    -not -path '*/.git/*' 2>/dev/null | wc -l | tr -d ' ')
  echo "$count $dirname"
done | sort -rn | head -15 | \
  awk 'BEGIN{printf "{"} {printf "%s\"%s\":%d", (NR>1?",":""), $2, $1} END{printf "}"}')

# ── Directory Tree (depth 3) ──
DIR_TREE=""
if command -v tree &>/dev/null; then
  DIR_TREE=$(tree -L 3 --dirsfirst -I 'node_modules|vendor|.git|venv|target|__pycache__|dist|build|.next' -a --noreport 2>/dev/null | head -80)
else
  # Fallback: use find-based tree
  DIR_TREE=$(find . -maxdepth 3 -not -path '*/node_modules/*' -not -path '*/vendor/*' -not -path '*/.git/*' \
    -not -path '*/venv/*' -not -path '*/target/*' -not -path '*/.next/*' \
    -type d 2>/dev/null | sort | \
    awk -F/ '{depth=NF-1; for(i=1;i<depth;i++) printf "  "; printf "├── %s\n", $NF}' | head -80)
fi

# Escape for JSON
escape_json() {
  local s="${1//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  echo "$s"
}

DIR_TREE_ESCAPED=$(escape_json "$DIR_TREE")

# ── Assemble JSON Output ──
cat <<EOF
{
  "status": "success",
  "project_name": "$PROJECT_NAME",
  "clone_path": "$CLONE_DIR",
  "clone_depth": "$([ "$DEEP" = true ] && echo 'full' || echo 'shallow')",
  "clone_duration_seconds": $CLONE_DURATION,
  "tech_stack": {
    "primary_language": "$PRIMARY_LANGUAGE",
    "language_breakdown": $LANG_BREAKDOWN,
    "framework": $FRAMEWORK,
    "build_system": $BUILD_SYSTEM,
    "test_framework": $TEST_FRAMEWORK
  },
  "file_stats": {
    "total": $FILE_COUNT,
    "by_extension": $EXT_COUNTS,
    "by_top_directory": $DIR_COUNTS
  },
  "directory_tree": "$DIR_TREE_ESCAPED"
}
EOF
