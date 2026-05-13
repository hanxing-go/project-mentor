# Project Type Dissection Strategies

## Type Detection Flowchart

When you first clone a project, answer these questions in order to classify it:

```
Is there a package.json? ─── Yes ──▶ Does it contain "next"/"react"/"vue"?
    │                                       │
    No                                      ├─ Yes → Frontend / Fullstack
    │                                       └─ No → Check for "express"/"fastify"
    ▼                                                      │
Is there a go.mod? ─── Yes ──▶ Is there a main.go?       ├─ Yes → Web Backend
    │                            │                        └─ No → CLI Tool
    No                           ├─ Yes → Check for /cmd/ or /internal/
    │                            │         ├─ Has router setup → Web Backend
    ▼                            │         └─ No router → CLI Tool
Is there a Cargo.toml? ── Yes ─▶ Check src/main.rs
    │                            ├─ Has #[tokio::main] + router → Web Backend
    No                           └─ Has clap/structopt → CLI Tool
    │
    ▼
Is there a pyproject.toml / requirements.txt?
    │
    Yes ──▶ Check for fastapi/flask/django → Web Backend
    │       Check for click/typer/argparse → CLI Tool
    │       Check for torch/tensorflow/jax → Data/AI
    No
    │
    ▼
Is there a setup.py / setup.cfg (no web framework)?
    │
    Yes ──▶ Library / SDK
    No
    │
    ▼
Check top-level directory names:
  src/ + no main entry → Library / SDK
  app/ or server/      → Web Backend
  components/ or pages/ → Frontend / Fullstack
  cmd/ or cli/          → CLI Tool
  models/ or data/      → Data/AI
```

---

## Strategy 1: Web Backend (Spring / Express / Django / Gin / FastAPI / Axum)

### Detection Signals
- Route definitions (`@GetMapping`, `app.get()`, `urlpatterns`, `r.GET()`)
- Middleware files or directories
- Controller/handler/service/repository directory structure
- Database configuration files (database.yml, .env with DB URLs)
- HTTP server startup in entry file

### Entry Point Pattern
Look for: the file that initializes the HTTP server. Usually `main.go`, `app.js`, `server.ts`, `manage.py`, `__main__.py`. Trace from there: config loading → middleware registration → route binding → `ListenAndServe()`.

### Key Directories
```
controllers/ or handlers/   — Request handling, input validation
services/                   — Business logic
repositories/ or models/    — Data access layer
middleware/                 — Cross-cutting concerns (auth, logging, CORS)
config/                     — Configuration files
routes/ or urls/            — URL-to-handler mappings
```

### Data Flow Pattern
```
HTTP Request
  → Middleware Chain (auth → logging → cors → rate-limit)
  → Router (URL pattern match)
  → Controller/Handler (parse input, validate)
  → Service Layer (business logic)
  → Repository/DAO (SQL/ORM queries)
  → Database
  ← Response (JSON/HTML)
```

### Typical Design Patterns Found
- **Middleware Chain:** Chain of Responsibility pattern
- **Repository Pattern:** Abstracting data access behind interfaces
- **Dependency Injection:** Wiring services into controllers
- **DTO/Serializer:** Data transformation between layers
- **Service Layer:** Facade over business logic

### Phase-by-Phase Adaptations
- **Phase 2 (Entry):** Focus on server startup — what order are middlewares registered? What happens before the first request can be served?
- **Phase 3 (Skeleton):** Map controller→service→repository dependencies. Which controllers call which services?
- **Phase 4 (Bloodline):** Pick the most common endpoint (e.g., `GET /users/:id`). Trace from route definition through to DB query and back.
- **Phase 6 (Practice):** Task idea: add a new endpoint with validation, or add a new middleware.

---

## Strategy 2: Frontend / Fullstack (React / Vue / Next.js / Svelte / Nuxt)

### Detection Signals
- `package.json` with react/vue/next/nuxt/svelte dependencies
- `components/`, `pages/`, or `app/` directories
- `jsx`/`tsx`/`.vue`/`.svelte` file extensions
- Tailwind/CSS-in-JS configuration
- `next.config.js`, `vite.config.ts`, `nuxt.config.ts`

### Entry Point Pattern
Look for: the root component (`App.tsx`, `_app.tsx`, `app.vue`, `+layout.svelte`). For frameworks with routing: the route configuration file. The entry is typically: HTML shell → root component mount → router init → first render.

