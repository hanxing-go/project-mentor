# Git Archaeology Methodology

## Core Principles

Git history is the most underused teaching tool in open-source education. Every project's commit log tells a story: the author's initial spark, the features that mattered most, the pivots, the architectural decisions made under pressure, the bugs fixed at 2am.

Reading a project without its Git history is like studying a finished building without seeing its construction photos. You can understand the final structure, but you miss WHY each wall was placed where it is.

This document defines the methodology for extracting that story.

### The "Project Biography" Metaphor

- **First commit** = Birth — What was the minimal kernel of the idea?
- **Milestone commits** = Life events — Graduation (v1.0), new job (major refactor), moving cities (platform migration)
- **Recent activity** = Current health — Is this project alive? Active? In maintenance mode?
- **Growth curve** = Coming of age — How fast did it grow? Was it steady or explosive?

---

## Step 1: First Commit Analysis

### Commands

```bash
# Find the very first commit (chronologically)
git log --reverse --format="%H|%ai|%an|%s" | head -1

# Get details on the first commit
git show --stat $(git rev-list --max-parents=0 HEAD)

# Count files and lines in the first commit
git show --format="" --name-only $(git rev-list --max-parents=0 HEAD) | wc -l
git diff --stat $(git rev-list --max-parents=0 HEAD) HEAD | tail -1
```

### What to Extract

- **Date:** When did the project start?
- **Author:** Who started it?
- **Commit message:** What did the author say they were doing?
- **Files changed:** How many files were in that first commit?
- **Lines added:** How much code was it?
- **File contents (brief):** What was the project at its simplest?

### Narrative Framing

Turn these facts into a story:

> "On {{DATE}}, {{AUTHOR}} wrote the first {{LINES}} lines of {{PROJECT}}. The commit message was '{{MESSAGE}}'. At this point, the project was {{DESCRIPTION_OF_WHAT_EXISTED}}. Everything else — all {{CURRENT_FILES}} files — grew from this seed."

---

## Step 2: Milestone Detection

### Method A: Directory Birth Detection

```bash
# For each top-level directory, find the first commit that touched it
for dir in $(ls -d */ | head -20); do
  echo "=== $dir ==="
  git log --reverse --format="%ai %s" -- "$dir" | head -1
done
```

A new top-level directory signals a new subsystem. `coordinator/` appearing = multi-agent was added. `plugins/` appearing = extension system was added.

### Method B: Tag-Based Detection

```bash
# List all tags with dates
git tag --sort=creatordate --format="%(creatordate:short)|%(refname:short)"
```

Tags often mark releases. Especially look for major version bumps (v1.0, v2.0) and release candidates.

### Method C: README Changelog Parsing

Some projects maintain a CHANGELOG.md. Extract it:
```bash
# If CHANGELOG.md exists, extract its contents
git show HEAD:CHANGELOG.md 2>/dev/null | head -100
```

### Method D: File-Count Inflection Points

```bash
# Track file count growth by month
git log --reverse --format="%ai" | cut -d'-' -f1,2 | uniq -c | \
  while read count month; do echo "$month $count"; done
```

Look for months where the commit rate or file growth rate spikes — these are likely milestone moments (new feature, major refactor, post-launch bug-fix frenzy).

### Heuristic Ranking and Deduplication

Combine the four methods, then rank milestones by:
1. **Structural impact:** New top-level directory > new file in existing dir > tag
2. **Semantic signal:** Has a tag AND a new directory AND README mention → high confidence
3. **Temporal uniqueness:** Only one milestone per calendar month (dedup)

---

## Step 3: Growth Timeline Construction

### Data Aggregation

```bash
# Per-month commit count
git log --reverse --format="%ai" | cut -d'-' -f1,2 | sort | uniq -c

# Per-month contributor count
git log --reverse --format="%ai|%an" | cut -d'-' -f1,2 | sort -u | cut -d'|' -f1,2 | cut -d'-' -f1,2 | sort | uniq -c

# File count over time (expensive — sample at milestones only)
for commit in $(git log --reverse --format="%H" | awk 'NR % 50 == 0'); do
  echo "$(git show -s --format="%ai" $commit)|$(git ls-files $commit 2>/dev/null | wc -l)"
done
```

