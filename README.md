# Shell Examples (Shellex)

Shellex keeps shell command examples and notes in editable files, organised into groups. It stores commands as text; it never executes them.

## Install

Requires [uv](https://docs.astral.sh/uv/) and Python 3.9 or newer. From the project directory, run `uv sync` to create and install the locked project environment. Run the CLI with `uv run shellex --help`; uv also syncs the environment automatically when needed. To install a standalone `shellex` command on your PATH, use `uv tool install .` instead.

## Usage

```sh
uv run shellex --help
```

The examples below use the standalone `shellex` command. If working from the project without a tool installation, prefix each command with `uv run`.

```sh
shellex list
shellex new journalctl
shellex add journalctl --command 'journalctl -xe' --description 'Recent messages'
shellex add journalctl --command 'journalctl -u ssh | grep "Failed"'
shellex examples journalctl
shellex search journalctl 'recent'
shellex search journalctl 'journalctl' --field command
shellex search journalctl 'messages' --field description
shellex copy journalctl 1
shellex update journalctl 1 --description 'Recent messages with context'
shellex update journalctl 1 --description ''  # Clear the description
shellex delete journalctl 1
shellex delete journalctl 1 --yes              # No confirmation
shellex notes journalctl
shellex notes journalctl --edit
```

Example numbers start at 1 and reflect the current CSV order. They are not persistent IDs: check `examples` again after rows are added, removed or reordered. Delete shows the selected example and asks for confirmation. In scripts, use `--yes`.

Search matches substrings without regard to case, in both fields by default. Results retain their original row numbers for use with `copy`, `update` or `delete`. Copy places the exact command text on the system clipboard without executing it. It uses `pbcopy` on macOS, `clip.exe` on Windows, or `wl-copy`, `xclip` or `xsel` in a suitable Linux graphical session; install the relevant clipboard tool if needed.

A group name such as `sudo` does not require quotes simply because it is also a command. Quote command text so your shell passes it literally instead of interpreting pipes, redirects, variables or substitutions. In bash and zsh, single quotes are usually useful; to include a literal single quote, one option is `--command 'echo '\''hello'\'''`. Quoting rules vary by shell.

## Files

By default data lives in `~/.shellex`:

```text
~/.shellex/journalctl/
├── journalctl.csv
└── journalctl.md
```

CSV files have the header `command,description`. Descriptions may be empty. Use a CSV-aware editor for commands containing commas, quotes or newlines. An empty CSV file is accepted; malformed data is reported without being overwritten. Markdown notes are rendered in a terminal and printed as raw Markdown when redirected. Existing `<group>.txt` notes are supported as plain text when no Markdown file exists; to migrate, rename the file to `<group>.md`. If both exist, Markdown takes precedence.

`notes --edit` uses `VISUAL`, then `EDITOR`, then `vi`. The editor setting may include arguments (for example `EDITOR='nvim -f'`).

Set `SHELLEX_DIR` to change the default location, or pass `--data-dir` before the subcommand to override it:

```sh
shellex --data-dir tests/examples list
```

Shellex loads settings from `.env` via python-dotenv, without overriding variables already set in the environment. Copy `.env.example` to `.env` for a local starting point; `.env` is ignored by Git.

Group names start with a letter, number or underscore and may contain letters, numbers, underscores, hyphens and dots. Shellex writes CSV changes via a temporary file and checks for external changes before replacing the original. Avoid editing a CSV simultaneously in multiple programs: this check cannot eliminate every race between concurrent writers.

Colour is disabled for redirected output and when `NO_COLOR` is set. Use `shellex COMMAND --help` for command-specific help.

## Tests

```sh
uv run python -m unittest discover -s tests
```
