# Pipeline Runner Design Options

This note explores approaches for implementing the new pipeline runner that will replace the `Complete_Analysis*.py` scripts. It feeds into the ADR described in the refactor plan (Workstream 1).

---

## Requirements Recap

- Execute a sequence of stages (filters) with shared context and clear input/output contracts.
- Allow conditional stages (e.g., tide correction optional) driven by `settings.json`.
- Provide progress logging and structured error handling (stop vs continue).
- Support resuming or rerunning individual stages when upstream artifacts already exist.
- Integrate with CLI commands (and future GUI) via a clean API.

---

## Option A — Function Pipeline with Context Object

**Shape**
- Define `PipelineContext` dataclass holding settings, paths, intermediate artifacts.
- Each stage is a function `stage(context: PipelineContext) -> PipelineContext`.
- Runner iterates over a list of stage callables, updating context in place.

**Pros**
- Simple, minimal boilerplate; easy to unit test each stage.
- Uses existing functions with small wrappers.
- Easy to add instrumentation (log before/after each function).

**Cons**
- Harder to inject per-stage metadata (retry policy, required artifacts) without additional structure.
- No built-in skip/resume logic; would need external bookkeeping.

---

## Option B — Stage Classes with Interface

**Shape**
- Create `BaseStage` class with methods:
  - `should_run(context) -> bool`
  - `run(context) -> None`
  - `artifacts_produced` metadata
- Runner loops over stage instances; context is mutated or returns new objects.

**Pros**
- Encapsulates logic for skipping/resuming within each stage.
- Allows stage-specific configuration (e.g., max retries, logging tags).
- Easier to extend with decorators (timing, metrics).

**Cons**
- Slightly more boilerplate and indirection.
- Might be overkill if most stages stay simple functions.

---

## Option C — Declarative Stage Registry (YAML/JSON)

**Shape**
- Define pipeline stages in a registry (list of dicts) describing name, callable path, dependencies, toggles.
- Runner reads registry, resolves callables, executes based on config flags.

**Pros**
- Highly configurable; pipeline definition can evolve without code changes.
- Enables advanced features (dynamic DAG execution, parallel stages) later.

**Cons**
- Requires more infrastructure up front (registry format, resolver, validation).
- Overhead might be unnecessary until we need complex branching.

---

## Proposed Direction (Chosen)

We will implement the runner using **Option B** (stage classes) because it balances structure with flexibility:
- Build a `PipelineStage` protocol / abstract base class.
- Provide a stage registry (Python list) and simple runner that respects stage order and optional flags.
- Add lightweight metadata (name, description, dependencies) to each stage instance for logging and CLI output.

Once the basic runner works, we can layer extra features (skip/resume, caching, declarative configuration) without rewriting stages.

> **Implementation note:** everything can be done with standard-library Python (`abc`, `typing.Protocol`, `dataclasses`, `logging`). No new third-party frameworks are required.

---

## Next Steps

1. Draft ADR for choosing the stage-class runner (summarize pros/cons vs alternatives).
2. Prototype `PipelineContext`, `PipelineStage`, and `PipelineRunner` modules.
3. Wrap existing functions (`load_settings`, `initial_settings`, etc.) as stage implementations.
4. Add CLI flag (e.g., `--use-new-runner`) to opt into the new pipeline for testing.

Document any decisions or spikes in this folder so the team can follow along.
