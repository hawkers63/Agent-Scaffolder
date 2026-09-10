# Changelog

## Unreleased

Nothing yet.

## 1.3 — 2026-09-11

Batch-1 UX polish (session testing runs live verification only every 6th release —
see `notes/notes_006.txt`).

- **`_job_running` guard + busy cursor:** `start_generation` now no-ops if a job is
  already running (defensive; buttons already prevented this in practice), and the
  window cursor switches to the Windows wait cursor for the duration of a generation.
- **Close-during-job confirmation:** closing the window while a generation is in
  flight now asks for confirmation first, warning that it will abandon the job and
  may leave a temporary Repomix file behind, instead of silently killing it.

## 1.2 — 2026-09-10

Window identity, product icon, model picker, and repo professionalism pass on top of 1.1.

- **Settings → Generation model** dropdown (Claude Haiku 4.5, Sonnet 5, Opus 5) with prices in the label; choice saved to gitignored `model_choice.json`. Resolution order: `AGENT_SCAFFOLDER_MODEL` env override → Settings choice → `DEFAULT_MODEL`.
- Launcher no longer forces `AGENT_SCAFFOLDER_MODEL` in `Run-Agent-Scaffolder.bat` (superseded by the picker).
- Proprietary **LICENSE** (All Rights Reserved, hawkers63, 2026), copyright header on `agent_scaffolder.py`, stronger README copyright section, and `projects.example.json` template.
- `.gitignore` extended for `config.json` / temp / backup patterns; Repomix ignore pattern updated to `/.repomix-context*.xml`.
- **Window identity + product icon:** main-window heading aligned to "Agent Scaffolder" (version remains in the title bar only). Ships `icon/Agent.Scaffolder.ico` via `iconbitmap` on the main window and Settings (with a short CTk re-apply); removed uncleared `mstscax_13417.ico` (`notes/notes_005.txt`).


## 1.1 — 2026-09-10

Correctness and reliability pass over the 1.0 baseline, driven by the findings in
`notes/notes_001.txt` and `notes/notes_002.txt`. No new features, no change to the
single-file architecture, generation prompts, or the Desktop output contract.

- Worker setup (keyring read, Anthropic client construction, output-directory
  creation) now runs inside the same try/finally as the rest of generation, so a
  failure there still re-enables the UI.
- `projects.json` and `last_project.json` entries are validated (non-dict entries,
  non-string or empty name/path, reserved/duplicate names) instead of trusted as-is.
- The selected project directory and output folder are snapshotted on the UI thread
  before the background worker starts; the worker no longer reads live widgets.
- The three generated files are staged in memory and only written once all three
  requests succeed, and each response is checked for truncation or empty content
  before being staged. A failed generation now leaves previously-generated output
  completely untouched instead of a mix of new and old files.
- The temporary Repomix XML file uses a unique per-run name, so two running
  instances can no longer collide.
- Settings dialog: keyring reads/writes are guarded with a clear error dialog
  instead of crashing the UI thread; a deliberate empty save (clearing the key) no
  longer immediately reopens the Settings window.
- The status line now keeps the last success or error message instead of being
  overwritten the instant the job finishes.
- Raised the generation `max_tokens` from 4096 to 16000. The original limit
  truncated real output on a live run against this repository (even 8192 wasn't
  enough); 16000 is Anthropic's documented default ceiling for a non-streaming
  call, and since usage is billed by tokens actually generated, this doesn't
  increase cost unless a response genuinely needs the room.

This release includes a live Windows verification pass — real launch, Settings,
project selection, and a full real end-to-end generation run against this
repository's own codebase — not just a syntax/import check. See
`notes/notes_003.txt` (implementation) and `notes/notes_004.txt` (verification).

## 1.0 — 2026-09-10

Initial versioned baseline of the existing application.

- Project shortcuts, directory browsing and remembered local selection.
- Keyring-backed Anthropic credentials in a Settings dialog.
- Background Repomix packaging and generation of three Markdown configurations.
- Desktop output folder and Windows Explorer opening after successful generation.
- Explicit version displayed in the window title.
- Checkout-relative launcher with Python launcher/PATH fallback.
- Ignore rules, line-ending policy, setup and contribution documents, Windows syntax/import CI and pull-request template.
- Detailed baseline review in `notes/notes1.txt`.

The existing generation behaviour and documented limitations are retained. This release does not claim a live API integration test or complete GUI validation.
