# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

A Claude Code skill that tutors developers through unfamiliar open-source codebases using a structured 7-phase methodology (0: Git archaeology → 1: Architecture overview → 2: Entry point tracing → 3: Module dependency topology → 4: Data flow tracing → 5: Design patterns → 6: Hands-on practice). Also supports an Academic Mode for paper+code study.

## Architecture

```
SKILL.md              → Skill definition (triggers, phases, teaching flows, state schema)
scripts/*.py / *.sh   → 4 analysis tools (`.py` preferred on Windows; `.sh` for zero-dependency Unix)
references/*.md       → Teaching strategies, pattern catalogs, output templates, gamification
memory/project-mentor/ → Runtime state files (created during sessions, not committed)
```

### Script pipeline (in order of use)

1. **`clone_and_analyze.py`** `<url>` — Shallow clone + tech stack detection + file stats + directory tree
2. **`git_archaeology.py`** `<path>` — Git history analysis: first commit, milestones, growth timeline, recent health
3. **`ast_skeleton.py`** `<path>` — Module skeleton extraction with **large-project aware** output:
   - `project_summary`: aggregate stats across all files
   - `module_summaries`: per-directory aggregation (always covers ALL directories, even on 1000+ file projects)
   - `modules`: per-file details sorted by architectural importance score; may be truncated (check `truncation_notice`)
   - Key flags: `--summaries-only` (lightweight overview), `--max-files N` (default 500, 0=unlimited)
4. **`paper_analyze.py`** `<pdf>` or `--arxiv-id` — Paper metadata, section structure, innovation claims, formula inventory

All `.py` scripts use Python 3 stdlib only (no pip dependencies). All produce JSON on stdout. The `.sh` versions produce identical JSON for Unix environments without Python.

### `ast_skeleton.py` internals

The largest and most complex script. Key pipeline in `main()`:
1. `discover_files()` — finds all source files (no longer has a hard limit)
2. Per-file: detect language → call language-specific `extract_*()` → get imports, functions, classes, interfaces
3. `classify_file()` — assigns `kind` (entry/service/controller/dto/enum/mapper/config/util/test/other) via filename rules → path rules → class-name inference
4. `build_import_map()` — cross-references imports to compute fan-in counts
5. `compute_importance_score()` — entry point +100, fan-in +2/edge, service/controller +30, interface +20, large file +10, root location +20, boilerplate -50
6. Sort by score descending → truncate to `--max-files`
7. `build_module_summaries()` — group by directory, compute per-dir stats and top classes/exports
8. Output JSON with backward-compatible old fields (`status`, `files_analyzed`, `modules` with old keys)

Support 5 languages: Go, Python, TypeScript, Rust, Java, C/C++.

### Runtime files

During a mentoring session, state lives in `memory/project-mentor/`:
- `.mentor-state.json` — current phase, badges, user profile
- `knowledge-base.json` — cross-project knowledge graph
- `{project}/progress.md` and `notes.md` — per-project artifacts

## Common commands

```bash
# Analyze a new project
python scripts/clone_and_analyze.py https://github.com/user/repo
python scripts/git_archaeology.py /tmp/project-mentor-test/repo
python scripts/ast_skeleton.py /tmp/project-mentor-test/repo

# Large project: lightweight directory overview
python scripts/ast_skeleton.py /tmp/project-mentor-test/repo --summaries-only

# Control detail depth
python scripts/ast_skeleton.py /tmp/project-mentor-test/repo --max-files 100

# Paper analysis
python scripts/paper_analyze.py --arxiv-id 1706.03762

# Test files are skipped by default; to include them:
python scripts/ast_skeleton.py <path> --no-skip-tests

# Validate JSON output of any script
python scripts/ast_skeleton.py <path> | python -m json.tool > /dev/null
```

## Permission requirements

This skill needs broad Bash/Read/Write permissions to function without constant prompts. The project ships with `references/permission-setup.md` (3 tiers) and `.claude/settings.local.json` (project-scoped allowlist). Future instances should check that permissions are configured before starting a session.
