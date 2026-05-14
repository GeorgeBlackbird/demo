from __future__ import annotations

import argparse
from pathlib import Path

from . import copy_to, get_payload_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show payload path or copy exam solution files."
    )
    parser.add_argument(
        "--copy-to",
        type=Path,
        help="Destination directory where bundled files will be copied.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files that already exist in destination.",
    )
    args = parser.parse_args()

    if args.copy_to:
        destination = copy_to(args.copy_to, overwrite=args.overwrite)
        print(f"Copied payload to: {destination}")
        return

    print(get_payload_dir())


if __name__ == "__main__":
    main()
