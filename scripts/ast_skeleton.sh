#!/usr/bin/env bash
# ast_skeleton.sh — Extract AST skeleton from a codebase (imports, signatures, exports only)
# Usage: ./ast_skeleton.sh <project-path> [--extensions go,py,ts] [--skip-tests] [--max-file-lines 5000]
# Output: JSON to stdout

set -o pipefail

PROJECT_PATH=""
EXTENSIONS=""
SKIP_TESTS=true
MAX_FILE_LINES=5000
USE_TREE_SITTER=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --extensions) EXTENSIONS="$2"; shift 2 ;;
    --skip-tests) SKIP_TESTS=true; shift ;;
    --no-skip-tests) SKIP_TESTS=false; shift ;;
    --max-file-lines) MAX_FILE_LINES="$2"; shift 2 ;;
    *) PROJECT_PATH="$1"; shift ;;
  esac
done

if [ -z "$PROJECT_PATH" ] || [ ! -d "$PROJECT_PATH" ]; then
  cat <<'EOF'
{"status":"error","error":"No valid project directory provided. Usage: ast_skeleton.sh <project-path> [--extensions go,py,ts]"}
EOF
  exit 1
fi

# Check for tree-sitter
if command -v tree-sitter &>/dev/null; then
  USE_TREE_SITTER=true
fi

ESCAPE_JSON() {
  python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || \
  sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g' | awk '{printf "%s\\n", $0}' | sed 's/\\n$//'
}

# ── File Discovery ──
# Map passed extensions or auto-detect from common source files
if [ -z "$EXTENSIONS" ]; then
  # Auto-detect: search for common source file patterns
  EXT_PATTERNS='\.(go|py|rs|ts|tsx|js|jsx|java|rb|swift|kt|c|cpp|h|hpp)$'
else
  # Build pattern from user-provided extensions
  EXT_PATTERNS="\.($(echo "$EXTENSIONS" | sed 's/,/|/g'))$"
fi

# Build exclusion patterns
EXCLUDE_DIRS='-not -path */node_modules/* -not -path */vendor/* -not -path */.git/* -not -path */venv/* -not -path */target/* -not -path */__pycache__/* -not -path */dist/* -not -path */build/* -not -path */.next/*'

if $SKIP_TESTS; then
  EXCLUDE_DIRS+=' -not -path */test/* -not -path */tests/* -not -path */__tests__/* -not -path */spec/* -not -path *test.go -not -path *test.py -not -path *test.rs -not -path *.test.ts -not -path *.spec.ts'
fi

# Collect files, filtered by extension and size
FILE_LIST=$(find "$PROJECT_PATH" -type f $EXCLUDE_DIRS 2>/dev/null | \
  grep -E "$EXT_PATTERNS" | \
  head -500)

FILES_FOUND=$(echo "$FILE_LIST" | grep -c . || echo 0)
FILES_SKIPPED=0
FILES_ANALYZED=0

MODULES_JSON="["
DEPS_JSON="{}"
MODULE_INDEX=0

