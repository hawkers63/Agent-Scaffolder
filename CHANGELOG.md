# Changelog

## Unreleased

Nothing yet.

## 1.12 — 2026-09-11

First step toward a distributable build (see `notes/notes_017.txt`).

- **Clear error when Repomix/Node.js is missing.** If Repomix fails to run,
  the app now checks whether Node.js (`node`/`npx`) and Repomix itself are
  actually findable on PATH and shows an actionable message — "install
  Node.js from nodejs.org, then run `npm install -g repomix`" — instead of
  the previous generic "Repomix failed: Command 'repomix' returned
  non-zero exit status 1." This only changes the failure-path message;
  normal operation (Repomix found and working) is unchanged.

## 1.11 — 2026-09-11

Batch-2 feature work, fourth and final release (see `notes/notes_015.txt`).

- **In-app Project Manager.** Settings gained a "Manage Projects..." button
  opening a compact window to add, edit (including rename), and remove
  `projects.json` shortcuts without hand-editing the file — including
  setting the same optional `exclude` field added in 1.10. Validates name
  (non-empty, not `Other...`, unique) and path (non-empty) before saving;
  each add/edit/remove writes to `projects.json` immediately. Closing the
  manager refreshes the main window's project dropdown, keeping the
  currently active target directory selected by path (so a rename follows
  it) rather than resetting to whatever was last saved on disk.

This closes out batch 2 (1.8-1.11).

**Live-test checkpoint (2026-09-11, see `notes/notes_016.txt`): all pass, no
bugs found.** Numbered output confirmed end-to-end with a real Anthropic
call: an existing `agents.md` was correctly left untouched and a new
`agents_2.md` written instead. Exclusion passthrough confirmed against the
real Repomix binary: a custom pattern (`--ignore "*.secretdata"`) correctly
excluded a matching file's content from the packaged output, while an
identical run without it included it. No fix release needed — batch 3
starts fresh at the next version.

## 1.10 — 2026-09-11

Batch-2 feature work, third release (see `notes/notes_014.txt`).

- **Optional Repomix exclusion passthrough.** A named `projects.json` entry
  can now include an `"exclude"` field (comma-separated Repomix `--ignore`
  patterns, e.g. `"*.log,node_modules/**"`); when set, it's passed straight
  through to Repomix on top of the target's own `.gitignore` (which Repomix
  already respects by default). Malformed values (wrong type, blank) are
  dropped without rejecting the whole project entry. Not available for the
  ad-hoc **Other…** folder picker, since there's no persisted config to
  read a pattern from. README's project-config table and example JSON
  updated.

## 1.9 — 2026-09-11

Batch-2 feature work, second release (see `notes/notes_013.txt`).

