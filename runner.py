#!/usr/bin/env python
import os
import pipes
import daemon
import argparse
import subprocess

from lockfile.pidlockfile import PIDLockFile


def main():
    args = parse_args()
    context = daemon.DaemonContext(
        working_directory=args.cwd or '.',
        detach_process=True
    )
    if args.stderr:
        ensure_dir(args.stderr)
        context.stderr = open(args.stderr, 'a+')
    if args.stdout:
        ensure_dir(args.stdout)
        context.stdout = open(args.stdout, 'a+')
    if args.pid_file:
        context.pidfile = PIDLockFile(args.pid_file)
    if args.user:
        context.uid = get_uid(args.user)
    with context:
        exec_process(args)


def exec_process(args):
    subprocess.Popen(' '.join(pipes.quote(arg) for arg in args.command),
                     shell=True).wait()


def parse_args():
    parser = argparse.ArgumentParser(description="Run a command as a daemon")
    parser.add_argument("-o", "--stdout", help="Standard output destination")
    parser.add_argument("-w", "--cwd", help="Working directory")
    parser.add_argument("-e", "--stderr", help="Standard error destination")
    parser.add_argument("-p", "--pid-file", help="PID file location")
    parser.add_argument("-u", "--user", help="User to run process")
    parser.add_argument("-c", "--command", help="Command to run", nargs=argparse.REMAINDER, required=True)
    return parser.parse_args()


def get_uid(user):
    try:
        return int(user)
    except ValueError:
        pass
    return subprocess.Popen("id -u {0}".format(pipes.quote(user)),
                            shell=True,
                            stdout=subprocess.PIPE).communicate()[0]


def ensure_dir(filename):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        try:
            os.makedirs(dirname)
        except OSError:
            pass


if __name__ == '__main__':
    main()