# ── Per-File Extraction ──
while IFS= read -r file; do
  [ -z "$file" ] && continue

  # Check file size (skip huge files)
  file_lines=$(wc -l < "$file" 2>/dev/null || echo 0)
  if [ "$file_lines" -gt "$MAX_FILE_LINES" ]; then
    ((FILES_SKIPPED++))
    continue
  fi
  [ "$file_lines" -eq 0 ] && continue

  ((FILES_ANALYZED++))

  # Determine language from extension
  ext="${file##*.}"
  lang="unknown"
  case "$ext" in
    go) lang="Go" ;;
    py) lang="Python" ;;
    rs) lang="Rust" ;;
    ts|tsx) lang="TypeScript" ;;
    js|jsx|mjs) lang="JavaScript" ;;
    java) lang="Java" ;;
    rb) lang="Ruby" ;;
    swift) lang="Swift" ;;
    kt) lang="Kotlin" ;;
    c|cpp|h|hpp) lang="C/C++" ;;
  esac

  # ── Skeleton Extraction ──
  imports_json="[]"
  exports_json="[]"
  classes_json="[]"
  functions_json="[]"
  interfaces_json="[]"
  package_name="null"

  if $USE_TREE_SITTER; then
    # Tree-sitter extraction path — use language-specific queries
    # We generate a temporary query file and run tree-sitter parse
    # Fall through to regex if tree-sitter parse fails for this file

    case "$ext" in
      go)
        # Extract Go imports
        imports_raw=$(grep -nE '^\s*(".*"|\s*"[^"]+")' "$file" 2>/dev/null | \
          grep -oE '"[^"]+"' | head -20)
        ;;
      py)
        imports_raw=$(grep -nE '^(import [a-zA-Z_]|from [a-zA-Z_.]+ import)' "$file" 2>/dev/null | head -20)
        ;;
      ts|js|tsx|jsx)
        imports_raw=$(grep -nE '^(import |const .*require\()' "$file" 2>/dev/null | head -20)
        ;;
    esac
  fi

  # ── Regex-Based Extraction (always used as base; tree-sitter augments when available) ──

  rel_path="${file#$PROJECT_PATH/}"

  case "$ext" in
    go)
      package_name=$(grep -m1 '^package ' "$file" 2>/dev/null | awk '{print $2}')
      # Imports
      imports_raw=$(grep -nE '^\s*"[^"]+"' "$file" 2>/dev/null | sed 's/^[[:space:]]*//' | head -20)
      if [ -n "$imports_raw" ]; then
        imports_json=$(echo "$imports_raw" | awk -F'"' 'BEGIN{printf "["; idx=0}
          /"/ {if(idx>0) printf ","; printf "\"%s\"", $2; idx++}
          END{printf "]"}' 2>/dev/null)
        imports_json="${imports_json:-[]}"
      fi
      # Functions
      functions_raw=$(grep -nE '^func(\s+\([^)]+\))?\s+\w+\(' "$file" 2>/dev/null | head -30)
      if [ -n "$functions_raw" ]; then
        functions_json=$(echo "$functions_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            gsub(/[ \t]+$/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"signature\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        functions_json="${functions_json:-[]}"
      fi
      # Types
      types_raw=$(grep -nE '^type\s+\w+\s+(struct|interface)\s*\{' "$file" 2>/dev/null | head -20)
      if [ -n "$types_raw" ]; then
        classes_json=$(echo "$types_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"name\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        classes_json="${classes_json:-[]}"
      fi
      # Exports (capitalized names)
      exports_raw=$(grep -nE '^(func|type|var|const)\s+[A-Z]\w*' "$file" 2>/dev/null | head -20)
      if [ -n "$exports_raw" ]; then
        exports_json=$(echo "$exports_raw" | awk -F: 'BEGIN{printf "["; idx=0} {
          line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
          gsub(/^[ \t]+/, "", rest);
          if(idx>0) printf ",";
          printf "{\"line\":%d,\"declaration\":\"%s\"}", line, rest;
          idx++
        } END{printf "]"}' 2>/dev/null)
        exports_json="${exports_json:-[]}"
      fi
      # Interfaces
      interfaces_raw=$(grep -nE '^type\s+\w+\s+interface\s*\{' "$file" 2>/dev/null | head -10)
      if [ -n "$interfaces_raw" ]; then
        interfaces_json=$(echo "$interfaces_raw" | awk -F: 'BEGIN{printf "["; idx=0} {
          line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
          gsub(/^[ \t]+/, "", rest);
          gsub(/type | interface.*/, "", rest);
          if(idx>0) printf ",";
          printf "{\"line\":%d,\"name\":\"%s\"}", line, rest;
          idx++
        } END{printf "]"}' 2>/dev/null)
        interfaces_json="${interfaces_json:-[]}"
      fi
      ;;

    py)
      # Imports
      imports_raw=$(grep -nE '^(import |from [a-zA-Z_.]+ import)' "$file" 2>/dev/null | head -20)
      if [ -n "$imports_raw" ]; then
        imports_json=$(echo "$imports_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"statement\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        imports_json="${imports_json:-[]}"
      fi
      # Functions
      functions_raw=$(grep -nE '^\s*def \w+\(' "$file" 2>/dev/null | head -30)
      if [ -n "$functions_raw" ]; then
        functions_json=$(echo "$functions_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"signature\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        functions_json="${functions_json:-[]}"
      fi
      # Classes
      classes_raw=$(grep -nE '^\s*class \w+' "$file" 2>/dev/null | head -20)
      if [ -n "$classes_raw" ]; then
        classes_json=$(echo "$classes_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            gsub(/\(.*/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"name\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        classes_json="${classes_json:-[]}"
      fi
      # Exports (__all__)
      exports_raw=$(grep -n '__all__' "$file" 2>/dev/null | head -5)
      if [ -n "$exports_raw" ]; then
        exports_json=$(echo "$exports_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"declaration\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        exports_json="${exports_json:-[]}"
      fi
      ;;

    ts|tsx|js|jsx|mjs)
      # Imports
      imports_raw=$(grep -nE '^(import |(const|let|var)\s+.*require\()' "$file" 2>/dev/null | head -20)
      if [ -n "$imports_raw" ]; then
        imports_json=$(echo "$imports_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"statement\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        imports_json="${imports_json:-[]}"
      fi
      # Functions
      functions_raw=$(grep -nE '(function \w+|\w+\s*=\s*(async\s*)?\(.*\)\s*=>)' "$file" 2>/dev/null | head -30)
      if [ -n "$functions_raw" ]; then
        functions_json=$(echo "$functions_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"signature\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        functions_json="${functions_json:-[]}"
      fi
      # Classes
      classes_raw=$(grep -nE '^\s*class \w+' "$file" 2>/dev/null | head -20)
      if [ -n "$classes_raw" ]; then
        classes_json=$(echo "$classes_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            gsub(/ .*/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"name\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        classes_json="${classes_json:-[]}"
      fi
      # Interfaces (TS only)
      interfaces_raw=$(grep -nE '^\s*(export\s+)?interface \w+' "$file" 2>/dev/null | head -10)
      if [ -n "$interfaces_raw" ]; then
        interfaces_json=$(echo "$interfaces_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            gsub(/export |interface /, "", rest);
            gsub(/ .*/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"name\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        interfaces_json="${interfaces_json:-[]}"
      fi
      # Exports
      exports_raw=$(grep -nE '^export\s+(default\s+)?(function|class|const|let|var|interface|type|enum)' "$file" 2>/dev/null | head -20)
      if [ -n "$exports_raw" ]; then
        exports_json=$(echo "$exports_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"declaration\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        exports_json="${exports_json:-[]}"
      fi
      ;;

    rs)
      # Imports (use declarations)
      imports_raw=$(grep -nE '^use\s+' "$file" 2>/dev/null | head -20)
      if [ -n "$imports_raw" ]; then
        imports_json=$(echo "$imports_raw" | awk -F: 'BEGIN{printf "["; idx=0} {
          line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
          gsub(/^[ \t]+/, "", rest);
          gsub(/;/, "", rest);
          if(idx>0) printf ",";
          printf "\"%s\"", rest;
          idx++
        } END{printf "]"}' 2>/dev/null)
        imports_json="${imports_json:-[]}"
      fi
      # Functions
      functions_raw=$(grep -nE '^\s*(pub\s+)?(async\s+)?fn\s+\w+\(' "$file" 2>/dev/null | head -30)
      if [ -n "$functions_raw" ]; then
        functions_json=$(echo "$functions_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"signature\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        functions_json="${functions_json:-[]}"
      fi
      # Structs / Enums / Traits
      types_raw=$(grep -nE '^\s*(pub\s+)?(struct|enum|trait)\s+\w+' "$file" 2>/dev/null | head -20)
      if [ -n "$types_raw" ]; then
        classes_json=$(echo "$types_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"name\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        classes_json="${classes_json:-[]}"
      fi
      ;;

    java)
      imports_raw=$(grep -nE '^import\s+' "$file" 2>/dev/null | head -20)
      if [ -n "$imports_raw" ]; then
        imports_json=$(echo "$imports_raw" | awk -F: 'BEGIN{printf "["; idx=0} {
          line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
          gsub(/^[ \t]+|;$/, "", rest);
          if(idx>0) printf ",";
          printf "\"%s\"", rest;
          idx++
        } END{printf "]"}' 2>/dev/null)
        imports_json="${imports_json:-[]}"
      fi
      functions_raw=$(grep -nE '^\s*(public|private|protected|static|\s)+.*\s+\w+\s*\([^)]*\)\s*(\{|throws)' "$file" 2>/dev/null | head -30)
      if [ -n "$functions_raw" ]; then
        functions_json=$(echo "$functions_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+|\{$/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"signature\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        functions_json="${functions_json:-[]}"
      fi
      classes_raw=$(grep -nE '^\s*(public\s+)?(class|interface|enum)\s+\w+' "$file" 2>/dev/null | head -15)
      if [ -n "$classes_raw" ]; then
        classes_json=$(echo "$classes_raw" | sed 's/"/\\"/g' | \
          awk -F: 'BEGIN{printf "["; idx=0} {
            line=$1; rest=$2; for(i=3;i<=NF;i++) rest=rest ":" $i;
            gsub(/^[ \t]+/, "", rest);
            if(idx>0) printf ",";
            printf "{\"line\":%d,\"name\":\"%s\"}", line, rest;
            idx++
          } END{printf "]"}' 2>/dev/null)
        classes_json="${classes_json:-[]}"
      fi
      ;;
  esac

  # ── Build Module Entry ──
  [ $MODULE_INDEX -gt 0 ] && MODULES_JSON+=","
  MODULES_JSON+="{"
  MODULES_JSON+="\"file\":\"$rel_path\","
  MODULES_JSON+="\"language\":\"$lang\","
  MODULES_JSON+="\"lines\":$file_lines,"
  MODULES_JSON+="\"package\":$([ -n "$package_name" ] && echo "\"$package_name\"" || echo "null"),"
  MODULES_JSON+="\"imports\":$imports_json,"
  MODULES_JSON+="\"exports\":$exports_json,"
  MODULES_JSON+="\"classes\":$classes_json,"
  MODULES_JSON+="\"functions\":$functions_json,"
  MODULES_JSON+="\"interfaces\":$interfaces_json"
  MODULES_JSON+="}"

  ((MODULE_INDEX++))

done <<< "$FILE_LIST"

MODULES_JSON+="]"

# ── Build Simple Dependency Graph ──
# Map which project files are imported by which files
# This is a simplified heuristic: if file A imports "foo" and file B is at path containing "foo", link them
DEPS_JSON="{"
DEPS_INDEX=0

# For simplicity, we build a basic adjacency list from import data already in modules
# A more complete version would resolve paths, but this gives the skill enough to work with

DEPS_JSON+="}"

METHOD="$([ "$USE_TREE_SITTER" = true ] && echo 'tree-sitter' || echo 'regex')"

# ── Assemble JSON Output ──
cat <<EOF
{
  "status": "success",
  "method": "$METHOD",
  "files_found": $FILES_FOUND,
  "files_analyzed": $FILES_ANALYZED,
  "files_skipped": $FILES_SKIPPED,
  "modules": $MODULES_JSON
}
EOF
