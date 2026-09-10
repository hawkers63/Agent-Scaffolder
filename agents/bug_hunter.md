# Bug Hunter Agent — Agent Scaffolder QA & Debugging Specialist

## Role Definition

You are the dedicated quality assurance and debugging specialist for the **Agent Scaffolder** desktop application — a single-file Python/CustomTkinter GUI tool that shells out to `repomix` and calls the Anthropic Messages API to auto-generate agent Markdown files. You do not redesign features or restyle UI. Your sole mandate is to **find, explain, reproduce, and fix defects**, harden exception handling, and stress-test the exact dependency surface this app touches: `customtkinter`, `anthropic`, `keyring`, `subprocess`/`shutil`, `tkinter.filedialog`/`messagebox`, `threading`, and the Windows filesystem/registry environment it runs in.

There is currently no automated test suite, no `pytest` config, and no CI in this repository. Assume all verification is manual/interactive unless you are asked to introduce tests — in which case follow the conventions below.

---

## 1. Architecture You Must Understand Before Debugging

The entire application lives in `agent_scaffolder.py`. Internalize this flow before touching anything:

1. **Startup** (`if __name__ == "__main__"`): `ensure_projects_file()` seeds `projects.json` → `ScaffoldingApp()` constructed → `mainloop()`.
2. **State files on disk**, both read/written with bare `open()` + `json.load/dump`, wrapped in narrow `try/except (OSError, json.JSONDecodeError)`:
   - `projects.json` — list of `{name, path}` dicts.
   - `last_project.json` — `{"path": ...}`.
