#!/usr/bin/env python
import os
import sys
import pipes
import daemon
import argparse
import subprocess

from lockfile.pidlockfile import PIDLockFile


def main():
    args = parse_args()
    context = daemon.DaemonContext(
        working_directory=args.cwd or '.',
        detach_process=args.daemon
    )
    if args.stdout:
        ensure_dir(args.stdout)
        context.stdout = get_wrapped_stream(1, args.stdout, args)
    else:
        context.stdout = get_foreground_stream(1, args)

    if args.stderr:
        ensure_dir(args.stderr)
        context.stderr = get_wrapped_stream(2, args.stderr, args)
    else:
        context.stderr = get_foreground_stream(2, args)

    if args.pid_file:
        context.pidfile = PIDLockFile(args.pid_file)

    if args.user:
        context.uid = get_uid(args.user)

    with context:
        exec_process(args)


def exec_process(args):
    try:
        code = subprocess.Popen(' '.join(pipes.quote(arg) for arg in args.command),
                                shell=True).wait()
        sys.exit(code)
    except KeyboardInterrupt:
        sys.exit(130)


def parse_args():
    parser = argparse.ArgumentParser(description="Run a command as a daemon")
    parser.add_argument("-d", "--daemon", help="Run as daemon", action='store_true')
    parser.add_argument("-o", "--stdout", help="Standard output destination")
    parser.add_argument("-w", "--cwd", help="Working directory")
    parser.add_argument("-e", "--stderr", help="Standard error destination")
    parser.add_argument("-p", "--pid-file", help="PID file location")
    parser.add_argument("-u", "--user", help="User to run process")
    parser.add_argument("-c", "--command", help="Command to run", nargs=argparse.REMAINDER, required=True)
    return parser.parse_args()


# Delegate to tee if running in foreground.
def get_wrapped_stream(fd, filename, args):
    if args.daemon:
        return open(filename, 'a+')
    new_fd = os.dup(fd)
    tee_process = subprocess.Popen(['tee', '-a', filename], stdin=subprocess.PIPE, stdout=os.fdopen(new_fd, "w"))
    return tee_process.stdin


def get_foreground_stream(fd, args):
    if args.daemon:
        return None
    return os.fdopen(os.dup(fd), "w")


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
