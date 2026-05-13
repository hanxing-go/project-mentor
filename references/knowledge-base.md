# Knowledge Base System Design

## Design Philosophy

Most learning tools are disposable: you use them once, they leave no trace. Project Mentor is designed to be a **long-term learning companion** — the more projects you study, the richer your personal knowledge graph becomes, and the better the skill can connect new concepts to things you already know.

Three mechanisms drive this:

1. **Pre-learning warmup** — Before starting a new project, scan your knowledge base and tell you what you already know that's relevant
2. **Incremental accumulation** — After each phase, extract new concepts and add them to your knowledge graph
3. **Cross-project review** — When you encounter a concept you've seen before, actively remind you

---

## Schema: `knowledge-base.json`

```json
{
  "version": "2.0",
  "createdAt": "2026-05-12T00:00:00Z",
  "lastUpdated": "2026-05-12T00:00:00Z",
  "user": {
    "knownStacks": [
      {
        "name": "Express",
        "category": "backend",
        "proficiency": 0.8,
        "lastUsed": "2026-05-01"
      }
    ],
    "learningHistory": [
      {
        "project": "claude-code",
        "url": "https://github.com/user/repo",
        "date": "2026-05-01",
        "phasesCompleted": [0, 1, 2, 3, 4, 5, 6],
        "domainsCovered": ["agent-systems", "cli-tools"],
        "conceptsLearned": ["tool-registry-pattern", "middleware-chain"]
      }
    ]
  },
  "domains": {
    "backend": {
      "masteryLevel": 0.45,
      "concepts": [
        {
          "id": "middleware-chain",
          "name": "Middleware Chain Pattern",
          "encounters": 2,
          "lastSeen": "2026-05-12"
        }
      ]
    },
    "agent-systems": {
      "masteryLevel": 0.30,
      "concepts": [
        {
          "id": "tool-registry-pattern",
          "name": "Tool Registry Pattern",
          "encounters": 1,
          "lastSeen": "2026-05-01"
        }
      ]
    }
  },
  "concepts": {
    "middleware-chain": {
      "name": "Middleware Chain Pattern",
      "domain": "backend",
      "definition": "A chain of independent handlers that process a request sequentially, each with the ability to short-circuit or modify the request/response.",
      "firstEncountered": "2026-04-15",
      "reviews": ["2026-04-15", "2026-05-12"],
      "relatedConcepts": ["pipeline-pattern", "interceptor-pattern", "chain-of-responsibility"],
      "anchorFor": ["Gin middleware", "Express app.use()", "FastAPI middleware"],
      "projectsSeenIn": ["express-blog", "claude-code"]
    }
  },
  "crossReferences": [
    {
      "conceptA": "middleware-chain",
      "conceptB": "interceptor-pattern",
      "relationship": "similar",
      "explanation": "Both intercept requests before they reach handlers. Middleware chains pass through all layers; interceptors are targeted to specific handlers/routes."
    }
  ]
}
```

---

## Domain Categories

| Domain | Detection Signals (in project) | Example Concepts |
|--------|------------------------------|-----------------|
| `backend` | HTTP server, REST API, route handlers, middleware | Routing, middleware, ORM, auth, caching |
| `frontend` | Components, state management, rendering | Virtual DOM, reactivity, composition |
| `cli-tools` | Argument parsing, command dispatch, stdin/stdout | Subcommands, flags, piping |
| `systems` | Memory management, concurrency, networking | Goroutines, ownership, async I/O |
| `data-engineering` | ETL, data pipelines, streaming | Batch processing, streaming, partitioning |
| `machine-learning` | Model definitions, training loops, datasets | Forward pass, backprop, attention |
| `devops` | CI/CD, containerization, infrastructure | Docker, Kubernetes, Terraform |
| `agent-systems` | Tool use, multi-agent, planning, memory | Agent loop, tool calling, RAG |

A project can touch multiple domains. Update all relevant domains after each completed project.

---

## Proximity Scoring Algorithm

When the user starts a new project, compute how "close" it is to their existing knowledge:

```
For each concept in the new project's tech stack:
  For each domain the user has studied:
    score += domain.masteryLevel * overlapCoefficient(projectConcept, domain.concepts)
```

The warmup prompt is generated from the top-N closest matches:

```
🔍 Knowledge base scan:
  → You studied Transformer (BERT) on 05-01 — this project uses the same attention mechanism
  → You know middleware chains from Express — this project's Go Gin uses the same pattern
  → NLP mastery: 0.7 — you're well-prepared for this project

📣 This project builds directly on concepts you already know. The key new idea is...
```

---

## Mechanism 1: Pre-Learning Warmup

