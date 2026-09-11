"""
Copyright (c) 2026 Mark Hawksworth (hawkers63). All rights reserved.

This file is proprietary to Mark Hawksworth (hawkers63). Unauthorised copying, reproduction,
redistribution, modification, reverse-engineering, or commercial use of this
software, in whole or in part, is strictly prohibited without prior written
consent from the copyright holder. See LICENSE in the project root.
"""
import json
import os
import shutil
import subprocess
import threading
import uuid
import customtkinter as ctk
import anthropic
import keyring
from tkinter import filedialog, messagebox

APP_VERSION = "1.10"

# Credential Manager service for Anthropic API key (never store keys in files)
SERVICE_NAME = "AgentScaffolderApp"
ACCOUNT_NAME = "AnthropicAPIKey"

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_FILE = os.path.join(APP_DIR, "projects.json")
LAST_PROJECT_FILE = os.path.join(APP_DIR, "last_project.json")
MODEL_CHOICE_FILE = os.path.join(APP_DIR, "model_choice.json")

# Desktop output folder — generated agents land here so they are easy to find.
# Prefer USERPROFILE so this works on Hawkeye (C:\Users\Administrator) and other profiles.
OUTPUT_ROOT = os.path.join(
    os.environ.get("USERPROFILE", r"C:\Users\Administrator"),
    "Desktop",
    "Agent Outputs",
)

# Repomix should finish in well under a minute for a typical project; this is
# a safety net against a hung or pathologically large repo, not a normal-case
# limit. On expiry the process is terminated/killed and generation stops
# before any Anthropic call is made.
REPOMIX_TIMEOUT_SECONDS = 300

# Generation model. Resolution order (see resolve_model()): the
# AGENT_SCAFFOLDER_MODEL env var (power-user/CI override) > the choice saved
# from Settings (model_choice.json) > DEFAULT_MODEL. Prices are per 1M tokens,
# input/output, and are display-only context for the Settings picker.
DEFAULT_MODEL = "claude-sonnet-5"
MODEL_CHOICES = [
    ("Claude Haiku 4.5 — fastest & cheapest ($1 / $5)", "claude-haiku-4-5"),
    ("Claude Sonnet 5 — balanced, default ($2 / $10)", "claude-sonnet-5"),
    ("Claude Opus 5 — highest quality ($5 / $25)", "claude-opus-5"),
]

DEFAULT_PROJECTS = [
    {"name": "Desktop Vista", "path": r"D:\Desktop_Vista"},
    {"name": "Scriptorium", "path": r"C:\Scriptorium"},
    {"name": "Logacta", "path": r"C:\Logacta"},
    {"name": "Plume", "path": r"C:\Plume"},
    {"name": "EuroDatabase", "path": r"C:\EuroDatabase"},
]

OTHER_LABEL = "Other..."


class ScaffoldingError(Exception):
    """A recognized generation failure with a message safe to show the user."""


class GenerationCancelled(Exception):
    """Raised internally when the user cancels an in-flight generation."""


def ensure_projects_file():
    """Seed projects.json with the default five entries if missing."""
    if os.path.isfile(PROJECTS_FILE):
        return
    try:
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PROJECTS, f, indent=2)
    except OSError:
        pass


def _valid_project_entries(data):
    """Keep only well-formed {name, path} entries with non-empty, unique names.
    An optional "exclude" string (Repomix --ignore patterns, comma-separated)
    is kept if present and non-empty; a malformed exclude value is dropped
    without rejecting the whole entry."""
    valid = []
    seen_names = set()
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        path = entry.get("path")
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(path, str) or not path.strip():
            continue
        name = name.strip()
        if name == OTHER_LABEL or name in seen_names:
            continue
        seen_names.add(name)
        clean = {"name": name, "path": path}
        exclude = entry.get("exclude")
        if isinstance(exclude, str) and exclude.strip():
            clean["exclude"] = exclude.strip()
        valid.append(clean)
    return valid


def load_projects():
    ensure_projects_file()
    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            valid = _valid_project_entries(data)
            if valid:
                return valid
    except (OSError, json.JSONDecodeError):
        pass
    return list(DEFAULT_PROJECTS)