### Key Directories
```
pages/ or app/              — Route-level components (Next.js/Remix)
components/                 — Reusable UI components
layouts/                    — Page shell/layout components
stores/ or state/           — State management
composables/ or hooks/      — Reusable logic
lib/ or utils/              — Utility functions
api/ or services/           — API client calls
public/ or static/          — Static assets
```

### Data Flow Pattern
```
User Interaction (click/type)
  → Event Handler
  → State Update (useState / store action / signal set)
  → Re-render (virtual DOM diff → real DOM update)
  → (Optional) API Call → Server → Response → State Update → Re-render
```

### Typical Design Patterns Found
- **Container/Presentational:** Smart components manage state; dumb components render
- **Composition:** Components composed from smaller pieces
- **Observer:** State changes → automatic UI updates
- **HOC / Render Props:** (Older React) Cross-cutting component logic
- **Module Federation:** Micro-frontend architecture

### Phase-by-Phase Adaptations
- **Phase 2 (Entry):** Focus on the root component tree — what renders first? How does the router decide which page to show?
- **Phase 3 (Skeleton):** Map component hierarchy. Which components import which? What's the state wiring?
- **Phase 4 (Bloodline):** Pick a feature (e.g., "user clicks login"). Trace from button click → form state → API call → response → redirect.
- **Phase 6 (Practice):** Task idea: add a new page with a form, or modify an existing component's behavior.

---

## Strategy 3: CLI Tool

### Detection Signals
- `main.go`, `main.rs`, `cli.py`, `index.js` with argument parsing
- Libraries: cobra/flag (Go), clap/structopt (Rust), click/typer/argparse (Python), commander/yargs (Node)
- `cmd/` directory with subcommand files
- Binary name in `Cargo.toml` `[[bin]]` section
- No HTTP server initialization

### Entry Point Pattern
Look for: `main()` function. Trace: argument definition → argument parsing → command dispatch → execution. Most CLI tools follow a pattern where subcommands map to handler functions.

### Key Directories
```
cmd/ or commands/           — Subcommand implementations
internal/ or lib/           — Core logic
pkg/ or api/                — Public API (Go library CLI pattern)
config/                     — Configuration loading
```

### Data Flow Pattern
```
CLI Arguments (os.Args / sys.argv)
  → Argument Parser (flag definitions, help text generation)
  → Command Router (match subcommand)
  → Pre-flight Checks (config load, validate flags, check prerequisites)
  → Core Logic Execution
  → Output Formatting (table, JSON, plain text)
  → Exit Code
```

### Typical Design Patterns Found
- **Command Pattern:** Each subcommand is a command object
- **Builder Pattern:** Chained configuration building
- **Strategy Pattern:** Different output formatters (table vs. JSON vs. YAML)
- **Pipeline Pattern:** Data transformation steps

### Phase-by-Phase Adaptations
- **Phase 2 (Entry):** Focus on argument parsing and command dispatch. How does the tool decide which subcommand to run?
- **Phase 3 (Skeleton):** Map subcommands to handler modules. Identify shared utilities.
- **Phase 4 (Bloodline):** Pick the most-used subcommand. Trace from CLI flag → parsed config → execution → output.
- **Phase 6 (Practice):** Task idea: add a new flag to an existing command, or add a new subcommand.

---

## Strategy 4: Library / SDK

### Detection Signals
- `setup.py` / `pyproject.toml` (Python package)
- `package.json` with `"main"` field (Node package)
- `go.mod` with no `main.go` (Go module)
- `Cargo.toml` with `[lib]` section (Rust crate)
- Exported functions/classes are the primary artifact
- No entry point; instead has public API surface

### Entry Point Pattern
Libraries don't have a single entry point. Instead, trace the **public API surface**: which functions/classes are exported? Which are internal? The "entry" is the module index — the file that re-exports everything.

### Key Directories
```
src/ or lib/                — Source code
tests/ or __tests__/        — Tests (often serve as usage examples)
examples/                   — Usage examples (goldmine for understanding)
benchmarks/                 — Performance tests
```

### Data Flow Pattern
```
Client Code
  → Import Library
  → Call Public API Function
  → Internal Validation + Processing
  → (Optional) Internal Pipeline of Transformations
  ← Return Result
```

