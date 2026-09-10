# Agent Scaffolder

Version **1.0** — a Windows desktop utility that turns project source context into tailored Markdown agent instructions. It generates configuration documents for an AI assistant; it does not generate or execute an autonomous Python agent.

The single-file Python application uses CustomTkinter, Repomix and the Anthropic API. Select a project, save an API key in Settings, and choose **Generate Agents**.

## Requirements and setup

- Windows with Python 3.11, including Tk.
- Node.js/npm and the Repomix CLI on PATH.
- An Anthropic API key with access to the configured model.

Run from the checkout in PowerShell:

```powershell
python -m pip install -r requirements-scaffolder.txt
npm install -g repomix
repomix --version
python agent_scaffolder.py
```

Ensure `python --version` reports your intended Python 3.11 installation. Alternatively, double-click `Run-Agent-Scaffolder.bat`. It finds the application relative to itself and uses `py -3.11` when the Python launcher exists, otherwise `python` on PATH. It retains the optional `C:\nvm4w\nodejs` PATH entry. The checkout must be writable for local settings and temporary XML.

## Configuration and output

1. Save your API key in **Settings**. It is stored through `keyring` under service `AgentScaffolderApp`, account `AnthropicAPIKey`, rather than JSON.
2. Choose a listed project or **Other...**. Built-in shortcuts are the maintainer's defaults and may not exist on your machine.
3. Choose **Generate Agents** when a key and valid directory are available.

`projects.json` contains local shortcuts as a list of objects with non-empty `name` and `path` strings. It is seeded from built-in defaults when absent. Edit it while the app is closed, for example:

```json
[{"name": "My Project", "path": "D:\\Projects\\MyProject"}]
```

`last_project.json` remembers the selection. Both files are ignored by Git.

Three documents are saved under `%USERPROFILE%\Desktop\Agent Outputs\<project>`:

- `agents.md` — architecture and coding instructions.
- `bug_hunter.md` — testing and debugging instructions.
- `enhancement_agent.md` — feature and UI guidance.

Existing files with these names are overwritten. Review generated instructions before using them. Repomix writes temporary `.repomix-context.xml` in the application directory; the worker attempts cleanup on completion or failure.

## Model and data handling

The source default is `claude-sonnet-5`. This release does not certify provider model availability or API compatibility. Set `AGENT_SCAFFOLDER_MODEL` to an identifier available to your account if needed:

```powershell
$env:AGENT_SCAFFOLDER_MODEL = "your-available-model-id"
python agent_scaffolder.py
```

Generation sends the selected repository's packaged source to Anthropic in three sequential requests and can incur API charges. Review the target project's Repomix exclusions before generation; this checkout's `.gitignore` does not protect other target projects. Do not rely on packaging alone to remove sensitive content.

## Verification and development

```powershell
python -m compileall -q agent_scaffolder.py
python -c "import agent_scaffolder; print(agent_scaffolder.APP_VERSION)"
```

GitHub Actions runs syntax and import checks on Windows with Python 3.11. These checks do not launch the GUI, access stored credentials, invoke Repomix or make paid API requests.

Keep the single-file CustomTkinter architecture and follow `agents/enhancement_agent.md` for feature/UI work. See `CONTRIBUTING.md`, `CHANGELOG.md` and `notes/notes1.txt` for release scope and known limitations. No software licence is granted by this repository; that choice remains with the owner.
