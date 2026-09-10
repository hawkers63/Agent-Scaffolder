# Agent Scaffolder — Project Architect Agent

## 1. Project Identity

**Agent Scaffolder** is a single-file, Windows-first desktop utility built with **CustomTkinter** that automates the creation of AI agent configuration files (`agents.md`, `bug_hunter.md`, `enhancement_agent.md`) for *other* codebases. It orchestrates two external systems:

1. **Repomix** (Node.js CLI, invoked via subprocess) — packages a target repository into a single XML context blob.
2. **Anthropic Claude API** (via the `anthropic` Python SDK) — consumes that XML and generates tailored Markdown agent prompts.

There is currently **no package structure, no tests, and no build system** — this is a lightweight internal tool, not a distributed library. Treat it accordingly: prioritize correctness, safety of file/subprocess operations, and UI responsiveness over enterprise architecture.

---

## 2. Tech Stack (Authoritative — Do Not Substitute)

| Concern | Technology | Notes |
|---|---|---|
| Language | Python 3.11 | Pinned interpreter path in `.bat` launcher: `Python311` |
| GUI | `customtkinter` (>=5.2) | **Never** use raw `tkinter` widgets, `ttk`, PyQt, or any other GUI toolkit. All UI elements must be `CTk*` classes. |
| LLM Client | `anthropic` (>=0.40) | Use `anthropic.Anthropic(api_key=...)` and `client.messages.create(...)`. Do not introduce OpenAI, LangChain, or other LLM SDKs. |
| Secrets Storage | `keyring` (>=25) | **All secrets** (API keys) go through Windows Credential Manager via `keyring.set_password` / `get_password` / `delete_password`. Never write API keys to disk, `.env` files, JSON, or logs. |
| Config Persistence | Plain JSON files (`projects.json`, `last_project.json`) | No database, no ORM, no config framework (no YAML/TOML libs). Keep this pattern. |
| External Repo Packaging | `repomix` (Node.js CLI) | Invoked via `subprocess`, resolved with `shutil.which`, with a `shell=True` string-command fallback if not found on PATH. |
| Concurrency | `threading.Thread(..., daemon=True)` | Used to keep the CTk mainloop responsive during long-running I/O (subprocess calls, network calls). |
| Platform | Windows only | Hardcoded paths (`C:\nvm4w\nodejs`, `USERPROFILE`, `explorer.exe`). Do not add cross-platform abstractions unless explicitly requested. |

**Do not add**: virtual environments tooling (poetry/pipenv), async frameworks (asyncio/trio) unless required, web frameworks, ORMs, YAML configs, or GUI frameworks other than CustomTkinter.

---

## 3. File Structure Rules

This is a **flat, single-module application**. Maintain this structure unless a refactor is explicitly requested:

```
agent_scaffolder.py          # Entire application: GUI, settings, orchestration logic
requirements-scaffolder.txt  # Pinned minimal dependency list (no lockfiles, no requirements.txt duplication)
projects.json                # User-editable list of {"name": ..., "path": ...} project shortcuts
last_project.json            # Persists last-selected project path as {"path": "..."}
Run-Agent-Scaffolder.bat     # Windows launcher: sets PATH for nvm/node, invokes pinned python.exe
icon/                       # Product icon: Agent.Scaffolder.ico (wired via iconbitmap)
                             # Settings + main window; missing file keeps default Tk icon
```

**Rules:**
- Do **not** split `agent_scaffolder.py` into multiple modules/packages unless the file grows unmanageably (it is intentionally monolithic for a small utility). If a split is ever justified, keep it minimal: e.g., separate `settings.py` / `scaffolding.py`, but confirm with the maintainer first.
- Constants (`SERVICE_NAME`, `ACCOUNT_NAME`, `APP_DIR`, `PROJECTS_FILE`, `LAST_PROJECT_FILE`, `OUTPUT_ROOT`, `MODEL`, `DEFAULT_PROJECTS`, `OTHER_LABEL`) belong at module top level, above class definitions — preserve this convention.
- Generated agent output is **never** written into the app's own directory or into the target project's source tree. It goes to `OUTPUT_ROOT` (`%USERPROFILE%\Desktop\Agent Outputs\<safe_project_name>`). Preserve this separation strictly — this tool must never mutate the codebase it's analyzing.
- Temporary Repomix XML output must live under `APP_DIR` (`.repomix-context.xml`), never inside the target project directory, and must always be cleaned up in a `finally` block.

---

## 4. Coding Standards

### 4.1 Style
- Standard PEP 8, 4-space indentation, snake_case for functions/variables, PascalCase for classes (`ScaffoldingApp`, `SettingsWindow`).
- Module-level helper functions (`ensure_projects_file`, `load_projects`, `safe_folder_name`, etc.) precede class definitions — keep pure I/O/utility logic outside classes when it doesn't need instance state.
- Docstrings are short and used sparingly, only on non-obvious helpers (e.g., `safe_folder_name`). Do not over-document trivial code.

### 4.2 Security & Secrets
- **Never** store API keys in JSON files, environment files, source code, or logs.
- All key access must go through `keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)`.
- When deleting a key, always wrap `keyring.delete_password` in a `try/except keyring.errors.PasswordDeleteError: pass` — deletion of a non-existent key must not crash the app.
- Never print or display the raw API key in the UI except in the masked `CTkEntry(show="*")` field.

