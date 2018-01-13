"""CLI utility to run shell commands in parallel."""
import argparse
import subprocess
import sys
from multiprocessing import Pool

parser = argparse.ArgumentParser(description="run a bunch of commands in parallel")
parser.add_argument('cmd', nargs="+", help='a command')
parser.add_argument('-j', type=int, dest='jobs', default=None, help='number of workers')
parser.add_argument('--ordered', action='store_true', default=False,
                    help='run commands in order (default is unordered)')


def run_cmd(cmd):
    p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return cmd, p.returncode, p.stdout.decode(errors="surrogateescape"), p.stderr.decode(errors="surrogateescape")


if __name__ == "__main__":
    args = parser.parse_args()
    with Pool(args.jobs) as pool:
        returncodes = []
        map_func = pool.imap if args.ordered else pool.imap_unordered
        for cmd, returncode, stdout, stderr in map_func(run_cmd, args.cmd):
            print(f">>> {cmd} returned {returncode}")
            if stdout:
                print(stdout)
            if stderr:
                print(stderr)
            returncodes.append(returncode)
    returncode = 0 if all(rc == 0 for rc in returncodes) else 1
    sys.exit(returncode)
