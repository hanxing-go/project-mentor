# Permission Whitelist Configuration Guide

## The Problem: CLI Confirmation Hell

When a Claude Code Skill tutors a beginner through a large codebase, the agent needs to: read files, search for patterns, run analysis scripts, and occasionally clone repos. Without pre-configured permissions, each of these actions triggers a confirmation prompt. For a 7-phase tutoring session spanning dozens of operations, the user gets interrupted every 2-3 minutes.

This kills flow. The solution is a targeted allowlist configured BEFORE the tutoring session begins.

---

## Solution: Targeted Allowlisting

Permissions are configured in `.claude/settings.local.json` (project-scoped, committed) or `~/.claude/settings.json` (user-global). The project-mentor skill uses **project-scoped** permissions by default.

### Where to Apply

Add the permissions under `.claude/settings.local.json` in the project-mentor directory:

```json
{
  "permissions": {
    "allow": [
      "..."
    ]
  }
}
```

---

## Tier 1: Minimal (Most Restrictive)

For users who want maximum control. Only allows read-only operations + the 4 project-mentor scripts.

```
Read
Glob
Grep
WebSearch
WebFetch(allowedDomains:["github.com","arxiv.org"])
Bash(clone_and_analyze.sh)
Bash(git_archaeology.sh)
Bash(ast_skeleton.sh)
Bash(paper_analyze.sh)
```

**What gets blocked:** Any Bash command not in the 4 scripts. If the skill needs to run an ad-hoc `git` or `find` command, the user must approve it.

**Best for:** Security-conscious users, enterprise environments.

---

## Tier 2: Standard (Recommended)

Adds read-only git operations and common file discovery commands that the skill may need during exploration phases.

```
Read
Write(memory/project-mentor/**)
Glob
Grep
WebSearch
WebFetch(allowedDomains:["github.com","arxiv.org","pypi.org","docs.rs","pkg.go.dev"])
Bash(clone:*)
Bash(git:*)
Bash(find:*)
Bash(wc:*)
Bash(tree:*)
Bash(python3:*)
```

**What gets blocked:** Destructive operations (`git push`, `rm`, `mv`), arbitrary package installation, network calls beyond allowed domains.

**Best for:** Most users. Provides smooth flow without risky operations.

---

## Tier 3: Permissive (For Experienced Users)

Adds broader Bash access, including package installation for tool dependencies.

```
Read
Write(memory/project-mentor/**)
Glob
Grep
WebSearch
WebFetch
Bash
```

**What gets blocked:** Effectively nothing in the Bash namespace. The WebFetch unrestricted allows any URL.

**Best for:** Users who trust the agent fully and want zero interruptions. Power users who can audit agent actions.

---

## How to Apply

### Step 1: Open the settings file

The project-mentor skill comes with a `.claude/settings.local.json` in its directory. If it doesn't exist yet:

```bash
touch .claude/settings.local.json
```

### Step 2: Add the permissions block

Start with Tier 2 (Standard). Copy the permission list into the file:

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Write(memory/project-mentor/**)",
      "Glob",
      "Grep",
      "WebSearch",
      "WebFetch(allowedDomains:[\"github.com\",\"arxiv.org\",\"pypi.org\",\"docs.rs\",\"pkg.go.dev\"])",
      "Bash(clone:*)",
      "Bash(git:*)",
      "Bash(find:*)",
      "Bash(wc:*)",
      "Bash(tree:*)",
      "Bash(python3:*)"
    ]
  }
}
```

### Step 3: Verify the configuration

Run a quick test:

```
# In Claude Code, try:
> Run: git log --oneline -5
```

If no permission prompt appears, the allowlist is active.

---

## Dependency Installation

The skill requires certain tools. Install them before starting:

**Required:**
- `git` — present on most systems
- `bash` — present on most systems

**Optional but recommended:**
- `tree-sitter` — for AST skeleton extraction (fallback regex works without it)
- `python3` + `pdfplumber` — for paper analysis mode only
- `tree` — for directory visualization

Install tree-sitter (for AST mode):
```bash
npm install -g tree-sitter-cli
# or
cargo install tree-sitter-cli
```

Install pdfplumber (for paper mode):
```bash
pip install pdfplumber
```

---

## Security Considerations

- **Why not just allow all Bash?** Arbitrary Bash access means the agent could run `rm -rf`, `curl | bash`, or modify files outside the workspace. For teaching purposes, we don't need that.
- **Why Git is safe:** Read-only Git operations (`log`, `show`, `diff`, `status`) don't modify state. Cloning is the only write operation and should be explicitly allowed.
- **Why Write is scoped:** The skill only writes to `memory/project-mentor/` for notes and state. Scoping the Write permission prevents accidental modification of project files during analysis.
- **WebFetch domain restriction:** Restricting to github.com and arxiv.org prevents the agent from fetching arbitrary URLs, reducing data exfiltration risk.
