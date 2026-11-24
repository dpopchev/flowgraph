"""The commands that take the lock of their record: every one that writes it (B-0035).

A command is locked unless it is listed as one that writes nothing, so a command added later is
locked until it is listed.
"""

import argparse

# The commands that write nothing, so they never take the lock; config show is one too.
READS = ("status", "watch", "show", "about", "brief", "knowledge", "terms", "graph", "goal")


def takes_lock(args: argparse.Namespace) -> bool:
    """Whether the command the arguments name writes, so takes the lock of its record.

    False for no command, for a command of READS and for config show; true for every other.
    """
    if args.command is None or args.command in READS:
        return False
    return not (args.command == "config" and getattr(args, "action", None) == "show")
