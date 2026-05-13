# AST Pruning Strategy & Two-Stage Loading

## Why Two-Stage Loading?

A mid-size open-source project has ~500-2000 files. Loading every file in full would consume 100K-500K tokens before the skill even begins teaching. This causes three problems:

1. **Token explosion:** Claude's context fills up with implementation details, leaving no room for teaching
2. **Model attention dilution:** When every line is visible, no line stands out. The model can't distinguish signal from noise.
3. **Extraction errors:** LLMs hallucinate summaries when asked to compress too much code at once

**Solution:** Two-stage loading. Phases 0-4 use AST skeletons (30-50 lines per 500-line file). Only Phase 5 loads full code — and only for 2-3 files.

### Token Budget

| Phase | Strategy | Typical Token Cost |
|-------|----------|-------------------|
| 0 | Git metadata only (no code) | ~1K |
| 1 | Directory tree + AST overview | ~2K-3K |
| 2 | Entry file full, rest skeleton | ~2K-3K |
| 3 | All modules as skeleton | ~3K-5K |
| 4 | Traceroute files full, rest skeleton | ~3K-5K |
| 5 | 2-3 files full code | ~3K-8K |
| 6 | No code loading (user writes code) | ~1K |
| **Total** | | **~15K-30K** |

Compared to full-code loading for a 500-file project: ~250K+. Two-stage loading saves ~90% of the context budget.

---

## Stage A: Skeleton Extraction (Phases 0-4)

### What We Keep

| Element | Extract | Reason |
|---------|---------|--------|
| `import` / `require` / `use` statements | ✅ | Shows dependency graph — which files talk to which files |
| `class` / `interface` / `struct` definitions | ✅ | Shows type hierarchy and module structure |
| Function / method signatures | ✅ | Shows what each module is capable of (API surface) |
| `export` / `public` declarations | ✅ | Shows what's part of the public API vs. internal |
| `package` / `module` declarations | ✅ | Shows code organization |
| Generic / type parameters | ✅ | Shows type constraints (important for Rust/TypeScript/Go generics) |

### What We Prune

| Element | Extract | Reason |
|---------|---------|--------|
| Function bodies (code inside `{}`) | ❌ | Implementation detail, not needed for structure understanding |
| Local variable declarations | ❌ | Ephemeral and noisy |
| Comments and docstrings | ❌ | Valuable but bulky; read on-demand |
| String literals | ❌ | Rarely structurally meaningful |
| Test files (by default) | ❌ | Tests duplicate production structure; skip unless user asks |
| Generated code | ❌ | Not authored, not meaningful for learning |
| `node_modules` / `vendor` / `venv` / `target/` | ❌ | External dependencies, not project code |

### Skip Directories (Default Exclusions)

```
node_modules/, vendor/, venv/, .venv/, __pycache__/, target/, build/,
dist/, .git/, .next/, .nuxt/, .cache/, coverage/, *.egg-info/
```

---

## Language-Specific Extraction Rules

### Go

```scheme
; tree-sitter query
(function_declaration
  name: (identifier) @function.name
  parameters: (parameter_list) @function.params
  result: (type_identifier)? @function.return) @function.def

(method_declaration
  receiver: (parameter_list) @method.receiver
  name: (field_identifier) @method.name
  parameters: (parameter_list) @method.params
  result: (type_identifier)? @method.return) @method.def

(type_declaration
  (type_spec
    name: (type_identifier) @type.name
    type: (struct_type) @type.struct)) @type.def

(import_declaration
  (import_spec
    path: (interpreted_string_literal) @import.path)) @import.def
```

**Regex fallback:**
```bash
# Imports
grep -nE '^\s*import \(|^\s*".+"' "$file"

# Functions
grep -nE '^func\s+(\(.*\)\s+)?\w+\(' "$file"

# Type definitions
grep -nE '^type\s+\w+\s+(struct|interface)' "$file"

# Exports (capitalized names)
grep -nE '^(func|type|var|const)\s+[A-Z]\w*' "$file"
```

### Python

```scheme
(function_definition
  name: (identifier) @func.name
  parameters: (parameters) @func.params
  return_type: (type)? @func.return) @func.def

(class_definition
  name: (identifier) @class.name
  superclasses: (argument_list)? @class.bases) @class.def

(import_statement) @import.def
(import_from_statement) @import.from
```

