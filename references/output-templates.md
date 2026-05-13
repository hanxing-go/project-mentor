# Output Templates

Templates use `{{PLACEHOLDER}}` syntax. The skill fills these in at runtime.

---

## Phase Notes Templates

### Phase 0: Git Archaeology

```markdown
## ⏳ Phase 0: Git Archaeology — Project Growth Timeline

### 🎂 The First Commit

**Date:** {{FIRST_COMMIT_DATE}}
**Author:** {{FIRST_COMMIT_AUTHOR}}
**Message:** {{FIRST_COMMIT_MESSAGE}}

The project started with **{{FIRST_COMMIT_FILES}} files** and **{{FIRST_COMMIT_LINES}} lines of code**.

{{FIRST_COMMIT_NARRATIVE}}

### 📈 Growth Timeline

{{GROWTH_TIMELINE}}

### 🏔️ Key Milestones

| Date | Event | Significance |
|------|-------|-------------|
{{MILESTONE_ROWS}}

### 📊 Project Stats

- **Total commits:** {{TOTAL_COMMITS}}
- **Contributors:** {{CONTRIBUTOR_COUNT}}
- **Active branches:** {{ACTIVE_BRANCHES}}
- **Recent activity ({{RECENT_DAYS}} days):** {{RECENT_COMMITS}} commits

### 💡 What This Means For You

{{NARRATIVE_SUMMARY}}
```

### Phase 1: Reconnaissance

```markdown
## 🔭 Phase 1: Reconnaissance — Project Card & Architecture Overview

### 📇 Project Card

| Field | Value |
|-------|-------|
| **Name** | {{PROJECT_NAME}} |
| **One-liner** | {{PROJECT_DESCRIPTION}} |
| **Language** | {{PRIMARY_LANGUAGE}} |
| **Framework** | {{FRAMEWORK}} |
| **Build System** | {{BUILD_SYSTEM}} |
| **Test Framework** | {{TEST_FRAMEWORK}} |
| **Files** | {{FILE_COUNT}} |
| **Lines of Code** | {{LOC}} |
| **Architecture Type** | {{ARCHITECTURE_TYPE}} |

### 🏗️ Architecture Type: {{ARCHITECTURE_TYPE}}

{{ARCHITECTURE_EXPLANATION}}

### 📁 Top-Level Directory Structure

```
{{DIRECTORY_TREE}}
```

### 🔑 Key Directories

| Directory | Purpose |
|-----------|---------|
{{KEY_DIRECTORY_ROWS}}

### 🧩 Tech Stack Breakdown

| Layer | Technology | Your Familiarity |
|-------|-----------|-----------------|
{{TECH_STACK_ROWS}}

### 🎯 Learning Goals for This Project

{{LEARNING_GOALS}}
```

### Phase 2: Entry Point

```markdown
## 🚪 Phase 2: Entry Point — Startup Flow

### 🔑 Entry File

**Path:** `{{ENTRY_FILE_PATH}}`
**Language:** {{ENTRY_LANGUAGE}}

### 📋 Startup Sequence

```
{{STARTUP_FLOW_ASCII}}
```

### Step-by-Step Walkthrough

{{STARTUP_STEPS}}

### 🧠 Key Concept: {{ENTRY_CONCEPT_NAME}}

{{ENTRY_CONCEPT_EXPLANATION}}

### 💬 Check-in Question

{{CHECK_IN_QUESTION}}
```

### Phase 3: Skeleton

```markdown
## 🦴 Phase 3: Skeleton — Module Dependency Topology

### 🗺️ Module Dependency Graph

```mermaid
{{DEPENDENCY_GRAPH_MERMAID}}
```

(If Mermaid not supported:)
```
{{DEPENDENCY_GRAPH_ASCII}}
```

### 📦 Module Inventory

| Module | Path | Responsibility | Dependencies |
|--------|------|---------------|-------------|
{{MODULE_ROWS}}

### 🧱 Layer Architecture

```
{{LAYER_ARCHITECTURE_ASCII}}
```

| Layer | Modules | Role |
|-------|---------|------|
{{LAYER_ROWS}}

### 🔌 Key Interfaces

{{KEY_INTERFACES}}

### 🔗 Dependency Direction

{{DEPENDENCY_DIRECTION}}
```

