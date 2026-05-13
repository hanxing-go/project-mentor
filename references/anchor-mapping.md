# Tech Stack Anchor Mapping Table (Rosetta Stone)

## How This Table Works

When explaining unfamiliar technology to a user, use a 3-step mapping process:

1. **Identify the user's known stack** — Ask in pre-flight: "What backend/frontend/database tech are you most comfortable with?"
2. **Identify the project's unfamiliar tech** — From `clone_and_analyze.sh` output, note which technologies the user flagged as unfamiliar
3. **Cross-reference below** — Find the bridging analogy and use it in explanations

**Golden rule:** Always state the analogy explicitly. Don't just think it — say it: *"This Go Gin router is like Express's `app.get()` — you define a path and a handler function."*

Use the template: **"X in this project is like Y in [your familiar stack] — [one-line explanation of the similarity]."**

---

## Backend Framework Mappings

### Route / Request Handling

| Unfamiliar Tech | If user knows Spring Boot | If user knows Express | If user knows Django | If user knows Flask |
|----------------|--------------------------|----------------------|---------------------|--------------------|
| **Gin (Go)** | `@RequestMapping` / Controller | `app.get()` / Router | `urlpatterns` / View | `@app.route()` |
| **Echo (Go)** | Same as Gin mapping | Same as Gin mapping | Same as Gin mapping | Same as Gin mapping |
| **FastAPI (Python)** | `@GetMapping` with type hints | Express but with automatic validation | Django REST Framework ViewSet | Flask + marshmallow |
| **Actix (Rust)** | WebFlux / reactive controllers | Express with middleware chain | Django async views | — |
| **Axum (Rust)** | Similar to Actix mapping | Express-like extractors | — | — |

### Middleware / Interceptors

| Unfamiliar Tech | Spring Boot | Express | Django |
|----------------|-------------|---------|--------|
| **Gin Middleware** | Filter / HandlerInterceptor | `app.use()` middleware | Django Middleware (process_request) |
| **Echo Middleware** | Same as Gin | Same as Gin | Same as Gin |
| **FastAPI Middleware** | Filter | Express middleware | Django middleware |
| **Actix Middleware** | WebFilter | Connect middleware | — |

### Dependency Injection

| Unfamiliar Tech | Spring Boot | Express | Django |
|----------------|-------------|---------|--------|
| **Wire (Go)** | `@Autowired` | Manual DI (no framework) | — |
| **Dig (Go)** | `@Autowired` | Manual DI | — |
| **FastAPI Depends()** | `@Autowired` on method params | — | Django CBV mixins |

### ORM / Data Access

| Unfamiliar Tech | Spring Boot (JPA/Hibernate) | Express (Sequelize/Prisma) | Django ORM |
|----------------|---------------------------|--------------------------|-----------|
| **GORM (Go)** | JPA Repository + Hibernate | Sequelize Model | Django Models |
| **sqlc (Go)** | Spring Data JDBC | Raw SQL builder | Raw SQL |
| **SQLx (Rust)** | JdbcTemplate | Knex | Django db.connection |
| **Diesel (Rust)** | JPA type-safe queries | Prisma type-safe | Django ORM type-safe queries |

---

## Frontend Framework Mappings

### Component Model

| Unfamiliar Tech | If user knows React | If user knows Vue | If user knows Angular |
|----------------|--------------------|--------------------|----------------------|
| **Svelte** | Component but compiled away (no virtual DOM) | Single-file components but no VDOM | Standalone components |
| **SolidJS** | React hooks but no re-renders | Vue Composition API but signals | — |
| **Preact** | React but lighter (same API) | — | — |
| **Lit** | Class components but web-standard | — | Web Components standard |

### State Management

| Unfamiliar Tech | React | Vue | Angular |
|----------------|-------|-----|---------|
| **Zustand** | Simpler Redux / Context | Pinia | Service with BehaviorSubject |
| **Jotai** | Atomic state like Recoil | Ref + reactive | Signal |
| **XState** | useReducer + state machine | Vue state machine | NgRx + state machine |

---

## Async / Concurrency Mappings

| Unfamiliar Tech | If user knows JS/TS | If user knows Python | If user knows Java |
|----------------|--------------------|--------------------|--------------------|
| **Goroutine + Channel** | Promise + async/await + event loop (but lighter) | asyncio + Queue (but OS-thread-backed) | Virtual Threads (Project Loom) + BlockingQueue |
| **Go select {}** | `Promise.race()` | `asyncio.wait(return_when=FIRST_COMPLETED)` | `ExecutorService.invokeAny()` |
| **Rust async/await** | JS async/await (similar syntax, different runtime) | Python async/await (similar syntax) | CompletableFuture + thenCompose |
| **Rust tokio::spawn** | `new Promise()` + run | `asyncio.create_task()` | `ExecutorService.submit()` |

---

## Build & Package Management

| Unfamiliar Tech | If user knows npm | If user knows pip | If user knows Maven/Gradle |
|----------------|-----------------|-----------------|--------------------------|
| **Go modules** | package.json + node_modules | requirements.txt + venv | pom.xml + Maven Central |
| **Cargo (Rust)** | npm + Cargo.toml (more structured) | pip + pyproject.toml | Gradle + build.gradle |
| **Bundler (Ruby)** | npm + package.json (Gemfile = package.json) | pip + Pipfile | Maven + pom.xml |

---

## Architecture Patterns

| Pattern | In Spring Boot | In Express | In React |
|---------|---------------|-----------|----------|
| **Hexagonal / Ports & Adapters** | Service interface + Impl + Repository | Service layer + Data access layer | Context + Hooks + API client |
| **CQRS** | Separate Read/Write services | Separate GET/POST handlers | Separate query/mutation hooks |
| **Event Sourcing** | Spring Events + Mongo change stream | EventEmitter + event store | useReducer + action log |

---

## When NOT to Use an Analogy

Some concepts don't have clean cross-stack analogs. When this happens:

1. **Say so honestly:** "This Go `defer` mechanism doesn't really have a direct equivalent in Express. Let me explain it from scratch."
2. **Explain from first principles:** Use life analogies (restaurant, assembly line) instead of tech analogies.
3. **Mark it as new:** "This will be a new concept in your toolkit. Pay extra attention — it's a powerful pattern you'll see in many languages."

### Concepts that are often unique to their ecosystem:

- Go: `defer`, zero-value initialization, implicit interface satisfaction
- Rust: ownership/borrowing, lifetimes, trait system (beyond interfaces)
- React: hooks rules, reconciliation, synthetic events
- Erlang/Elixir: actor model, let-it-crash, hot code swapping