**When triggered:** After pre-flight profiling, before Phase 0 begins.

**What it does:**
1. Extract the new project's tech stack from `clone_and_analyze.sh` output
2. Search `knowledge-base.json` domains and concepts for matches
3. Compute proximity score
4. Generate a warmup intro message

**Warmup prompt template:**

```
🔍 I checked your learning history. Here's what's relevant:

📚 You already know:
{{RELATED_CONCEPTS}}

📊 Domain readiness:
{{DOMAIN_SCORES}}

🎯 What's new in this project:
{{NEW_CONCEPTS}}

Ready to dive in? Let's start with Phase 0 — the archaeology dig.
```

**When to skip the warmup:**
- First project (empty knowledge base) — just say "This is your first project with me. Everything you learn here will help with future projects."
- User opted for "quick start" mode — skip warmup, go directly to Phase 0

---

## Mechanism 2: Incremental Accumulation

**When triggered:** After each phase completion.

**What gets extracted:**

| Phase | Concepts Typically Extracted |
|-------|------------------------------|
| 0 | None (git history, no code concepts) |
| 1 | Architecture type, tech stack components |
| 2 | Startup patterns, configuration patterns |
| 3 | Module organization, dependency management, interface design |
| 4 | Data flow patterns, transformation pipelines |
| 5 | Design patterns, optimization techniques |
| 6 | None (user writes code, no new reading) |

**Extraction process:**
1. Identify new technical terms encountered in this phase
2. For each term: check if it exists in `concepts` already
3. If new: add to `concepts`, assign to a domain, set initial definition
4. If existing: increment `encounters` counter, add to `reviews`
5. Update domain `masteryLevel`: `newLevel = oldLevel + (1 - oldLevel) * 0.05 * newConceptsCount`
6. Check for cross-references: does this new concept relate to any existing concept?

**Domain mastery update formula:**
```
masteryLevel_new = masteryLevel_old + (1 - masteryLevel_old) * 0.05 * newConceptsInDomain
```
This is a diminishing-returns curve — early projects in a domain raise mastery quickly; later projects add smaller increments.

---

## Mechanism 3: Cross-Project Concept Review

**When triggered:** During tutoring, when the skill encounters a concept the user has seen before (checked against `concepts` with `encounters > 0`).

**The interruption pattern:**

```
💡 Wait — you've seen this before! {{CONCEPT_NAME}} appeared in
{{PREVIOUS_PROJECT}} on {{DATE}}. Remember the {{ANCHOR_EXAMPLE}}?

This project uses the same pattern, but with a twist: {{DIFFERENCE}}.
```

**When NOT to interrupt:**
- The concept was seen only once and it was more than 3 months ago (likely forgotten, treat as new)
- The match is trivial (mention briefly but don't do a full interruption)
- The user is currently confused or stuck (don't distract them)
- The user is in Free Exploration mode (they're driving, stay concise)

**Review impact:** When a cross-project review happens, add a review entry to the concept. This counts as a spaced repetition event, strengthening the user's retention.

---

## Update Trigger Rules

| Trigger | Action | Priority |
|---------|--------|----------|
| New project started (pre-flight) | Run warmup: scan knowledge base, generate intro | High |
| Phase 1 completed | Classify project into domains, add tech stack to known stacks | Medium |
| Phase 2-5 completed | Extract new concepts, update domain mastery, check cross-references | Medium |
| Project fully completed | Full knowledge extraction: all new concepts, cross-references, update learning history, regenerate summary | High |
| User explicitly asks to review knowledge | Display learning journey summary and concept inventory | Low |

---

## File Organization

```
memory/project-mentor/
├── .mentor-state.json          # Current session progress
├── knowledge-base.json         # Cross-project knowledge graph
├── summary.md                  # Human-readable learning journey overview
└── {project-name}/
    ├── progress.md             # Per-project phase progress
    └── notes.md                # Per-project accumulated phase notes
```

### `summary.md` Template

```markdown
# Your Learning Journey

> Started: {{FIRST_PROJECT_DATE}}
> Projects completed: {{PROJECT_COUNT}}
> Concepts in toolkit: {{CONCEPT_COUNT}}

## Domain Distribution

{{DOMAIN_BAR_CHART_ASCII}}

## Project History

| Date | Project | Phases | Key Takeaways |
|------|---------|--------|---------------|
{{PROJECT_HISTORY_ROWS}}

## Concepts by Domain

### {{DOMAIN_NAME}} ({{MASTERY_PERCENT}}%)
{{CONCEPT_LIST}}

## Design Patterns Encountered
{{PATTERN_SUMMARY}}
```
