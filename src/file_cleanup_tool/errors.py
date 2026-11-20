"""Errors raised by the library. The command line turns these into a short message and exit code 1."""


class CleanupError(Exception):
    """A problem the user can fix (bad path, bad plan file, unsafe destination)."""
