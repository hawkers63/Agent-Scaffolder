# Contributing

Use Python 3.11 and install `requirements-scaffolder.txt`. Follow the instructions in `agents/`, particularly `agents/enhancement_agent.md` for UI work.

Keep changes incremental and preserve the single-file architecture, CustomTkinter widgets, `pack()` layout, keyring storage and Desktop output contract. Keep subprocess/API work off the Tk main loop and marshal widget operations through the UI thread. Add focused regression tests for behaviour fixes, including failure and cleanup paths.

Before submitting:

1. Run the syntax and import commands in the README.
2. Run focused checks for changed behaviour and record results.
3. Manually check relevant Windows UI flows and disclose checks not performed.
4. Update the changelog and add the next `notes/notes_NNN.txt` (zero-padded, e.g. `notes_009.txt`) for release/review reports, preserving earlier notes.
5. Review the staged diff for credentials, local settings and packaged source.

Dependency minimums are not a lockfile. Record versions when reporting regressions. Explain the reason and impact before adding frameworks or changing model parameters or output behaviour.