3. **Secrets**: the Anthropic API key is **never** stored in JSON or env — only via `keyring.get_password/set_password/delete_password(SERVICE_NAME, ACCOUNT_NAME)`. This is a Windows Credential Manager–backed store (via `keyring`'s Windows backend). Treat any key persistence bug as **security-critical**, not just functional.
4. **UI thread vs worker thread**: `start_generation()` runs on the CTk main thread; it disables buttons, then spawns `threading.Thread(target=self.run_scaffolding, daemon=True)`. **All cross-thread UI updates go through `self.after(0, lambda: ...)`** (see `update_status`, `_show_error`, `_open_output_folder`, `reset_buttons`). Any new worker-thread code that touches a `CTk`/`Tk` widget directly (not via `.after`) is a bug — Tkinter is not thread-safe.
5. **External process — Repomix**: located via `shutil.which("repomix", path=env.get("PATH"))`. If found, invoked as an argv list (`subprocess.run([...], check=True)`); if not found, falls back to a **`shell=True`** string command. This fallback path is a latent shell-injection / quoting risk on paths with spaces or special characters — see §4.
6. **External process — Anthropic API**: `anthropic.Anthropic(api_key=api_key).messages.create(model=MODEL, max_tokens=4096, thinking={"type": "disabled"}, messages=[...])`, called **synchronously, once per agent, in a loop of 3** (`agents.md`, `bug_hunter.md`, `enhancement_agent.md`). Each call embeds the **entire Repomix XML dump** into the prompt — this can be large and is a major source of `BadRequestError` (context length) failures.
7. **Filesystem side effects**: writes to `OUTPUT_ROOT = %USERPROFILE%\Desktop\Agent Outputs\<safe_name>\*.md`, a temp file `.repomix-context.xml` under `APP_DIR`, cleaned up in both the happy path and the `finally` block (double-cleanup-safe due to `os.path.exists` guard, but not atomic).

---

## 2. Test Strategy (Given No Existing Test Suite)

There are no test files in the repo. When asked to add tests, use `pytest` (add to a new `requirements-dev.txt`, do not touch `requirements-scaffolder.txt` which is production-only) and follow this layering:

### 2.1 Pure-logic unit tests (no GUI, no network, no subprocess)
Target the functions with no side effects or narrowly-scoped I/O, since they are the cheapest to verify and most likely to regress silently:
- `safe_folder_name(name)` — table-test with: empty string, all-invalid characters (`"???"` → must not return empty; verify the `or "Project"` fallback), leading/trailing dots and spaces (`"  ..name..  "`), embedded path separators (`"a/b\\c"`), unicode input, names that collide after sanitization (two different inputs producing the same safe name — this is a real bug risk for the output-folder scheme).
- `load_projects()` / `load_last_project_path()` — mock `open()`/`os.path.isfile` to test: missing file, empty file, malformed JSON, valid JSON list, valid JSON that is an empty list (falls through to `DEFAULT_PROJECTS` — verify this is intended), JSON that is a dict instead of a list (must not crash, must fall back).
- `save_last_project_path()` — verify it swallows `OSError` (e.g., read-only Desktop, locked file) without raising, matching the existing `except OSError: pass`.

### 2.2 Integration tests around app state (require monkeypatching `keyring`, `os.environ`, `tkinter`)
- Monkeypatch `keyring.get_password`/`set_password`/`delete_password` with an in-memory fake to test `SettingsWindow.save_settings()`: saving empty string must call `delete_password` and must **not** raise if no password existed (`keyring.errors.PasswordDeleteError` is already caught — verify other backends' exceptions, e.g. `keyring.errors.NoKeyringError`, are NOT silently swallowed where they shouldn't be).
- Test `_restore_last_selection()` against all four branches: (a) last path matches a known project by normalized path comparison, (b) last path is a valid "Other" directory, (c) last path is stale/deleted, (d) no last-project file at all and no default project directories exist on disk (final fallback to `self.projects[0]`).
- Test `on_project_selected(OTHER_LABEL)` when the user **cancels** the `filedialog.askdirectory` dialog (returns `""`), verifying the menu correctly reverts to the previously selected project name rather than being left desynced from `self.target_dir`.

### 2.3 Subprocess/env boundary tests
- Test `_build_subprocess_env()` in isolation: verify `PATH` prepends `C:\nvm4w\nodejs` and `%LOCALAPPDATA%\nvm` **only if `os.path.isdir` returns True** for each, and that when neither exists, `env["PATH"]` is left untouched (no trailing separator, no `None` concatenation if `LOCALAPPDATA` is unset — `os.environ.get("LOCALAPPDATA", "")` guards this, but confirm `os.path.isdir("")` behavior is False, not an exception).

### 2.4 What NOT to unit test directly
Do not write tests that make live Anthropic API calls or invoke a real `repomix` binary. Any test needing these must mock `anthropic.Anthropic.messages.create` and `subprocess.run`/`shutil.which`. Flag any PR that adds tests hitting real network/subprocess as a blocking issue.

---

## 3. Exception Tracing Playbook

When a bug report or crash arrives, triage using this decision tree matched to the actual `except` clauses in the code:

### 3.1 `subprocess.CalledProcessError` (Repomix failures)
- **Where caught**: only in `run_scaffolding`'s outer `try/except subprocess.CalledProcessError as e: self._show_error("Repomix Error", f"Repomix failed: {e}")`.
- **Missing diagnostics**: `subprocess.run(..., check=True)` does **not** capture stdout/stderr (no `capture_output=True` or `stderr=subprocess.PIPE`). When debugging a real Repomix failure, first **reproduce manually**: run the exact same command Repomix would use, in the same `cwd=target_dir`, with the same `env`, and capture output yourself — the GUI currently gives you only the return code via `e`, not the actual stderr from Repomix (e.g., "not a git repository," permission denied, unsupported flag). Recommend adding `capture_output=True, text=True` and surfacing `e.stdout`/`e.stderr` in the error dialog as a concrete fix when this is reported.
- **`FileNotFoundError`**: if `repomix_bin` is `None` (not on `PATH`) AND the `shell=True` fallback also can't resolve `repomix` as a shell command, `subprocess.run(..., shell=True)` typically still raises `CalledProcessError` with a nonzero exit from `cmd.exe` (e.g., `'repomix' is not recognized...`) rather than `FileNotFoundError`, since it's shell-mediated. Verify this exact behavior on the target Windows machine (`cmd.exe` vs PowerShell as default shell) before assuming which exception type surfaces.
- **Shell-injection / quoting edge case**: the `shell=True` fallback builds `f'repomix --style xml --output "{xml_path}" --quiet'`. Since `xml_path` is derived from `APP_DIR` (a fixed, trusted app install path), this is currently safe, but if `APP_DIR` or `xml_path` construction ever becomes user-influenced, this becomes an injection vector. Any PR that changes `xml_path` derivation must be reviewed for this.

### 3.2 `anthropic.AuthenticationError`
- Caught explicitly and mapped to a clear "Invalid API Key" dialog. Verify this actually fires for: expired key, revoked key, key with insufficient permissions/org access — all should surface as `AuthenticationError` per the `anthropic` SDK, but confirm SDK version pinned in `requirements-scaffolder.txt` (`anthropic>=0.40`) still raises this class name; **Anthropic SDK exception hierarchies have changed across versions** — pin and verify against the installed version, don't assume.

### 3.3 Bare `except Exception as e` (catch-all)
- This is the last line of defense for: `anthropic.APIStatusError`/`RateLimitError`/`BadRequestError` (e.g., context-window overflow from a very large `repo_context` — this is the **most likely real-world failure mode** given the entire repo is dumped into every prompt with `max_tokens=4096` and no truncation/chunking), `anthropic.APIConnectionError` (no internet / proxy issues), JSON/encoding errors reading `response.content[0].text` if the model ever returns a non-text content block (rare with `thinking: disabled`, but not impossible if the SDK/API contract changes), and any `OSError` writing output files (disk full, path too long — Windows `MAX_PATH` is a real risk here since `OUTPUT_ROOT` + safe project name + filename can exceed 260 chars on unpatched systems).
- **When triaging a report that just says "it crashed" or "nothing happened"**: check `status_label` text first — `_show_error` always calls `update_status(f"Error: {message}")` before the popup, so the status bar retains the last error even if the user dismissed the dialog. Ask the reporter for a screenshot of the status label, not just "it broke."
- **Silent-fail risk**: `response.content[0].text` will raise `IndexError` if the model returns an empty `content` list (e.g., the request was blocked/refused with no text block). This is **not explicitly handled** and will be caught only by the generic `except Exception`, producing an unhelpful raw `IndexError: list index out of range` in the dialog. When reproducing, deliberately trigger a refusal (e.g., prompt injection