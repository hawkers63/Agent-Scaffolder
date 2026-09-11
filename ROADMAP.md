# ROADMAP.md — Agent Scaffolder

Current version: **1.13** (released 2026-09-11 — see `CHANGELOG.md` and `notes/notes_018.txt`).
`notes/notes_017.txt`; batch-2 live-verified in `notes/notes_016.txt`). This
roadmap sequences the work identified in the maintainer's own review notes
(`notes/notes_001.txt`, `notes/notes_002.txt`) plus ideas for turning this from a
working utility into a more capable desktop application. Nothing here is committed
until picked up in a session — treat it as a backlog. Record actual releases in
`CHANGELOG.md` plus a new `notes/notes_NNN.txt`, and bump `APP_VERSION` alongside them.

**Testing cadence (adopted 2026-09-11):** live end-to-end runs (real Repomix +
real Anthropic API calls) cost real money, so they're batched — five code-only
releases verified by source review / compile checks only, then a live test
pass, fixing whatever it finds, then repeat. Batch 1 was versions 1.3-1.7;
its live-test checkpoint (2026-09-11, `notes/notes_011.txt`) found **no
bugs**, so no separate "bugfix" release was needed. **Batch 2 (1.8-1.11)
is now complete** — numbered output, subprocess timeout, exclusion
passthrough, project manager — four items, not five; the backlog only had
four well-scoped items ready to go, and forcing a fifth just for symmetry
wasn't worth it. Three of the four hit real live-GUI automation hangs
during verification (unrelated to the app's own correctness — see
`notes/notes_013.txt` and `notes/notes_014.txt`); all were resolved via
isolated non-GUI tests instead, and a firm rule is now recorded in
MEMORY.md ("don't monkeypatch `subprocess.Popen` while driving a live
`app.mainloop()` with a background thread"). **Batch 2's live-test
checkpoint ran 2026-09-11** (`notes/notes_016.txt`): real end-to-end
confirmation that numbered output leaves an existing file alone and writes
a new numbered one, and that Repomix's `--ignore` flag genuinely excludes
matching content — **no bugs found**. Batch 3 starts fresh at the next
version. If a checkpoint finds bugs, that fix work should occupy the next
version number before the following batch's code-only releases begin.

## v1.1 — Correctness & reliability (shipped)
Both audits agree these are the changes that make current behaviour honest, before any
new feature work sits on top of it. **Implemented and released 2026-09-10** — see
`CHANGELOG.md`, `notes/notes_003.txt` (implementation) and `notes/notes_004.txt`
(live verification, including a real end-to-end generation run).
- [x] Wrap all of `run_scaffolding`'s setup (keyring read, client init, output-dir calc)
      inside the try/finally so a startup exception still re-enables controls.
- [x] Validate `projects.json` / `last_project.json` entries (non-dict, non-string,
      empty path) instead of trusting shape.
- [x] Snapshot `target_dir` and the output folder name on the UI thread before starting
      the worker; stop reading `project_menu.get()` from the background thread.
- [x] Stage the three generated files and only replace the real files once all three
      requests succeed; also validates each response (rejects empty/truncated output)
      before staging it.
- [x] Use a unique per-run temp XML path instead of the shared `.repomix-context.xml`
      (two running instances currently collide).
- [x] Guard keyring get/set/delete in Settings with an error dialog; stop the
      empty-save-then-auto-reopen loop (Settings no longer force-reopens itself after
      a deliberate clear — only `first_run_check` and the Generate-without-a-key guard
      open it automatically).
- [x] Keep the terminal success/error status on screen instead of letting
      `reset_buttons -> refresh_ui_state` clobber it immediately.

Not done in this pass (deliberately left for v1.2 per scope): reserved Windows device
names in `safe_folder_name`, and true crash-safe atomic writes (writes are staged in
memory and only hit disk after all three requests succeed, which resolves the reported
"mixed old/new files" failure mode, but isn't a temp-file+rename swap per file).

- [x] **New finding from the first live end-to-end run (2026-09-10), not in either
      original audit:** the hardcoded `max_tokens=4096` on the generation calls was too
      low — it truncated a real `agents.md` response against this repo's own codebase.
      The `stop_reason == "max_tokens"` check added above caught it cleanly (clear error,
      no corrupt file), but the underlying cap needed raising. Tried `8192` next — still
      truncated `bug_hunter.md`. Settled on **`max_tokens=16000`**, which is Anthropic's
      documented default ceiling for a non-streaming call (this app doesn't stream;
      Sonnet 5 supports up to 128K but that requires streaming to avoid HTTP timeouts).
      Confirmed working end-to-end: all three files generated in full, correct sizes,
      clean endings, Explorer opened to the real output folder. Since Anthropic bills by
      tokens actually generated and not by this ceiling, raising it doesn't add cost
      unless a response genuinely needs the room.

## Since 1.1 (unreleased — not yet in a tagged version)
- [x] **In-app generation model picker**, added 2026-09-10 at explicit user request
      (previously "rejected without an explicit product request" per notes_002.txt §8;
      that condition is now met). Settings gained a "Generation model:" dropdown listing
      the three current Anthropic tiers with live per-1M-token pricing: Claude Haiku 4.5
      ($1/$5), Claude Sonnet 5 ($2/$10, the previous hardcoded default), Claude Opus 5
      ($5/$25). Selection saves immediately to `model_choice.json` (local, gitignored,
      same pattern as `projects.json`). Resolution order: `AGENT_SCAFFOLDER_MODEL` env
      var (unchanged power-user/CI override — the picker disables itself and shows the
      active override when this is set) > the Settings choice > `DEFAULT_MODEL`
      (`claude-sonnet-5`, unchanged). Correcting a mid-conversation assumption: Sonnet
      4.6 was considered as a "cheaper" alternative but confirmed at $3/$15 per 1M —
      pricier than Sonnet 5 for an older model — so it was deliberately left out of the
      menu. `model_choice.json` is currently seeded to `claude-haiku-4-5` on this
      machine for cost-conscious iteration during development; change it via Settings
      any time. Live-verified: dropdown renders with correct pricing/em-dashes, opens
      and lists all three, selection persists to disk immediately and survives a
      dialog close/reopen, env-var-override disabling was code-reviewed (not yet
      GUI-tested with a real env var set). This superseded an earlier, cruder attempt
      at the same goal (a `Run-Agent-Scaffolder.bat` hardcoded env var) — reverted in
      favor of the picker.
- Also fixed while in this area: `.gitignore`'s `/.repomix-context.xml` entry didn't
  match the unique-per-run naming introduced in v1.1 (`.repomix-context-<hex>.xml`) —
  updated to `/.repomix-context*.xml`.

## v1.2 — UX polish (shipped, spread across releases 1.2–1.6)
- [x] Add a `_job_running` guard and busy cursor during generation; document (or handle)
      close-during-job. **Shipped in 1.3** (2026-09-11): `start_generation` no-ops while
      a job is already running, window cursor is "wait" during generation, and closing
      the window mid-job now asks for confirmation (warns it will abandon the job and
      may leave a temp Repomix file) instead of silently killing it. See
      `notes/notes_006.txt`.
- [x] ~~Fix `Other...` re-selection~~ — **not actually broken.** notes_002.txt's finding
      D was explicitly inferred without launching the GUI ("CTkOptionMenu typically does
      not fire command when the displayed value is selected again"). A live smoke test
      on 2026-09-10 (customtkinter 5.2.2) showed clicking the already-selected `Other...`
      *does* refire `on_project_selected` and reopens the folder picker as expected. No
      fix needed here; removed from the backlog.
- [x] Resolve window identity: one product name across the OS title bar and in-window
      heading; wire up a rights-cleared icon or stop documenting one that isn't shipped.
      Done 2026-09-10: in-window heading is now "Agent Scaffolder" (version stays in the
      OS title only). Product icon is `icon/Agent.Scaffolder.ico`, wired via `iconbitmap`
      on ScaffoldingApp and SettingsWindow (200ms re-apply for CTk). `mstscax_13417.ico`
      removed. Maintainer confirmed title-bar icon after relaunch; see `notes/notes_005.txt`.
- [x] `status_label` `justify="left"`; small copy pass on status strings and Settings.
      **Shipped in 1.5** (2026-09-11). See `notes/notes_008.txt`.
- [x] Align docs to the real `notes/notes_NNN.txt` naming. **Shipped in 1.6**
      (2026-09-11): fixed `CONTRIBUTING.md` (`notesN.txt` -> `notes_NNN.txt`) and
      this changelog's 1.0 entry (`notes1.txt` -> `notes_001.txt`). README
      already referenced `notes/` generically, not a stale filename, so it
      needed no change — the original finding overstated README's part in
      this. See `notes/notes_009.txt`.

## v1.3 — Feature expansion (needs a product decision first — see "Later" below)
- [x] Lightweight in-app project manager (add/edit/remove `projects.json` entries) as
      its own compact `CTkToplevel`, following the existing load/save JSON pattern.
      **Shipped in 1.11** (2026-09-11): opened from a new "Manage Projects..." button
      in Settings; add/edit/remove with validation, including the 1.10 `exclude`
      field; closing it refreshes the main dropdown, keeping the active target
      selected by path through a rename. See `notes/notes_015.txt`. **Closes out
      batch 2 (1.8-1.11).** Live-test checkpoint run 2026-09-11
      (`notes/notes_016.txt`): all pass, no bugs found.
- [x] Regenerate a single output file instead of always running all three.
      **Shipped in 1.7** (2026-09-11): "Files to generate:" checkboxes
      (`agents.md` / `bug_hunter.md` / `enhancement_agent.md`, all checked by
      default) filter which files trigger an Anthropic call; Repomix still
      packages once regardless (shared input). See `notes/notes_010.txt`.
      Closes out batch-1 (1.3-1.7). Live-test checkpoint run 2026-09-11
      (`notes/notes_011.txt`): all pass, no bugs found — see "Testing cadence" above.
- [x] Cancel button for an in-flight generation (join/kill the subprocess only).
      **Shipped in 1.4** (2026-09-11): Repomix now runs via `Popen` so Cancel can
      terminate it, plus a cancellation checkpoint before each Anthropic call and
      before writing files (a request already sent can't be recalled, but no
      further paid calls happen after cancel). See `notes/notes_007.txt`.
- [x] Bounded Repomix subprocess timeout. **Shipped in 1.9** (2026-09-11):
      5-minute `REPOMIX_TIMEOUT_SECONDS` ceiling; on expiry, terminate() with
      a kill() fallback, then a clear `ScaffoldingError` before any Anthropic
      call. See `notes/notes_013.txt`.
- [x] Optional Repomix exclusion passthrough. **Shipped in 1.10** (2026-09-11):
      a named `projects.json` entry can carry an `"exclude"` field
      (comma-separated `--ignore` patterns), passed straight through to
      Repomix on top of the target's own `.gitignore` (already respected by
      default). Not available for **Other…** (no persisted config to read
      from). See `notes/notes_014.txt`.
- [x] **Numbered output instead of overwrite** (explicit user request, 2026-09-11).
      **Shipped in 1.8** (2026-09-11): first generation keeps the plain filename;
      each later one gets the next free `_N` suffix, counted independently per
      file, filling the lowest free gap. The user's own phrasing ("agents_2.md and
      so on") settled the per-file-vs-shared-run-number question, so this shipped
      without a separate design-decision round. See `notes/notes_012.txt`.

## Distributable build (in progress, decided 2026-09-11)
Goal: a real `.exe` so this stops being a checkout-and-run tool, without
turning into an open-ended infra project. Decision made after discussion:
PyInstaller (not Nuitka — better track record with CustomTkinter's asset/
theme loading and `keyring`'s backend discovery) producing a portable
`.exe` that still expects Node.js + Repomix installed separately, with
clear guidance when they're missing, rather than bundling a full Node
runtime (bigger, more build complexity, another thing to keep in sync).
Revisit fully-bundled Node only if the pre-flight-and-guide approach turns
out to be a real adoption blocker.
- [x] Clear error when Repomix/Node.js is missing instead of a generic
      subprocess failure. **Shipped in 1.12** (2026-09-11): checks whether
      `node`/`npx` and `repomix` are findable on PATH when Repomix fails,
      and shows actionable install guidance instead of "Command 'repomix'
      returned non-zero exit status 1." See `notes/notes_017.txt`.
- [x] PyInstaller build config. **Shipped in 1.13** (2026-09-11): new
      `build-exe.ps1` + `requirements-build.txt`. `pyinstaller-hooks-contrib`
      already supplies a CustomTkinter hook (no manual asset `--add-data`
      needed); `keyring`'s Windows backend needed an explicit hidden-import.
      Built and smoke-tested a real `dist\Agent Scaffolder.exe` in a fully
      isolated temp directory (no source tree nearby) - launch, config
      persistence, and layout all confirmed via real screenshots. Surfaced
      and fixed two real bugs along the way: a frozen-build persistence bug
      (`APP_DIR` was resolving inside PyInstaller's temp extraction dir,
      which would have discarded every setting on each relaunch — new
      `RESOURCE_DIR` split fixes it) and a pre-existing main-window layout
      bug (fixed geometry never grew to fit the Cancel button + checkboxes
      added since 1.4/1.7, clipping the Settings button out of view
      entirely — affects source-run too). See `notes/notes_018.txt`.
      Not yet done: an end-to-end real generation through the built exe
      (launch/persistence/layout were the packaging-specific risks; the
      generation logic itself is unchanged from the already-verified
      source version).
- [ ] README "Download" / build-from-source docs reflecting the new `.exe`
      path alongside the existing checkout-and-run instructions.
- [ ] Code signing for the `.exe` (unsigned triggers Windows SmartScreen on
      another machine) — costs money for a cert; a separate decision, not
      started.
- [ ] Later, optional: a GitHub Actions release workflow that builds and
      attaches the `.exe` to a GitHub Release on tag push (ties into the
      existing README maintainer note "prefer creating a matching GitHub
      Release"). Not started — a real decision point on its own once the
      manual build path is proven.

## Later / needs discussion
Bigger bets — worth a decision before building:
- **Target the actual Claude Code subagent/skill format.** The tool currently emits
  three freeform Markdown files with no fixed schema. Claude Code specifically expects
  subagents as `.claude/agents/*.md` with YAML frontmatter (`name`, `description`,
  `tools`), and supports Skills under `.claude/skills/`. If Claude Code is the intended
  consumer, generating straight into that convention (optionally still exporting the
  current freeform docs for other assistants) would make outputs usable immediately
  instead of requiring manual wiring.
- **Multi-provider model choice.** An Anthropic-only model-*tier* picker (Haiku/Sonnet/
  Opus) shipped 2026-09-10 (see "Since 1.1" above). True multi-*provider* support (a
  non-Anthropic backend) is a separate, much larger idea and remains unrequested —
  revisit only if there's a real need to target non-Claude assistants.
- **Live API/model verification.** Live-verified multiple times now: 1.1
  (`notes/notes_004.txt`), 1.2 (`notes/notes_005.txt`, maintainer-confirmed), and the
  batch-1 checkpoint covering 1.3-1.7 (`notes/notes_011.txt`). Keep doing this at
  each cadence checkpoint rather than treating it as a one-time item.

## Explicitly out of scope unless requested again
See `notes/notes_002.txt` §8 — progress bars/spinners, grid()/place()/ttk/Qt/web UI
changes, a second credential store, writing generated files into the target repo, and
relocating the Desktop output root. Don't reintroduce these under a "polish" pass.

## Reference
- `notes/notes_001.txt` — architecture/robustness baseline audit.
- `notes/notes_002.txt` — UI/UX and feature-surface audit.
- `CHANGELOG.md` — released history; update alongside version bumps.
