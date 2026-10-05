"""Enables `python -m textstats`."""
import sys

if __package__:
    from .textstats import main
else:
    from textstats import main

if __name__ == "__main__":
    sys.exit(main())
