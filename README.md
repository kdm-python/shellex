# Shell Examples (Shellex)

Shellex keeps shell command examples and notes in editable files, organised into groups. It stores commands as text; it never executes them.

## Install

Requires Python 3.9 or newer. From the project directory, install with `pip install .` (or `uv tool install .` to install the CLI as a tool). Then run `shellex --help`. For development, use `pip install -e .`.

## Usage

```sh
shellex list
shellex new journalctl
shellex add journalctl --command 'journalctl -xe' --description 'Recent messages'
shellex add journalctl --command 'journalctl -u ssh | grep "Failed"'
shellex examples journalctl
shellex update journalctl 1 --description 'Recent messages with context'
shellex update journalctl 1 --description ''  # Clear the description
shellex delete journalctl 1
shellex delete journalctl 1 --yes              # No confirmation
shellex notes journalctl
shellex notes journalctl --edit
```

Example numbers start at 1 and reflect the current CSV order. They are not persistent IDs: check `examples` again after rows are added, removed or reordered. Delete shows the selected example and asks for confirmation. In scripts, use `--yes`.

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

Group names start with a letter, number or underscore and may contain letters, numbers, underscores, hyphens and dots. Shellex writes CSV changes via a temporary file and checks for external changes before replacing the original. Avoid editing a CSV simultaneously in multiple programs: this check cannot eliminate every race between concurrent writers.

Colour is disabled for redirected output and when `NO_COLOR` is set. Use `shellex COMMAND --help` for command-specific help.

## Tests

```sh
python -m unittest discover -s tests
```
