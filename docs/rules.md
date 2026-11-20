# Rules

`file-cleanup suggest` turns a rules file into a plan, so you start from a draft instead of a blank page.

```
file-cleanup scan  "C:\Shared\Team" --out inventory.csv
file-cleanup suggest --rules rules.json --inventory inventory.csv --out suggested_plan.csv
file-cleanup explore "C:\Shared\Team" --plan suggested_plan.csv     # review the result as a picture
```

Nothing is copied by `suggest`. See `examples/rules.example.json` for a starting point.

## File layout

```json
{
  "archive_root": "Archive",
  "default_action": "undecided",
  "rules": [ ... ]
}
```

| Key | Meaning |
|---|---|
| `archive_root` | Top folder for archived files. Default `Archive`. |
| `default_action` | What happens to files no rule matches: `undecided` (default) or `keep`. |
| `rules` | Tried in order. **The first rule that matches a file wins.** |

## A rule

| Key | Meaning |
|---|---|
| `name` | Shown in the plan's `rule` column, so you can see why a file was placed. |
| `match` | Conditions. The rule matches when **all** of them are true. Required. |
| `action` | `move` (default), `archive`, `keep` or `undecided`. |
| `folder` | Destination folder for `move`. Use `/` or `\`. May use fields (below). Optional for `archive`. |
| `rename` | Optional new file name, using fields. Default keeps the original name. |

## Match conditions

| Key | True when |
|---|---|
| `ext` | The extension is in the list: `[".pdf", ".docx"]` (the dot is optional). |
| `name_regex` | The file name matches this regular expression (searched, not anchored). Use `(?i)` for case-insensitive. |
| `path_regex` | The full relative path matches this regular expression. |
| `path_glob` | The path matches a pattern like `*/photos/*` (case-insensitive, `/` separators). A list means any of them. |
| `top_folder` | The first folder in the path equals this name. |
| `min_size_kb`, `max_size_kb` | Size limits in KB. |
| `older_than_days`, `older_than_years` | Last modified at least this long ago. |
| `newer_than_days` | Last modified within this many days. |

A file with no readable modified date never matches an age condition.

## Fields for `folder` and `rename`

`{name}` file name, `{stem}` name without extension, `{ext}` extension with the dot, `{parent}` the folder it is in,
`{top}` the first folder, `{path}` the whole old path, `{year}`, `{month}`, `{modified}` from the modified date.

Example: `"folder": "Finance/Invoices/{year}"`, `"rename": "{modified} {name}"`.

## Errors

A mistake in the rules file stops the command with a message that names the rule, for example
`rule 'Photos': unknown match key 'extension'`.