### Phase 4: Bloodline

```markdown
## 🩸 Phase 4: Bloodline — Data Flow Tracing

### 🎯 Scenario

{{SCENARIO_DESCRIPTION}}

### 📋 Complete Request Trace

```mermaid
{{DATA_FLOW_MERMAID}}
```

(Text version:)
```
{{DATA_FLOW_ASCII}}
```

### Step-by-Step Data Journey

{{DATA_FLOW_STEPS}}

### 🔄 Data Transformations

| Step | Input Format | Output Format | File:Line |
|------|-------------|---------------|-----------|
{{TRANSFORMATION_ROWS}}

### 📍 Code Location Map

{{CODE_LOCATION_MAP}}
```

### Phase 5: Essence

```markdown
## 💎 Phase 5: Essence — Design Patterns & Clever Implementations

### 🎨 Design Pattern Catalog

#### Pattern 1: {{PATTERN_1_NAME}}
- **Where:** `{{PATTERN_1_LOCATION}}`
- **Problem it solves:** {{PATTERN_1_PROBLEM}}
- **How it works:** {{PATTERN_1_EXPLANATION}}
- **If you wrote it naively vs. what the author did:**

```
{{PATTERN_1_COMPARISON}}
```

#### Pattern 2: {{PATTERN_2_NAME}}
[... same structure ...]

### ✨ Author's Clever Tricks

{{CLEVER_TRICKS}}

### 🔧 Room for Improvement

{{IMPROVEMENTS}}

### 🧠 Key Takeaway

{{KEY_TAKEAWAY}}
```

### Phase 6: Practice

```markdown
## 🛠️ Phase 6: Practice — Hands-On Tasks

### Task 1: {{TASK_1_TITLE}}

**Goal:** {{TASK_1_GOAL}}
**Difficulty:** {{TASK_1_DIFFICULTY}}
**Estimated time:** {{TASK_1_TIME}}

**Hints:**
{{TASK_1_HINTS}}

**Your solution:**
(Write your code here)

---

### Task 2: {{TASK_2_TITLE}}
[... same structure ...]
```

---

## Architecture Diagram Templates

### Mermaid: Module Dependency Graph

```mermaid
graph TD
{{DEPENDENCY_EDGES}}
```

### Mermaid: Sequence Diagram (Data Flow)

```mermaid
sequenceDiagram
{{SEQUENCE_STEPS}}
```

### Mermaid: Class Diagram

```mermaid
classDiagram
{{CLASS_RELATIONSHIPS}}
```

### ASCII: Simple Dependency Tree

```
{{ROOT_MODULE}}
├── {{DEP_1}}
│   ├── {{SUB_DEP_1}}
│   └── {{SUB_DEP_2}}
├── {{DEP_2}}
└── {{DEP_3}}
    └── {{SUB_DEP_3}}
```

### ASCII: Process Flow Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ {{STEP_1}} │ ──▶ │ {{STEP_2}} │ ──▶ │ {{STEP_3}} │
└──────────┘     └──────────┘     └──────────┘
```

---

## Badge Templates

Badges are inline text — emoji icon + title + flavor text, no ASCII art wrapper needed.

### Unlock Format

```
🏆 Achievement Unlocked: 🥚 Archaeologist
   "You have seen the first line of code this project ever had."
```

### Progress Bar Format

```
📊 Learning Progress
[████████░░░░░░░░░░░░] 42.8%

🏆 Unlocked: 🥚 🔭 🚪
🔒 Locked:  🦴 🩸 💎 🛠️
```

### Full Achievement Gallery (Final Notes)

```
## 🏆 Achievement Gallery

