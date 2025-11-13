"""Command-line entry point for generating the PayPal daily digest."""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

from .config import load_config
from .digest import run


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the PayPal daily news digest")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional override for the digest output path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(verbose=args.verbose)

    config = load_config()
    if args.output:
        config = replace(config, digest_dir=args.output.parent)
    result = run(config)
    if args.output:
        args.output.write_text(result.digest.to_markdown(), encoding="utf-8")


if __name__ == "__main__":
    main()
