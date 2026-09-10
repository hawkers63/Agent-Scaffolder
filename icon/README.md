# Icon assets

Product window / taskbar icon: `Agent.Scaffolder.ico`.

`ScaffoldingApp` and `SettingsWindow` load this file via `iconbitmap` when present
(with a short delayed re-apply so CustomTkinter does not wipe it after first paint).

If the file is missing, the app keeps the default Tk/Python icon and still launches.