| Badge | Title | Unlocked |
|-------|-------|----------|
| 🥚 | Archaeologist | {{PHASE_0_DATE}} |
| 🔭 | Scout | {{PHASE_1_DATE}} |
| 🚪 | Gatekeeper | {{PHASE_2_DATE}} |
| 🦴 | Anatomist | {{PHASE_3_DATE}} |
| 🩸 | Bloodline Tracker | {{PHASE_4_DATE}} |
| 💎 | Treasure Hunter | {{PHASE_5_DATE}} |
| 🛠️ | Creator | {{PHASE_6_DATE}} |
| 👑 | **Project Conqueror** | {{COMPLETION_DATE}} |
```

---

## Final Merged Notes Template

```markdown
# {{PROJECT_NAME}} — Complete Learning Notes

> **Studied by:** {{USER_NAME}}
> **Started:** {{START_DATE}}
> **Completed:** {{COMPLETION_DATE}}
> **Mode:** {{MODE}} | **Level:** {{LEVEL}}

---

## 📇 Project Card

[... from Phase 1 ...]

## ⏳ Git Growth Timeline

[... from Phase 0 ...]

## 🏗️ Architecture Overview

[... from Phase 1 ...]

## 🚪 Entry Point

[... from Phase 2 ...]

## 🦴 Module Skeleton

[... from Phase 3 ...]

## 🩸 Data Flow

[... from Phase 4 ...]

## 💎 Design Patterns

[... from Phase 5 ...]

## 🛠️ Practice Tasks

[... from Phase 6 ...]

## 📖 Glossary

| Term | Definition | First Seen |
|------|-----------|------------|
{{GLOSSARY_ROWS}}

## 🏆 Achievement Gallery

[... badge gallery ...]

---

> *Generated by Project Mentor Skill v2*
```

---

## Glossary Template

```markdown
## 📖 Glossary

| Term | Definition | First Seen In |
|------|-----------|---------------|
{{GLOSSARY_ROWS}}
```

Each row format: `| {{TERM}} | {{DEFINITION}} | Phase {{PHASE_NUMBER}} |`

---

## Placeholder Reference

| Placeholder | Source | Type |
|-------------|--------|------|
| `{{PROJECT_NAME}}` | clone_and_analyze.sh output | string |
| `{{FIRST_COMMIT_DATE}}` | git_archaeology.sh output | ISO date |
| `{{FIRST_COMMIT_AUTHOR}}` | git_archaeology.sh output | string |
| `{{FIRST_COMMIT_MESSAGE}}` | git_archaeology.sh output | string |
| `{{FIRST_COMMIT_FILES}}` | git_archaeology.sh output | number |
| `{{FIRST_COMMIT_LINES}}` | git_archaeology.sh output | number |
| `{{FIRST_COMMIT_NARRATIVE}}` | Generated by skill | markdown |
| `{{GROWTH_TIMELINE}}` | git_archaeology.sh output | formatted text |
| `{{MILESTONE_ROWS}}` | git_archaeology.sh output | markdown table rows |
| `{{TOTAL_COMMITS}}` | git_archaeology.sh output | number |
| `{{CONTRIBUTOR_COUNT}}` | git_archaeology.sh output | number |
| `{{PRIMARY_LANGUAGE}}` | clone_and_analyze.sh output | string |
| `{{FRAMEWORK}}` | clone_and_analyze.sh output | string |
| `{{FILE_COUNT}}` | clone_and_analyze.sh output | number |
| `{{LOC}}` | clone_and_analyze.sh output | number |
| `{{ARCHITECTURE_TYPE}}` | Skill classification via project-patterns.md | string |
| `{{DIRECTORY_TREE}}` | clone_and_analyze.sh output | ASCII text |
| `{{DEPENDENCY_GRAPH_MERMAID}}` | ast_skeleton.sh output (transformed) | Mermaid syntax |
| `{{ENTRY_FILE_PATH}}` | Skill discovery | relative path |
| `{{PHASE_NUMBER}}` | State tracking | number |
| `{{BADGE_LIST}}` | gamification.md + state | text |
| `{{GLOSSARY_ROWS}}` | Accumulated across phases | markdown table rows |
