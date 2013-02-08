#!/usr/bin/env python
import os
import sys
import pipes
import daemon
import shutil
import datetime
import argparse
import subprocess
import contextlib

from lockfile.pidlockfile import PIDLockFile, LockTimeout, NotMyLock


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
        context.pidfile = pidlock(args.pid_file)

    if args.user:
        context.uid = get_uid(args.user)

    with context:
        exec_process(args)


def exec_process(args):
    try:
        code = subprocess.Popen(' '.join(pipes.quote(arg) for arg in args.command),
                                shell=True).wait()
        move_logs(args)
        sys.exit(code)
    except KeyboardInterrupt:
        move_logs(args)
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


def move_logs(args):
    date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    for name in ('stdout', 'stderr'):
        filename = getattr(args, name, None)
        if not filename:
            continue
        basename, extension = filename.rsplit('.', 1)
        new_filename = '{0}-{1}.{1}'.format(
            basename,
            date,
            extension
        )
        shutil.move(filename, new_filename)


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


@contextlib.contextmanager
def pidlock(pid_file):
    lock = PIDLockFile(pid_file)
    acquired = False
    try:
        lock.acquire(timeout=.5)
        acquired = True
        yield
    except (LockTimeout, NotMyLock):
        sys.stderr.write("Couldn't acquire pidfile lock {0}, owned by {1}\n".format(pid_file, get_pid(pid_file)))
        sys.exit(1)
    finally:
        if acquired:
            lock.release()


def get_pid(pid_file):
    try:
        with open(pid_file) as f:
            return f.read().strip()
    except:
        return 'n/a'


if __name__ == '__main__':
    main()