### Timeline Format

Output each milestone as a timeline entry:

```
🎂 {{DATE}} — Birth: {{LINES}} lines, {{FILES}} files — "{{FIRST_MESSAGE}}"
🚀 {{DATE}} — {{MILESTONE_NAME}}: {{WHAT_CHANGED}} — {{SIGNIFICANCE}}
🧩 {{DATE}} — {{MILESTONE_NAME}}: {{WHAT_CHANGED}} — {{SIGNIFICANCE}}
...
📦 {{DATE}} — Present: {{CURRENT_FILES}} files, {{CURRENT_LOC}} lines
```

### ASCII Timeline Visualization

```
🎂 Mar 2024     🚀 Jun 2024       🧩 Sep 2024        🤝 Jan 2025
200 lines ───▶ QueryEngine ───▶ BashTool/ReadTool ───▶ coordinator/
CLI shell       LLM对话能力        操作文件系统         并行Agent
```

---

## Step 4: Recent Activity Analysis

### Commands

```bash
# Last 90 days of commit activity
git log --after="90 days ago" --format="%ai|%an|%s" | head -50

# Commit frequency (commits per week for last 90 days)
git log --after="90 days ago" --format="%ai" | cut -d'-' -f1,2 | sort | uniq -c

# Active branches
git branch -r --sort=-committerdate | head -10

# Top recent contributors
git shortlog -sn --after="90 days ago" | head -10
```

### What This Tells Us

- **High commit frequency with varied authors** = Active community, healthy project
- **Single author, weekly commits** = Maintained but solo project
- **No commits in 3+ months** = Possibly dormant (warn the user: "This project may be unmaintained")
- **Only dependency-bump commits** = Maintenance mode, stable project
- **Frequent force-pushes to main** = Active but possibly unstable development

### Narrative Framing

> "In the last 90 days, this project has seen {{COMMIT_COUNT}} commits from {{CONTRIBUTOR_COUNT}} contributors. The most active area is {{MOST_CHANGED_DIR}}. This tells us the project is {{HEALTH_ASSESSMENT}}."

---

## Edge Cases & Fallbacks

### Shallow Clones (--depth=1)

**Detection:** `git log --oneline | wc -l` returns 1
**Fallback:** Cannot do archaeology. Report: "This project was cloned with --depth=1, so I can't see its history. If you want the full archaeology experience, re-clone without the depth limit."

### Squashed Histories

**Detection:** `git log --oneline | wc -l` is very small relative to project age
**Fallback:** Work with what's available. The squashed history still shows merge events and PR numbers. Focus on the merge commit messages rather than individual commits.

### Monorepos

**Detection:** The repo URL has subdirectories with their own build systems
**Fallback:** Scope git analysis to the relevant subdirectory: `git log -- <subdirectory>`

### Repos With No Tags

**Fallback:** Use only directory-birth detection and commit frequency inflection points. Skip tag-based milestone detection entirely.

### First Commit is a "Mega-Commit"

**Detection:** First commit has 5000+ lines
**Fallback:** Report: "The author imported a lot of code in their first commit ({{LINES}} lines), so the 'birth' isn't a clean starting point. The first commit is more of an 'arrival' than a 'birth'."

---

## Output Format Specification

The `git_archaeology.sh` script outputs JSON. Key fields consumed by the skill:

```json
{
  "status": "success|partial|error",
  "first_commit": {
    "hash": "abc123",
    "date": "2024-03-15",
    "author": "Author Name",
    "message": "Initial commit",
    "files_changed": 12,
    "lines_added": 200
  },
  "milestones": [
    {
      "hash": "def456",
      "date": "2024-06-01",
      "description": "Added QueryEngine",
      "significance": "Introduced LLM conversation capability",
      "detected_by": "directory_birth"
    }
  ],
  "recent_activity": {
    "days_analyzed": 90,
    "commit_count": 45,
    "active_branches": ["main", "develop"],
    "top_contributors": [{"name": "...", "commits": 20}]
  },
  "growth_timeline": [
    {"date": "2024-03", "total_commits": 5, "total_files": 12, "total_contributors": 1}
  ],
  "narrative_summary": "Human-readable paragraph summarizing the project's history"
}
```