### 4.3 File & Subprocess Safety
- All file reads/writes use explicit `encoding="utf-8"`.
- All JSON load/parse operations must be wrapped in `try/except (OSError, json.JSONDecodeError)` with a safe fallback (never let malformed config crash startup).
- Subprocess calls must:
  - Resolve the binary explicitly via `shutil.which(...)` when possible, falling back to a `shell=True` string command only if resolution fails.
  - Pass an explicit `env` dict built via `_build_subprocess_env()` (which injects Node/nvm paths) — never rely on inherited PATH alone for `repomix`.
  - Use `check=True` so failures raise `CalledProcessError`, caught explicitly upstream.
  - Set `cwd` to the **target project directory**, not `APP_DIR`, when running Repomix.
- Any file/directory create must use `os.makedirs(..., exist_ok=True)`; never assume a directory exists.
- Path comparisons for "is this the same project" must use `os.path.normcase(os.path.abspath(...))` on both sides (Windows case-insensitivity).

### 4.4 GUI / Threading Rules
- **Never perform blocking I/O (subprocess, network, file I/O) on the main Tkinter thread.** All such work happens inside `threading.Thread(target=..., daemon=True).start()`, launched from a UI event handler.
- Any UI update triggered from a background thread **must** be marshaled back to the main thread via `self.after(0, lambda: ...)`. Do not call `.configure()` on widgets directly from a worker thread.
- Disable relevant interactive widgets (`generate_btn`, `settings_btn`, `project_menu`) before starting a long-running operation, and always re-enable them in a `finally`-driven `reset_buttons()` call — even on exceptions.
- Status text updates go through the single `update_status(text)` helper — do not create parallel status-reporting mechanisms.
- Modal-like child windows (e.g., `SettingsWindow`) must call `self.grab_set()` and guard against duplicate instantiation via a `winfo_exists()` check pattern, as done in `open_settings()`.

### 4.5 Error Handling
- Every top-level operation in `run_scaffolding` distinguishes error types explicitly:
  - `subprocess.CalledProcessError` → "Repomix Error"
  - `anthropic.AuthenticationError` → "Authentication Error" (prompt re-entry of key)
  - Generic `Exception` → "API/System Error" (catch-all, last resort)
- User-facing errors always go through `_show_error(title, message)`, which updates the status label **and** shows a `messagebox.showerror` — never fail silently, and never use bare `print()` for error reporting.
- Cleanup of temporary files (`.repomix-context.xml`) must happen in a `finally` block regardless of success/failure path.

---

## 5. LLM Integration Rules

- Model is configurable via `AGENT_SCAFFOLDER_MODEL` env var, defaulting to the module-level `MODEL` constant. Never hardcode the model string inline in the request call — always reference the `MODEL` constant.
- All Claude calls must set `thinking={"type": "disabled"}` unless a future feature explicitly requires extended thinking — keep generation fast and deterministic for this use case.
- `max_tokens` is fixed at 4096 for agent file generation; do not silently increase this without justification (cost/latency tradeoff for a batch of 3 generations per run).
- Prompts are constructed as a single `user` message embedding `<repository_context>` XML plus a role description. Maintain this exact prompt structure (system-prompt-as-instruction pattern) unless redesigning the generation pipeline.
- Response parsing assumes `response.content[0].text` — a single text block. Do not assume multi-block responses unless tool use / structured output is introduced.
- Instruct the model explicitly to output **raw Markdown only, no fences, no preamble** — this contract must be preserved in any prompt edits, since output is written directly to `.md` files via `.strip()`.

---

## 6. Configuration & State Management

- `projects.json` and `last_project.json` are **user-mutable, non-versioned local state** — treat them as runtime data, not source. `DEFAULT_PROJECTS` in code is the fallback/seed, not the source of truth once `projects.json` exists.
- `ensure_projects_file()` must remain idempotent and non-destructive — it only seeds the file if absent, never overwrites existing user data.
- `load_projects()` / `load_last_project_path()` must always degrade gracefully to defaults on any parse/IO failure — this app must never crash on startup due to corrupted local JSON.
- UI state restoration (`_restore_last_selection`) follows a strict priority order: (1) exact match to last saved project path among known projects, (2) valid arbitrary "Other" path, (3) first known project that exists on disk, (4) first project in list regardless of existence. Preserve this fallback chain when modifying selection logic.
- Use the `_suppress_project_event` flag pattern whenever programmatically setting `CTkOptionMenu` values to avoid re-triggering `on_project_selected` in a feedback loop.

---

## 7. Strict Execution Rules for Any Code Change

1. **Do not introduce new dependencies** without updating `requirements-scaffolder.txt` and confirming they serve a concrete, stated need (avoid dependency creep in a minimal tool).
2. **Do not change the output directory contract** (`%USERPROFILE%\Desktop\Agent Outputs\<project>`) without explicit instruction — downstream automation (e.g., the `.bat` launcher, user habits) depends on this location.
3. **Do not write generated artifacts into the target project directory** — this tool is strictly read-only against the codebase it sc