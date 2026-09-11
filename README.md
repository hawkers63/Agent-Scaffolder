# Agent Scaffolder

**Turn any project folder into tailored AI agent instructions — on Windows, in one click.**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)](https://github.com/hawkers63/Agent-Scaffolder)
[![CI](https://github.com/hawkers63/Agent-Scaffolder/actions/workflows/ci.yml/badge.svg)](https://github.com/hawkers63/Agent-Scaffolder/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20All%20Rights%20Reserved-red)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v1.11-success)](CHANGELOG.md)

Version **1.11** — a Windows desktop utility that packages project source with Repomix and generates Markdown configuration documents for an AI assistant. It does **not** generate or run an autonomous Python agent.

Built as a single-file CustomTkinter app using the Anthropic API. Pick a project, save your API key in Settings, choose a model, then **Generate Agents**.

## Why it exists

Hand-writing agent instructions for every codebase is slow and drifts out of date. Agent Scaffolder reads the selected project’s packaged source and produces three role-specific Markdown files you can drop into an assistant workflow — architecture, debugging, and enhancement guidance tailored to *that* tree.

## Key features

- **Project shortcuts** — named paths in `projects.json`, editable in-app via **Manage Projects...** (Settings) or by hand, plus **Other…** for any folder
- **Optional per-project Repomix exclusion** — an `"exclude"` field passes patterns straight to Repomix's `--ignore`, on top of the target's own `.gitignore`
- **Secure API key storage** — Windows Credential Manager via `keyring` (never JSON)
- **In-app model picker** — Haiku 4.5, Sonnet 5 (default), or Opus 5, with optional env override
- **Repomix packaging** — XML context of the target repo for generation, with a bounded timeout so a hung or oversized repo can't stall a run indefinitely
- **Three agent documents, generate any subset** — `agents.md`, `bug_hunter.md`, `enhancement_agent.md`, each individually selectable so a re-run only pays for what you check
- **Cancel button** — stops an in-flight run (terminates Repomix, skips any remaining API calls)
- **Never overwrites past output** — a regeneration writes the next numbered file (`agents_2.md`, ...) instead of replacing a previous one
- **Desktop output** — writes under `%USERPROFILE%\Desktop\Agent Outputs\<project>` and opens Explorer on success
- **Reliable worker** — UI snapshots, staged writes (all-or-nothing), unique temp XML, clear status messages, busy cursor and close-during-job confirmation
- **One-click launcher** — `Run-Agent-Scaffolder.bat` with `py -3.11` / `python` fallback

## Release

| | |
| --- | --- |
| **Current** | **[v1.11](https://github.com/hawkers63/Agent-Scaffolder/releases/tag/v1.11)** (2026-09-11) |
| **App version** | `APP_VERSION = "1.11"` in `agent_scaffolder.py` |
| **Highlights** | Numbered output instead of overwrite (`agents_2.md`, ...); bounded Repomix subprocess timeout; optional per-project Repomix exclusion passthrough; in-app Project Manager (add/edit/remove `projects.json` shortcuts from Settings). Live-verified against real Repomix + Anthropic calls — see `notes/notes_016.txt`. |
| **Changelog** | Full notes in [CHANGELOG.md](CHANGELOG.md) |
| **Tags** | [`v1.11`](https://github.com/hawkers63/Agent-Scaffolder/releases/tag/v1.11) · [`v1.10`](https://github.com/hawkers63/Agent-Scaffolder/releases/tag/v1.10) · [`v1.9`](https://github.com/hawkers63/Agent-Scaffolder/releases/tag/v1.9) · [`v1.8`](https://github.com/hawkers63/Agent-Scaffolder/releases/tag/v1.8) · [full history](https://github.com/hawkers63/Agent-Scaffolder/tags) |


> Maintainers: when you cut a release, bump `APP_VERSION`, update this **Release** table, add a CHANGELOG entry, and tag (`vX.Y`). Prefer creating a matching GitHub Release so the badges and links stay honest.

## Prerequisites

- Windows 10/11 with **Python 3.11** (Tk included)
- **Node.js / npm** and the **Repomix** CLI on `PATH`
- An **Anthropic API key** with access to the models you select

## Installation

From the checkout in PowerShell:

```powershell
python -m pip install -r requirements-scaffolder.txt
npm install -g repomix
repomix --version
python agent_scaffolder.py
```

Confirm `python --version` is the intended 3.11 install. Or double-click `Run-Agent-Scaffolder.bat` — it resolves the app relative to itself, prefers `py -3.11`, falls back to `python`, and keeps the optional `C:\nvm4w\nodejs` PATH entry. The checkout must be writable for local settings and temporary XML.

## Usage

1. Open **Settings**, paste your Anthropic API key, and pick a generation model if you want something other than the default.
2. Choose a listed project or **Other…**. Built-in shortcuts are maintainer defaults and may be missing on your machine.
3. Click **Generate Agents** when a key and valid directory are ready.
4. Review the three Markdown files under Desktop → `Agent Outputs` before using them.

### Keyboard / UI notes

This is a mouse-driven CustomTkinter UI (project menu, Generate, Settings). There is no separate global shortcut table in the app today.

## Configuration

| File / setting | Purpose | Tracked in Git? |
| --- | --- | --- |
| `projects.json` | List of `{ "name", "path", "exclude"? }` shortcuts | No (gitignored) |
| `projects.example.json` | Clean template for local shortcuts | Yes |
| `last_project.json` | Remembers last selection | No |
| `model_choice.json` | Last Settings model id | No |
| Windows keyring | API key under service `AgentScaffolderApp`, account `AnthropicAPIKey` | N/A (OS store) |
| `AGENT_SCAFFOLDER_MODEL` | Env override; disables the Settings picker when set | N/A |

Example `projects.json` (edit while the app is closed). The optional
`"exclude"` field is a comma-separated list of Repomix `--ignore` patterns,
passed through on top of the target's own `.gitignore` (which Repomix
already respects by default) — useful when a project's `.gitignore` doesn't
cover everything you want kept out of the packaged context:

```json
[
  {
    "name": "Example Project",
    "path": "D:\\Projects\\ExampleProject",
    "exclude": "*.log,node_modules/**"
  }
]
```

`exclude` isn't available for the **Other…** folder picker, since there's no
persisted config to read a pattern from — only named `projects.json` entries.

Model resolution order: `AGENT_SCAFFOLDER_MODEL` env var → Settings choice → `DEFAULT_MODEL` (`claude-sonnet-5`).

```powershell
$env:AGENT_SCAFFOLDER_MODEL = "your-available-model-id"
python agent_scaffolder.py
```

This release does not certify provider model availability or API compatibility.

## Output

Files are written to `%USERPROFILE%\Desktop\Agent Outputs\<project>` (existing names are overwritten only after all three generations succeed):

| File | Role |
| --- | --- |
| `agents.md` | Architecture and coding instructions |
| `bug_hunter.md` | Testing and debugging instructions |
| `enhancement_agent.md` | Feature and UI guidance |

Repomix writes a temporary `.repomix-context-<random>.xml` under the app directory (unique per run); the worker attempts cleanup on completion or failure.

## Model and data handling

Generation sends the selected repository’s packaged source to Anthropic in up to three sequential requests (fewer if you uncheck files) and can incur API charges. Review the target project’s Repomix exclusions before generation; this checkout’s `.gitignore` does not protect other target projects — add an `"exclude"` field to that project's `projects.json` entry if its own `.gitignore` doesn't cover everything. Do not rely on packaging alone to remove sensitive content.

Displayed Settings prices (per 1M tokens, input/output, display-only): Haiku 4.5 ≈ $1/$5 · Sonnet 5 ≈ $2/$10 · Opus 5 ≈ $5/$25. A cheaper model may write shallower instructions for a large codebase.

## Verification and development

```powershell
python -m compileall -q agent_scaffolder.py
python -c "import agent_scaffolder; print(agent_scaffolder.APP_VERSION)"
```

GitHub Actions runs syntax and import checks on Windows with Python 3.11. Those checks do not launch the GUI, access stored credentials, invoke Repomix, or make paid API requests.

Keep the single-file CustomTkinter architecture and follow `agents/enhancement_agent.md` for feature/UI work. See `CONTRIBUTING.md`, `CHANGELOG.md`, and `notes/` for release scope and known limitations.

## Copyright & License

Copyright (c) 2026 Mark Hawksworth. All rights reserved.

This project is proprietary software. No open-source or permissive licence is granted. Without prior written consent from Mark Hawksworth, you may not copy, reproduce, redistribute, modify, reverse-engineer, or use this software for commercial purposes.

See [LICENSE](LICENSE) for the full All Rights Reserved notice.
