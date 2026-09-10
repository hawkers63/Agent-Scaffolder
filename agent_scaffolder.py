import json
import os
import shutil
import subprocess
import threading
import customtkinter as ctk
import anthropic
import keyring
from tkinter import filedialog, messagebox

APP_VERSION = "1.0"

# Credential Manager service for Anthropic API key (never store keys in files)
SERVICE_NAME = "AgentScaffolderApp"
ACCOUNT_NAME = "AnthropicAPIKey"

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_FILE = os.path.join(APP_DIR, "projects.json")
LAST_PROJECT_FILE = os.path.join(APP_DIR, "last_project.json")

# Desktop output folder — generated agents land here so they are easy to find.
# Prefer USERPROFILE so this works on Hawkeye (C:\Users\Administrator) and other profiles.
OUTPUT_ROOT = os.path.join(
    os.environ.get("USERPROFILE", r"C:\Users\Administrator"),
    "Desktop",
    "Agent Outputs",
)

# Env-configurable model. Default: claude-sonnet-5 (current Anthropic Sonnet).
# Override with AGENT_SCAFFOLDER_MODEL if needed (e.g. claude-sonnet-4-6).
MODEL = os.environ.get("AGENT_SCAFFOLDER_MODEL", "claude-sonnet-5")

DEFAULT_PROJECTS = [
    {"name": "Desktop Vista", "path": r"D:\Desktop_Vista"},
    {"name": "Scriptorium", "path": r"C:\Scriptorium"},
    {"name": "Logacta", "path": r"C:\Logacta"},
    {"name": "Plume", "path": r"C:\Plume"},
    {"name": "EuroDatabase", "path": r"C:\EuroDatabase"},
]

OTHER_LABEL = "Other..."


def ensure_projects_file():
    """Seed projects.json with the default five entries if missing."""
    if os.path.isfile(PROJECTS_FILE):
        return
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_PROJECTS, f, indent=2)


def load_projects():
    ensure_projects_file()
    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return list(DEFAULT_PROJECTS)


def load_last_project_path():
    try:
        with open(LAST_PROJECT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("path"):
            return data["path"]
        if isinstance(data, str) and data:
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


def safe_folder_name(name):
    """Make a filesystem-safe folder name from a project label or path basename."""
    cleaned = "".join(c if (c.isalnum() or c in (" ", "-", "_")) else "_" for c in name)
    cleaned = " ".join(cleaned.split()).strip(" ._")
    return cleaned or "Project"


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, *args, on_saved=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_saved = on_saved
        self.title("Settings")
        self.geometry("400x200")
        self.grab_set()

        self.title_label = ctk.CTkLabel(self, text="API Configuration", font=("Segoe UI", 16, "bold"))
        self.title_label.pack(pady=(15, 10))

        self.key_label = ctk.CTkLabel(self, text="Anthropic API Key:")
        self.key_label.pack(anchor="w", padx=20)

        self.api_key_entry = ctk.CTkEntry(self, width=360, show="*")
        self.api_key_entry.pack(padx=20, pady=(0, 15))

        existing_key = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
        if existing_key:
            self.api_key_entry.insert(0, existing_key)

        self.save_btn = ctk.CTkButton(self, text="Save Key", command=self.save_settings)
        self.save_btn.pack()

    def save_settings(self):
        new_key = self.api_key_entry.get().strip()
        if new_key:
            keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, new_key)
        else:
            try:
                keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
            except keyring.errors.PasswordDeleteError:
                pass

        callback = self.on_saved
        self.destroy()
        if callback:
            callback()


class ScaffoldingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Agent Scaffolder v{APP_VERSION}")
        self.geometry("520x340")

        self.projects = load_projects()
        self.target_dir = None
        self.settings_window = None
        self._suppress_project_event = False

        self.title_label = ctk.CTkLabel(
            self, text="Project Agent Generator", font=("Segoe UI", 18, "bold")
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

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray", wraplength=460)
        self.status_label.pack(pady=(0, 10))

        self.generate_btn = ctk.CTkButton(self, text="Generate Agents", command=self.start_generation)
        self.generate_btn.pack(pady=5)

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

    def has_api_key(self):
        return bool(keyring.get_password(SERVICE_NAME, ACCOUNT_NAME))

    def project_path_valid(self):
        return bool(self.target_dir and os.path.isdir(self.target_dir))

    def refresh_ui_state(self):
        key_ok = self.has_api_key()
        path_ok = self.project_path_valid()
        if key_ok and path_ok:
            self.generate_btn.configure(state="normal")
            self.status_label.configure(text="Ready to generate")
        elif not key_ok:
            self.generate_btn.configure(state="disabled")
            self.status_label.configure(text="API key required - enter it in Settings")
        else:
            self.generate_btn.configure(state="disabled")
            self.status_label.configure(text="Select a valid project directory")

    def refresh_key_state(self):
        self.refresh_ui_state()
        if not self.has_api_key():
            self.open_settings()

    def first_run_check(self):
        if not self.has_api_key():
            self.open_settings()
        self.refresh_ui_state()

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self, on_saved=self.refresh_key_state)
            self.settings_window.focus()
        else:
            self.settings_window.focus()

    def start_generation(self):
        if not self.has_api_key():
            self.open_settings()
            return
        if not self.project_path_valid():
            self.status_label.configure(text="Select a valid project directory")
            return
        self.generate_btn.configure(state="disabled")
        self.settings_btn.configure(state="disabled")
        self.project_menu.configure(state="disabled")
        self.update_status("Packaging codebase with Repomix...")
        threading.Thread(target=self.run_scaffolding, daemon=True).start()

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

    def run_scaffolding(self):
        api_key = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
        if not api_key:
            self._show_error(
                "API Key Missing",
                "API Key missing. Please set it in Settings.",
            )
            self.after(0, self.reset_buttons)
            return

        target_dir = self.target_dir
        if not target_dir or not os.path.isdir(target_dir):
            self._show_error("Invalid Directory", "Invalid project directory.")
            self.after(0, self.reset_buttons)
            return

        output_dir = self._output_folder_for_selection()
        # Keep temporary Repomix XML under APP_DIR so we do not litter the project root.
        xml_path = os.path.join(APP_DIR, ".repomix-context.xml")
        env = self._build_subprocess_env()
        client = anthropic.Anthropic(api_key=api_key)

        try:
            os.makedirs(output_dir, exist_ok=True)

            repomix_bin = shutil.which("repomix", path=env.get("PATH"))
            # Absolute --output under APP_DIR; still run against the selected project (cwd=target_dir).
            if repomix_bin:
                subprocess.run(
                    [repomix_bin, "--style", "xml", "--output", xml_path, "--quiet"],
                    cwd=target_dir,
                    env=env,
                    check=True,
                )
            else:
                subprocess.run(
                    f'repomix --style xml --output "{xml_path}" --quiet',
                    cwd=target_dir,
                    env=env,
                    shell=True,
                    check=True,
                )

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

            for agent in agents:
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
                    model=MODEL,
                    max_tokens=4096,
                    thinking={"type": "disabled"},
                    messages=[{"role": "user", "content": prompt_text}],
                )

                out_path = os.path.join(output_dir, agent["name"])
                with open(out_path, "w", encoding="utf-8") as out_file:
                    out_file.write(response.content[0].text.strip())

            self.update_status("Cleaning up temporary files...")
            if os.path.exists(xml_path):
                try:
                    os.remove(xml_path)
                except OSError:
                    pass

            done_msg = f"Agent scaffolding complete!\nOutput: {output_dir}"
            self.update_status(done_msg)
            self.after(0, lambda d=output_dir: self._open_output_folder(d))

        except subprocess.CalledProcessError as e:
            self._show_error("Repomix Error", f"Repomix failed: {e}")
        except anthropic.AuthenticationError:
            self._show_error(
                "Authentication Error",
                "Invalid API Key. Please update it in Settings.",
            )
        except Exception as e:
            self._show_error("API/System Error", str(e))
        finally:
            # Always try to remove temp XML under APP_DIR
            if os.path.exists(xml_path):
                try:
                    os.remove(xml_path)
                except OSError:
                    pass
            self.after(0, self.reset_buttons)

    def reset_buttons(self):
        self.settings_btn.configure(state="normal")
        self.project_menu.configure(state="normal")
        self.refresh_ui_state()


if __name__ == "__main__":
    ensure_projects_file()
    app = ScaffoldingApp()
    app.mainloop()
