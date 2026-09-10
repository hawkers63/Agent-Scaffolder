# Agent Scaffolder

**Turn any project folder into tailored AI agent instructions — on Windows, in one click.**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)](https://github.com/hawkers63/Agent-Scaffolder)
[![CI](https://github.com/hawkers63/Agent-Scaffolder/actions/workflows/ci.yml/badge.svg)](https://github.com/hawkers63/Agent-Scaffolder/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20All%20Rights%20Reserved-red)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v1.2-success)](CHANGELOG.md)

Version **1.2** — a Windows desktop utility that packages project source with Repomix and generates Markdown configuration documents for an AI assistant. It does **not** generate or run an autonomous Python agent.

Built as a single-file CustomTkinter app using the Anthropic API. Pick a project, save your API key in Settings, choose a model, then **Generate Agents**.

## Why it exists

Hand-writing agent instructions for every codebase is slow and drifts out of date. Agent Scaffolder reads the selected project’s packaged source and produces three role-specific Markdown files you can drop into an assistant workflow — architecture, debugging, and enhancement guidance tailored to *that* tree.

## Key features

- **Project shortcuts** — named paths in `projects.json`, plus **Other…** for any folder
- **Secure API key storage** — Windows Credential Manager via `keyring` (never JSON)
- **In-app model picker** — Haiku 4.5, Sonnet 5 (default), or Opus 5, with optional env override
- **Repomix packaging** — XML context of the target repo for generation
- **Three agent documents** — `agents.md`, `bug_hunter.md`, `enhancement_agent.md`
- **Desktop output** — writes under `%USERPROFILE%\Desktop\Agent Outputs\<project>` and opens Explorer on success
- **Reliable worker** — UI snapshots, staged writes (all-or-nothing), unique temp XML, clear status messages
- **One-click launcher** — `Run-Agent-Scaffolder.bat` with `py -3.11` / `python` fallback

## Release

| | |
| --- | --- |
| **Current** | **[v1.2](https://github.com/hawkers63/Agent-Scaffolder/releases/tag/v1.2)** (2026-09-10) |
| **App version** | `APP_VERSION = "1.2"` in `agent_scaffolder.py` |
| **Highlights** | Window identity + `Agent.Scaffolder.ico`; in-app model picker; proprietary LICENSE / copyright; README Release section |
| **Changelog** | Full notes in [CHANGELOG.md](CHANGELOG.md) |
| **Tags** | [`v1.2`](https://github.com/hawkers63/Agent-Scaffolder/releases/tag/v1.2) · [`v1.1`](https://github.com/hawkers63/Agent-Scaffolder/releases/tag/v1.1) · [`v1.0`](https://github.com/hawkers63/Agent-Scaffolder/releases/tag/v1.0) |


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
| `projects.json` | List of `{ "name", "path" }` shortcuts | No (gitignored) |
| `projects.example.json` | Clean template for local shortcuts | Yes |
| `last_project.json` | Remembers last selection | No |
| `model_choice.json` | Last Settings model id | No |
| Windows keyring | API key under service `AgentScaffolderApp`, account `AnthropicAPIKey` | N/A (OS store) |
| `AGENT_SCAFFOLDER_MODEL` | Env override; disables the Settings picker when set | N/A |

Example `projects.json` (edit while the app is closed):

```json
[
  {
    "name": "Example Project",
    "path": "D:\\Projects\\ExampleProject"
  }
]
```

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

Generation sends the selected repository’s packaged source to Anthropic in three sequential requests and can incur API charges. Review the target project’s Repomix exclusions before generation; this checkout’s `.gitignore` does not protect other target projects. Do not rely on packaging alone to remove sensitive content.

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