def load_last_project_path():
    try:
        with open(LAST_PROJECT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            path = data.get("path")
            if isinstance(path, str) and path.strip():
                return path
        elif isinstance(data, str) and data.strip():
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return None


def save_last_project_path(path):
    try:
        with open(LAST_PROJECT_FILE, "w", encoding="utf-8") as f:
            json.dump({"path": path}, f, indent=2)
    except OSError:
        pass


def load_model_choice():
    try:
        with open(MODEL_CHOICE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            model_id = data.get("model_id")
            if isinstance(model_id, str) and any(model_id == mid for _, mid in MODEL_CHOICES):
                return model_id
    except (OSError, json.JSONDecodeError):
        pass
    return None


def save_model_choice(model_id):
    try:
        with open(MODEL_CHOICE_FILE, "w", encoding="utf-8") as f:
            json.dump({"model_id": model_id}, f, indent=2)
    except OSError:
        pass


def resolve_model():
    """AGENT_SCAFFOLDER_MODEL env var overrides everything; else the Settings
    choice; else DEFAULT_MODEL."""
    env_override = os.environ.get("AGENT_SCAFFOLDER_MODEL")
    if env_override:
        return env_override
    return load_model_choice() or DEFAULT_MODEL


def safe_folder_name(name):
    """Make a filesystem-safe folder name from a project label or path basename."""
    cleaned = "".join(c if (c.isalnum() or c in (" ", "-", "_")) else "_" for c in name)
    cleaned = " ".join(cleaned.split()).strip(" ._")
    return cleaned or "Project"


def _next_available_path(directory, filename):
    """First run keeps the plain filename; each later run for the same file
    gets the next free _N suffix (agents.md, agents_2.md, agents_3.md, ...),
    so a fresh generation never overwrites a previous one."""
    candidate = os.path.join(directory, filename)
    if not os.path.exists(candidate):
        return candidate
    base, ext = os.path.splitext(filename)
    n = 2
    while True:
        candidate = os.path.join(directory, f"{base}_{n}{ext}")
        if not os.path.exists(candidate):
            return candidate
        n += 1


def _extract_text_response(response, agent_name):
    """Pull generated Markdown out of an Anthropic response, or raise a clear error."""
    if getattr(response, "stop_reason", None) == "max_tokens":
        raise ScaffoldingError(f"{agent_name}: response was truncated (hit the token limit)")
    blocks = getattr(response, "content", None)
    if not blocks or getattr(blocks[0], "type", None) != "text" or not (blocks[0].text or "").strip():
        raise ScaffoldingError(f"{agent_name}: model returned no text content")
    return blocks[0].text.strip()


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, *args, on_saved=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_saved = on_saved
        self.title("Settings")
        self.geometry("400x340")
        self.grab_set()
        icon_path = os.path.join(APP_DIR, "icon", "Agent.Scaffolder.ico")
        if os.path.isfile(icon_path):
            try:
                self.iconbitmap(icon_path)
                self.after(200, lambda p=icon_path: self.iconbitmap(p))
            except Exception:
                pass

        self.title_label = ctk.CTkLabel(self, text="Settings", font=("Segoe UI", 16, "bold"))
        self.title_label.pack(pady=(15, 10))

        self.key_label = ctk.CTkLabel(self, text="Anthropic API Key:")
        self.key_label.pack(anchor="w", padx=20)

        self.api_key_entry = ctk.CTkEntry(self, width=360, show="*")
        self.api_key_entry.pack(padx=20, pady=(0, 15))

        try:
            existing_key = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception as e:
            existing_key = None
            messagebox.showerror(
                "Credential Store Error", f"Could not read the stored API key: {e}"
            )
        if existing_key:
            self.api_key_entry.insert(0, existing_key)

        self.save_btn = ctk.CTkButton(self, text="Save Key", command=self.save_settings)
        self.save_btn.pack(pady=(0, 15))

        self.model_label = ctk.CTkLabel(self, text="Generation model:")
        self.model_label.pack(anchor="w", padx=20)

        self._label_to_id = dict(MODEL_CHOICES)
        self._id_to_label = {mid: label for label, mid in MODEL_CHOICES}

        env_override = os.environ.get("AGENT_SCAFFOLDER_MODEL")
        current_id = env_override or load_model_choice() or DEFAULT_MODEL
        current_label = self._id_to_label.get(current_id, current_id)

        self.model_menu = ctk.CTkOptionMenu(
            self,
            values=[label for label, _ in MODEL_CHOICES],
            width=360,
            command=self.on_model_selected,
        )
        self.model_menu.set(current_label)
        self.model_menu.pack(padx=20, pady=(4, 4))

        if env_override:
            self.model_menu.configure(state="disabled")
            self.model_note = ctk.CTkLabel(
                self,
                text=(
                    "Model choice is locked by the AGENT_SCAFFOLDER_MODEL "
                    f"environment variable ({env_override})."
                ),
                text_color="gray",
                wraplength=360,
                justify="left",
            )
            self.model_note.pack(padx=20, pady=(0, 10))

    def on_model_selected(self, choice):
        model_id = self._label_to_id.get(choice)
        if model_id:
            save_model_choice(model_id)

    def save_settings(self):
        new_key = self.api_key_entry.get().strip()
        try:
            if new_key:
                keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, new_key)
            else:
                try:
                    keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
                except keyring.errors.PasswordDeleteError:
                    pass
        except Exception as e:
            messagebox.showerror("Credential Store Error", f"Could not save the API key: {e}")
            return

        callback = self.on_saved
        self.destroy()
        if callback:
            callback()


class ScaffoldingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Agent Scaffolder v{APP_VERSION}")
        self.geometry("520x340")
        self._apply_window_icon()

        self.projects = load_projects()
        self.target_dir = None
        self.settings_window = None
        self._suppress_project_event = False
        self._job_running = False
        self._cancel_requested = False
        self._current_process = None
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.title_label = ctk.CTkLabel(
            self, text="Agent Scaffolder", font=("Segoe UI", 18, "bold")
        )
        self.title_label.pack(pady=(16, 4))

        self.choose_label = ctk.CTkLabel(self, text="Choose project:")
        self.choose_label.pack(anchor="w", padx=24)

        names = [p["name"] for p in self.projects] + [OTHER_LABEL]
        self.project_menu = ctk.CTkOptionMenu(
            self, values=names, command=self.on_project_selected, width=360
        )
        self.project_menu.pack(padx=24, pady=(4, 8))

        self.path_label = ctk.CTkLabel(
            self, text="No project selected", text_color="gray", wraplength=460, justify="left"
        )
        self.path_label.pack(padx=24, pady=(0, 8))

        self.files_label = ctk.CTkLabel(self, text="Files to generate:")
        self.files_label.pack(anchor="w", padx=24)

        self.file_row = ctk.CTkFrame(self, fg_color="transparent")
        self.file_row.pack(padx=24, pady=(4, 8), anchor="w")

        self.file_checks = {}
        for fname in ("agents.md", "bug_hunter.md", "enhancement_agent.md"):
            cb = ctk.CTkCheckBox(self.file_row, text=fname, command=self.refresh_ui_state)
            cb.select()
            cb.pack(side="left", padx=(0, 12))
            self.file_checks[fname] = cb

        self.status_label = ctk.CTkLabel(
            self, text="Ready", text_color="gray", wraplength=460, justify="left"
        )
        self.status_label.pack(pady=(0, 10))

        self.generate_btn = ctk.CTkButton(self, text="Generate Agents", command=self.start_generation)
        self.generate_btn.pack(pady=5)

        self.cancel_btn = ctk.CTkButton(
            self,
            text="Cancel",
            fg_color="#8B2E2E",
            hover_color="#6E2424",
            command=self.cancel_generation,
            state="disabled",
        )
        self.cancel_btn.pack(pady=5)

        self.settings_btn = ctk.CTkButton(
            self,
            text="Settings",
            fg_color="gray",
            hover_color="#555555",
            command=self.open_settings,
        )
        self.settings_btn.pack(pady=5)

        self._restore_last_selection()
        self.after(200, self.first_run_check)


    def _apply_window_icon(self):
        """Set the Windows title-bar / taskbar icon from icon/Agent.Scaffolder.ico."""
        icon_path = os.path.join(APP_DIR, "icon", "Agent.Scaffolder.ico")
        if not os.path.isfile(icon_path):
            return
        try:
            self.iconbitmap(icon_path)
            # CustomTkinter can replace the icon after the first paint on some builds.
            self.after(200, lambda p=icon_path: self.iconbitmap(p))
        except Exception:
            # Icon failure must not block launch; default Tk icon remains.
            pass

    def _restore_last_selection(self):
        last = load_last_project_path()
        if last:
            for p in self.projects:
                if os.path.normcase(os.path.abspath(p["path"])) == os.path.normcase(
                    os.path.abspath(last)
                ):
                    self._suppress_project_event = True
                    self.project_menu.set(p["name"])
                    self._suppress_project_event = False
                    self._set_target(p["path"], remember=False)
                    return
            # Custom / Other path remembered
            if os.path.isdir(last):
                self._suppress_project_event = True
                self.project_menu.set(OTHER_LABEL)
                self._suppress_project_event = False
                self._set_target(last, remember=False)
                return
        # Default to first project that exists, else first entry
        for p in self.projects:
            if os.path.isdir(p["path"]):
                self._suppress_project_event = True
                self.project_menu.set(p["name"])
                self._suppress_project_event = False
                self._set_target(p["path"], remember=False)
                return
        if self.projects:
            self._suppress_project_event = True
            self.project_menu.set(self.projects[0]["name"])
            self._suppress_project_event = False
            self._set_target(self.projects[0]["path"], remember=False)

    def on_project_selected(self, choice):
        if self._suppress_project_event:
            return
        if choice == OTHER_LABEL:
            selected = filedialog.askdirectory(title="Select project directory")
            if selected:
                self._set_target(selected, remember=True)
            else:
                # Revert menu to previous named project if possible
                if self.target_dir:
                    for p in self.projects:
                        if os.path.normcase(os.path.abspath(p["path"])) == os.path.normcase(
                            os.path.abspath(self.target_dir)
                        ):
                            self._suppress_project_event = True
                            self.project_menu.set(p["name"])
                            self._suppress_project_event = False
                            return
                self.refresh_ui_state()
            return
        for p in self.projects:
            if p["name"] == choice:
                self._set_target(p["path"], remember=True)
                return

    def _set_target(self, path, remember=True):
        self.target_dir = path
        if remember and path:
            save_last_project_path(path)
        exists = bool(path and os.path.isdir(path))
        marker = "" if exists else " (path missing)"
        self.path_label.configure(text=f"Target: {path}{marker}" if path else "No project selected")
        self.refresh_ui_state()

    def _output_folder_for_selection(self):
        """Primary write location: OUTPUT_ROOT\\<safe_project_name>."""
        choice = self.project_menu.get()
        if choice == OTHER_LABEL:
            base = os.path.basename(os.path.normpath(self.target_dir or "Project"))
            name = safe_folder_name(base)
        else:
            name = safe_folder_name(choice)
        return os.path.join(OUTPUT_ROOT, name)

    def _selected_exclude_patterns(self):
        """Repomix --ignore patterns from the current named project's optional
        "exclude" field in projects.json. None for Other... (no persisted
        config to read one from) or if the field isn't set."""
        choice = self.project_menu.get()
        if choice == OTHER_LABEL:
            return None
        for p in self.projects:
            if p["name"] == choice:
                return p.get("exclude")
        return None

    def has_api_key(self):
        try:
            return bool(keyring.get_password(SERVICE_NAME, ACCOUNT_NAME))
        except Exception:
            return False

    def project_path_valid(self):
        return bool(self.target_dir and os.path.isdir(self.target_dir))

    def _selected_agent_files(self):
        return [name for name, cb in self.file_checks.items() if cb.get()]

    def refresh_ui_state(self, update_status_text=True):
        key_ok = self.has_api_key()
        path_ok = self.project_path_valid()
        files_ok = bool(self._selected_agent_files())
        if key_ok and path_ok and files_ok:
            self.generate_btn.configure(state="normal")
            if update_status_text:
                self.status_label.configure(text="Ready to generate")
        elif not key_ok:
            self.generate_btn.configure(state="disabled")
            if update_status_text:
                self.status_label.configure(text="API key required — set it in Settings")
        elif not path_ok:
            self.generate_btn.configure(state="disabled")
            if update_status_text:
                self.status_label.configure(text="Select a valid project directory")
        else:
            self.generate_btn.configure(state="disabled")
            if update_status_text:
                self.status_label.configure(text="Select at least one file to generate")

    def first_run_check(self):
        if not self.has_api_key():
            self.open_settings()
        self.refresh_ui_state()

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self, on_saved=self.refresh_ui_state)
            self.settings_window.focus()
        else:
            self.settings_window.focus()

    def start_generation(self):
        if self._job_running:
            return
        if not self.has_api_key():
            self.open_settings()
            return
        if not self.project_path_valid():
            self.status_label.configure(text="Select a valid project directory")
            return
        selected_files = self._selected_agent_files()
        if not selected_files:
            self.status_label.configure(text="Select at least one file to generate")
            return
        # Snapshot the selection on the UI thread; the worker never touches
        # target_dir, project_menu, or the file checkboxes again once it starts.
        target_dir = self.target_dir
        output_dir = self._output_folder_for_selection()
        exclude_patterns = self._selected_exclude_patterns()
        self._job_running = True
        self._cancel_requested = False
        self.configure(cursor="wait")
        self.generate_btn.configure(state="disabled")
        self.settings_btn.configure(state="disabled")
        self.project_menu.configure(state="disabled")
        for cb in self.file_checks.values():
            cb.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.update_status("Packaging codebase with Repomix...")
        threading.Thread(
            target=self.run_scaffolding,
            args=(target_dir, output_dir, selected_files, exclude_patterns),
            daemon=True,
        ).start()

    def cancel_generation(self):
        """Best-effort cancel: terminates the Repomix subprocess if it's still
        running, and skips any remaining Anthropic calls at the next checkpoint.
        Cannot recall an Anthropic request already in flight."""
        if not self._job_running or self._cancel_requested:
            return
        self._cancel_requested = True
        self.cancel_btn.configure(state="disabled")
        self.update_status("Cancelling...")
        proc = self._current_process
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass

    def _on_close(self):
        if self._job_running:
            proceed = messagebox.askyesno(
                "Generation in progress",
                "A generation is still running — use Cancel instead if you just want "
                "to stop it. Closing now will abandon the job and may leave a "
                "temporary Repomix file behind. Close anyway?",
                icon="warning",
            )
            if not proceed:
                return
        self.destroy()

    def update_status(self, text):
        self.after(0, lambda: self.status_label.configure(text=text))

    def _show_error(self, title, message):
        self.update_status(f"Error: {message}")
        self.after(0, lambda: messagebox.showerror(title, message))

    def _open_output_folder(self, folder):
        try:
            subprocess.Popen(["explorer.exe", folder], shell=False)
        except OSError:
            pass

    def _build_subprocess_env(self):
        env = os.environ.copy()
        path_parts = []
        nvm_nodejs = r"C:\nvm4w\nodejs"
        if os.path.isdir(nvm_nodejs):
            path_parts.append(nvm_nodejs)
        local_nvm = os.path.join(os.environ.get("LOCALAPPDATA", ""), "nvm")
        if local_nvm and os.path.isdir(local_nvm):
            path_parts.append(local_nvm)
        if path_parts:
            env["PATH"] = os.pathsep.join(path_parts) + os.pathsep + env.get("PATH", "")
        return env

    def run_scaffolding(self, target_dir, output_dir, selected_files, exclude_patterns):
        # Unique per-run temp XML under APP_DIR so concurrent instances don't collide,
        # and everything below (including the keyring read) sits inside one
        # try/finally so any failure still re-enables the UI.
        xml_path = os.path.join(APP_DIR, f".repomix-context-{uuid.uuid4().hex}.xml")

        try:
            api_key = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
            if not api_key:
                raise ScaffoldingError("API Key missing. Please set it in Settings.")

            model_id = resolve_model()
            env = self._build_subprocess_env()
            client = anthropic.Anthropic(api_key=api_key)

            os.makedirs(output_dir, exist_ok=True)

            repomix_bin = shutil.which("repomix", path=env.get("PATH"))
            # Absolute --output under APP_DIR; still run against the selected project (cwd=target_dir).
            # Popen (not run) so cancel_generation() can terminate it from the UI thread.
            # Note: in the shell=True fallback, terminate() only kills the cmd.exe
            # wrapper, not a repomix process it may have spawned underneath.
            # exclude_patterns (projects.json's optional per-project "exclude" field)
            # is passed straight through as Repomix's own --ignore patterns, on top
            # of the target's own .gitignore, which Repomix already respects by default.
            if repomix_bin:
                cmd = [repomix_bin, "--style", "xml", "--output", xml_path, "--quiet"]
                if exclude_patterns:
                    cmd += ["--ignore", exclude_patterns]
                proc = subprocess.Popen(cmd, cwd=target_dir, env=env)
            else:
                cmd = f'repomix --style xml --output "{xml_path}" --quiet'
                if exclude_patterns:
                    cmd += f' --ignore "{exclude_patterns}"'
                proc = subprocess.Popen(cmd, cwd=target_dir, env=env, shell=True)
            self._current_process = proc
            try:
                returncode = proc.wait(timeout=REPOMIX_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                self._current_process = None
                raise ScaffoldingError(
                    f"Repomix did not finish within {REPOMIX_TIMEOUT_SECONDS} seconds "
                    "and was stopped. The target project may be too large, or Repomix "
                    "may be stuck."
                )
            self._current_process = None
            if self._cancel_requested:
                raise GenerationCancelled()
            if returncode != 0:
                raise subprocess.CalledProcessError(returncode, "repomix")

            with open(xml_path, "r", encoding="utf-8") as f:
                repo_context = f.read()

            agents = [
                {
                    "name": "agents.md",
                    "role": (
                        "General project architect. Define the tech stack, core coding standards, "
                        "file structures, and strict execution rules for this specific project."
                    ),
                },
                {
                    "name": "bug_hunter.md",
                    "role": (
                        "Quality assurance and debugging specialist. Focus strictly on how to test, "
                        "trace exceptions, and handle edge cases specific to the dependencies used here."
                    ),
                },
                {
                    "name": "enhancement_agent.md",
                    "role": (
                        "Feature development and UI/UX specialist. Outline the design language, "
                        "GUI widget standards, and state management patterns found in this codebase."
                    ),
                },
            ]
            agents = [a for a in agents if a["name"] in selected_files]

            # Stage the selected responses in memory first. Nothing on disk is
            # touched until every requested file has succeeded, so a failure
            # partway through leaves the previous output files exactly as they were.
            generated = {}
            for agent in agents:
                if self._cancel_requested:
                    raise GenerationCancelled()
                self.update_status(f"Generating {agent['name']}...")

                prompt_text = (
                    f"You are an expert AI software architect. Analyze the provided repository context.\n\n"
                    f"<repository_context>\n{repo_context}\n</repository_context>\n\n"
                    f"Generate a comprehensive system prompt/agent configuration for the following role:\n"
                    f"ROLE: {agent['role']}\n\n"
                    f"Tailor the instructions strictly to the architecture, dependencies, and coding patterns "
                    f"found in the repository context. "
                    f"Output ONLY the raw Markdown content for the file. Do not include introductory text "
                    f"or markdown fences."
                )

                response = client.messages.create(
                    model=model_id,
                    # 4096 and then 8192 both truncated real "comprehensive" docs on
                    # live use (see notes/notes_003.txt addendum). 16000 is Anthropic's
                    # documented default ceiling for a non-streaming call (this one is
                    # non-streaming); Sonnet 5 supports up to 128K but that requires
                    # streaming to avoid HTTP timeouts. Anthropic bills by tokens
                    # actually generated, not by this ceiling, so raising it doesn't
                    # cost more unless the response genuinely needs the room.
                    max_tokens=16000,
                    thinking={"type": "disabled"},
                    messages=[{"role": "user", "content": prompt_text}],
                )

                generated[agent["name"]] = _extract_text_response(response, agent["name"])

            if self._cancel_requested:
                raise GenerationCancelled()

            self.update_status("Writing generated files...")
            written_paths = []
            for name, text in generated.items():
                out_path = _next_available_path(output_dir, name)
                with open(out_path, "w", encoding="utf-8") as out_file:
                    out_file.write(text)
                written_paths.append(out_path)

            count = len(written_paths)
            file_word = "file" if count == 1 else "files"
            written_names = ", ".join(os.path.basename(p) for p in written_paths)
            done_msg = (
                f"Agent scaffolding complete! ({count} {file_word}: {written_names})\n"
                f"Output: {output_dir}"
            )
            self.update_status(done_msg)
            self.after(0, lambda d=output_dir: self._open_output_folder(d))

        except GenerationCancelled:
            self.update_status("Cancelled.")
        except subprocess.CalledProcessError as e:
            self._show_error("Repomix Error", f"Repomix failed: {e}")
        except anthropic.AuthenticationError:
            self._show_error(
                "Authentication Error",
                "Invalid API Key. Please update it in Settings.",
            )
        except ScaffoldingError as e:
            self._show_error("Generation Error", str(e))
        except Exception as e:
            self._show_error("API/System Error", str(e))
        finally:
            if os.path.exists(xml_path):
                try:
                    os.remove(xml_path)
                except OSError:
                    pass
            self.after(0, self.reset_buttons)

    def reset_buttons(self):
        self._job_running = False
        self._current_process = None
        self.configure(cursor="")
        self.settings_btn.configure(state="normal")
        self.project_menu.configure(state="normal")
        for cb in self.file_checks.values():
            cb.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        # Restore button enablement without clobbering the success/error text
        # the job just posted; the next user action refreshes it normally.
        self.refresh_ui_state(update_status_text=False)


if __name__ == "__main__":
    ensure_projects_file()
    app = ScaffoldingApp()
    app.mainloop()
