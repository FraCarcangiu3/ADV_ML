#!/usr/bin/env python3
"""
Compatibility wrapper: delegates to database_fixer convert-flac subcommand.
"""

import sys

from fix_dataset.database_fixer import build_parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args(["convert-flac", *sys.argv[1:]])
    args.func(args)


if __name__ == "__main__":
    main()
