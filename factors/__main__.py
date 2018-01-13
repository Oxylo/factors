"""Main entry point module"""
import argparse
import logging
import sys

logger = logging.getLogger(__name__)

# Main CLI.
parser = argparse.ArgumentParser(description='factors CLI')
parser.add_argument('-v', '--version', action='store_true', help='print version')

subparsers = parser.add_subparsers(dest="command", help='available commands')


def main(args=None):
    """
    Parse args for CLI

    Parameters
    ----------
    args : list of str, optional

    Raises
    ------
    SystemExit
        If duplicate requirements are found or we failed to compile any of the documents
    """
    if args is None:
        args = sys.argv[1:]

    args = parser.parse_args(args)
    if args.version:
        cmd_version()
        return

    parser.print_help()


def cmd_version() -> None:
    """Prints and returns the current version to the command line."""
    from factors import __version__
    print(f"factors v{__version__}")


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s %(lineno)d %(message)s", stream=sys.stdout, level=logging.INFO)
    main()
