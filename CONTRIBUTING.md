# Contributing

Issues and pull requests are welcome.

- Keep it standard library only. The tool is meant to run on locked-down work machines where `pip install` is blocked.
- Library code in `src/file_cleanup_tool` must not print or call `sys.exit`; raise `CleanupError` and let `cli.py` report it.
- Add a test for every change. Run `python -m unittest discover -s tests -t . -v` before opening a pull request.
- Never commit real inventories, plans or explorer pages: they contain real file names.
- Anything that copies files must stay a dry run unless `--go` is given, and must never modify or delete the source.