### Typical Design Patterns Found
- **Facade Pattern:** Simple public API hides complex internals
- **Strategy Pattern:** Pluggable algorithms (sorting, encoding, etc.)
- **Builder Pattern:** Fluent API for constructing complex objects
- **Decorator/Wrapper:** Adding behavior to existing objects
- **Plugin System:** Extension points for user code

### Phase-by-Phase Adaptations
- **Phase 2 (Entry):** Instead of startup flow, trace the public API surface. What does a user see when they `import` this library?
- **Phase 3 (Skeleton):** Map the internal module structure. Which modules are public vs. private?
- **Phase 4 (Bloodline):** Pick the most commonly used API function. Trace its complete implementation path.
- **Phase 6 (Practice):** Task idea: use the library in a small script, or add a new public function.

---

## Strategy 5: Data / AI Project

### Detection Signals
- ML framework imports (torch, tensorflow, jax, transformers)
- `models/`, `data/`, `notebooks/`, `checkpoints/` directories
- Training configuration files (YAML, JSON configs)
- Dataset loading code (torch.utils.data, tf.data)
- `train.py`, `evaluate.py`, `inference.py`

### Entry Point Pattern
Usually `train.py` or a main script that orchestrates: data loading → model building → training loop → evaluation → checkpoint saving. May also have separate inference/API serving scripts.

### Key Directories
```
models/                     — Model architecture definitions
data/ or datasets/          — Data loading and preprocessing
trainers/ or engines/       — Training loop logic
configs/                    — Hyperparameter configurations
notebooks/                  — Exploratory notebooks
scripts/                    — Utility scripts for data prep, evaluation
```

### Data Flow Pattern
```
Raw Data
  → Data Loader (batching, shuffling, preprocessing)
  → Model Forward Pass (input → layers → output)
  → Loss Computation
  → Backward Pass (gradients)
  → Optimizer Step (weight update)
  → Metrics Logging
  → (Loop back to Data Loader for next epoch)
```

### Typical Design Patterns Found
- **Registry Pattern:** Model registry, loss registry, optimizer registry
- **Factory Pattern:** Creating models/datasets from config
- **Observer Pattern:** Logging/callback system during training
- **Strategy Pattern:** Different training strategies (supervised, self-supervised)

### Phase-by-Phase Adaptations
- **Phase 2 (Entry):** Trace the training script — what happens from `python train.py` to the first batch being processed?
- **Phase 3 (Skeleton):** Map model definition → data pipeline → training loop → evaluation. Which modules touch which?
- **Phase 4 (Bloodline):** Trace one training step: data batch → forward pass → loss → backward pass → weight update.
- **Phase 6 (Practice):** Task idea: modify a hyperparameter, add a metric, or write a small inference script.

---

## Hybrid Projects

Many real projects mix types. A CLI tool may also export a library API. A web backend may include a CLI for database migrations.

**Handling hybrids:**
1. Classify the **primary** type (what the README leads with)
2. Walk through that type's full strategy first
3. Then say: "This project also exposes a CLI — let me quickly show you that part too"
4. Use the secondary strategy as a supplement, not a full redo

### Common Hybrids:
- **CLI + Library:** See Go projects with `cmd/` + exported packages. Primary = CLI. Supplement = public API surface.
- **Web + CLI:** Database migration tools, admin CLIs. Primary = Web. Supplement = CLI subcommand structure.
- **Frontend + Backend:** Monorepo with `client/` and `server/`. Treat as two separate projects; ask the user which they want first.

---

## Quick Reference Decision Matrix

| Signal | Type | Entry Point | Key Directories | Data Flow Focus |
|--------|------|-------------|-----------------|----------------|
| Route definitions + HTTP server | Web Backend | Server init file | controllers, services, models | Request → Response |
| JSX/Vue/Svelte + component dirs | Frontend | Root component | components, pages, stores | Event → State → Render |
| Argument parsing + no HTTP | CLI Tool | main() func | cmd, internal, commands | Args → Command → Output |
| No main, exports API surface | Library/SDK | Public API index | src, lib, tests | Client Call → Internal Logic → Return |
| ML framework + training configs | Data/AI | train.py | models, data, configs | Data → Forward Pass → Loss → Backward |