- **Bounded Repomix subprocess timeout.** Repomix now has a 5-minute
  (`REPOMIX_TIMEOUT_SECONDS`) ceiling instead of waiting indefinitely. On
  expiry the process is terminated (falling back to a hard kill if it
  doesn't exit within 5 more seconds) and generation stops with a clear
  error before any Anthropic call is made — no wasted API cost from a
  hung or pathologically large target project. Same terminate/kill
  mechanism as the v1.4 Cancel button, just triggered by a timer instead
  of a user click.

## 1.8 — 2026-09-11

Batch-2 feature work, first release (see `notes/notes_012.txt`).

- **Numbered output instead of silent overwrite** (explicit user request):
  a fresh generation no longer overwrites `agents.md` / `bug_hunter.md` /
  `enhancement_agent.md` in place. The first-ever generation for a project
  still writes the plain filename; every later generation writes the next
  free numbered variant instead (`agents_2.md`, `agents_3.md`, ...) so a
  bad or unwanted regeneration never destroys a working set of
  instructions. Counted independently per file (matches v1.7's per-file
  selection: regenerating only `agents.md` five times produces
  `agents.md`, `agents_2.md`, ... `agents_5.md` while `bug_hunter.md`
  stays untouched at its original name). Fills the lowest free gap rather
  than always incrementing past the highest number that ever existed, so
  deleting a numbered file frees its slot again. Numbers grow unbounded —
  no automatic pruning of old generations (not requested; would need its
  own design if wanted later). The completion status now lists the actual
  filenames written, since they're no longer predictable from the
  checkboxes alone.

## 1.7 — 2026-09-11

Batch-1 feature work, final release of this batch (see `notes/notes_010.txt`).

- **Regenerate a single file (or any subset)** instead of always running all
  three: a "Files to generate:" row of checkboxes (`agents.md`,
  `bug_hunter.md`, `enhancement_agent.md`, all checked by default) lets you
  pick which files to generate. Repomix still packages the repo once
  regardless of selection (it's the shared input), but only the checked
  files trigger an Anthropic call — directly cuts per-run API cost when you
  only need to redo one file. Generate is disabled with a
  "Select at least one file to generate" status if nothing is checked; the
  completion message now states how many files were generated.
- Checkboxes lock (disabled) for the duration of a run, alongside the
  existing project/Settings locks, and unlock in `reset_buttons`.

This closes out the batch adopted 2026-09-11 (1.3-1.7). Per the agreed
cadence, a live end-to-end test pass covering everything in this batch was
run immediately after, with fixes reserved for whatever it found.

**Live-test checkpoint (2026-09-11, see `notes/notes_011.txt`): all pass, no
bugs found.** Real Repomix + real Anthropic (Haiku 4.5) calls confirmed:
unchecking two files and generating only `agents.md` made exactly 1 API
call (not 3), left the other two files byte-for-byte untouched, and showed
the wait cursor / disabled checkbox / enabled Cancel button mid-run;
cancelling immediately after starting made 0 API calls and ended cleanly at
"Cancelled."; the Settings window's heading and env-override note (1.5)
both render with the exact expected text. Since nothing needed fixing, no
6th "bugfix" version was cut — the next release starts fresh at 1.8 with
real feature work (a "regenerate to a numbered file instead of overwriting"
request came in during this checkpoint; see ROADMAP.md).

## 1.6 — 2026-09-11

Batch-1 docs alignment (see `notes/notes_009.txt`).

- Fixed stale `notes/notesN.txt` reference in `CONTRIBUTING.md` — now says
  `notes/notes_NNN.txt` with an example filename.
- Fixed stale `notes/notes1.txt` reference in this changelog's 1.0 entry —
  now points at `notes/notes_001.txt` with a note on the rename history.
  README already referenced `notes/` generically and needed no change.
- The README **Release** table/badge is intentionally left at v1.2 — per its
  own maintainer note, it tracks tagged releases, and 1.3–1.6 aren't tagged
  yet (tagging/pushing remains an explicit per-request action in this repo).
  It will be updated in one pass when this batch is tagged.

## 1.5 — 2026-09-11

Batch-1 UX polish, copy pass (see `notes/notes_008.txt`).

- `status_label` now sets `justify="left"` (previously unset — only mattered
  once a status message wrapped to more than one line).
- Copy pass: "API key required — set it in Settings" (was a hyphen, now an
  em dash matching the rest of the app's punctuation style); the Settings
  window's inner heading changed from "API Configuration" to "Settings" to
  match its title bar and the fact it now also holds the model picker; the
  environment-override note now explains *why* the model dropdown is
  disabled instead of just restating the variable; the close-during-job
  confirmation now points at the new Cancel button as the non-destructive
  alternative.

## 1.4 — 2026-09-11

Batch-1 UX polish, continued (see `notes/notes_007.txt`).

- **Cancel button:** a new "Cancel" button is enabled while a generation is in
  flight. It terminates the running Repomix subprocess and stops before any
  further Anthropic calls; a request already sent to the API cannot be
  recalled, but this stops the run before any *subsequent* paid calls, which
  also doubles as a cost control. The Repomix invocation switched from
  `subprocess.run` to `subprocess.Popen` so it can be terminated from the UI
  thread. Cancelling shows "Cancelled." in the status line rather than an
  error dialog. Known limitation: on the rare shell=True Repomix fallback
  path (used only if `repomix` isn't found via `shutil.which`), terminate()
  kills the `cmd.exe` wrapper but not a grandchild process it may have spawned.

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
- Detailed baseline review in `notes/notes_001.txt` (originally written as
  `notes1.txt`, later split into `notes_001.txt` and `notes_002.txt` and
  renamed to the current `notes_NNN.txt` convention).

The existing generation behaviour and documented limitations are retained. This release does not claim a live API integration test or complete GUI validation.