**Regex fallback:**
```bash
# Imports
grep -nE '^(import |from )' "$file"

# Functions
grep -nE '^\s*def \w+\(' "$file"

# Classes
grep -nE '^\s*class \w+' "$file"

# Decorated functions (2-line pattern)
grep -nE '^@\w+|^\s*def \w+\(' "$file"
```

### TypeScript / JavaScript

```scheme
(function_declaration
  name: (identifier) @func.name
  parameters: (formal_parameters) @func.params
  return_type: (type_annotation)? @func.return) @func.def

(arrow_function) @arrow.def  ; Only named ones via variable_declarator

(class_declaration
  name: (identifier) @class.name) @class.def

(interface_declaration
  name: (identifier) @interface.name) @interface.def

(import_statement) @import.def
(export_statement) @export.def
```

**Regex fallback:**
```bash
# Imports
grep -nE '^(import |const.*require)' "$file"

# Functions
grep -nE '(function \w+|=>\s*\{)' "$file"

# Classes
grep -nE '^\s*class \w+' "$file"

# Exports
grep -nE '^export\s+(default\s+)?(function|class|const|let|var)' "$file"
```

### Rust

```scheme
(function_item
  name: (identifier) @func.name
  parameters: (parameters) @func.params
  return_type: (type)? @func.return) @func.def

(struct_item
  name: (type_identifier) @struct.name) @struct.def

(impl_item
  type: (type_identifier) @impl.type
  trait: (type_identifier)? @impl.trait) @impl.def

(use_declaration) @use.def
(mod_item) @mod.def
```

**Regex fallback:**
```bash
# Use declarations
grep -nE '^use\s+' "$file"

# Functions (simplified — Rust fn syntax is regular)
grep -nE '^\s*(pub\s+)?(async\s+)?fn\s+\w+\(' "$file"

# Structs and enums
grep -nE '^\s*(pub\s+)?(struct|enum|trait)\s+\w+' "$file"
```

---

## Multi-Language Project Handling

When a project contains multiple languages:

1. Run AST extraction for each language independently
2. Mark each module with its detected language
3. For dependency graph: only link within the same language (Go imports don't import Python files)
4. Display language breakdown to the user: "This project is 70% Go, 20% TypeScript (frontend), 10% Shell scripts"

---

## Fallback: Regex-Based Extraction (No tree-sitter)

When `tree-sitter` is not installed:

1. Detect language by file extension
2. Apply the regex patterns defined above for that language
3. Mark the extraction method as `"method": "regex"` in the output JSON
4. Add a note: "tree-sitter not available — using regex-based extraction. For better accuracy, install tree-sitter: `npm install -g tree-sitter-cli`"
5. Warn the user: "The module structure I'm showing is regex-extracted and may miss some patterns. For a more accurate analysis, I'd recommend installing tree-sitter."

---

## Stage B: Full Loading (Phase 5 Only)

### File Selection Criteria

Choose 2-3 files that:
1. **Are architecturally central** — the most-imported module, the brain of the system
2. **Contain design patterns** — likely candidates for teaching
3. **Are manageable in size** — 50-300 lines each (skip behemoth files)

### How to Identify the Best Candidates

1. From the AST skeleton dependency graph, find the most-imported module
2. From the Phase 4 data flow trace, identify the files hit most often
3. From `git_archaeology.sh` output, look for files with many milestone commits
4. Prioritize non-generated, hand-written source files

### Token Budget Management

```
Maximum per file: 300 lines (~2K-3K tokens)
Maximum total: 3 files (~6K-9K tokens)
```

If a file is larger than 300 lines, read the most relevant section (identified from data flow trace) plus the file's top-level declarations.

---

## Summary: Loading Strategy by Phase

| Phase | What to Load | From Where |
|-------|-------------|-----------|
| 0 | Nothing (git metadata only) | `git_archaeology.sh` stdout |
| 1 | Directory tree + skeleton of all top-level modules | `clone_and_analyze.sh` + `ast_skeleton.sh` |
| 2 | Entry file FULL + skeleton of imported modules | Read tool + `ast_skeleton.sh` |
| 3 | All non-test modules as skeleton | `ast_skeleton.sh` |
| 4 | Data flow files FULL (targeted) + skeleton of rest | Read tool + `ast_skeleton.sh` |
| 5 | 2-3 files FULL | Read tool |
| 6 | Nothing (user writes code) | — |
