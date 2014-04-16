#!/usr/bin/env python
import os
import sys
import time
import fcntl
import pipes
import errno
import daemon
import signal
import atexit
import shutil
import datetime
import argparse
import subprocess
import contextlib


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

    context.prevent_core = False

    if args.stderr:
        ensure_dir(args.stderr)
        context.stderr = get_wrapped_stream(2, args.stderr, args)
    else:
        context.stderr = get_foreground_stream(2, args)

    if args.user:
        context.uid = get_uid(args.user)

    if args.single_process and args.pid_file:
        context.pid_file = args.pid_file

    if not args.daemon:
        context.files_preserve = [sys.stdin.fileno()]
        context.stdin = sys.stdin

    with context:
        if args.single_process:
            exec_process(args)
        try:
            watch_process(args, args.pid_file or None)
        except KeyboardInterrupt:
            move_logs(args)
            sys.exit(130)


process = [None]


def exec_process(args):
    os.execl('/bin/sh', '/bin/sh', '-c', ' '.join(pipes.quote(arg) for arg in args.command))


def watch_process(args, pid_file=None):
    atexit.register(after_exit)
    signal.signal(signal.SIGABRT, sigkill_child)

    try:
        pidfile = acquire_pidfile_lock(pid_file)
    except Exception, e:
        sys.stderr.write("Couldn't acquire pidfile lock {0}, owned by {1} ({2})\n".format(pid_file, get_pid(pid_file), e))
        sys.exit(1)

    if args.daemon:
        stdin = None
    else:
        stdin = sys.stdin

    try:
        process[0] = subprocess.Popen(' '.join(pipes.quote(arg) for arg in args.command),
                                      shell=True, stdin=stdin)
        p = process[0]
        pid = p.pid

        if pidfile:
            write_pid_to_pidfile(pidfile, pid)

        code = p.wait()
        try:
            move_logs(args)
        except:
            pass
    finally:
        try:
            if pid_file is not None:
                os.unlink(pid_file)
        except:
            pass
    sys.exit(code)


def after_exit():
    if process[0] is None: return
    while process[0].poll() is None:
        process[0].terminate()
        time.sleep(1)


def sigkill_child():
    while process[0].poll() is None:
        process[0].send_signal(signal.SIGKILL)
        time.sleep(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Run a command as a daemon")
    parser.add_argument("-d", "--daemon", help="Run as daemon", action='store_true')
    parser.add_argument("-o", "--stdout", help="Standard output destination")
    parser.add_argument("-w", "--cwd", help="Working directory")
    parser.add_argument("-e", "--stderr", help="Standard error destination")
    parser.add_argument("-p", "--pid-file", help="PID file location")
    parser.add_argument("-u", "--user", help="User to run process")
    parser.add_argument("-c", "--command", help="Command to run", nargs=argparse.REMAINDER, required=True)
    parser.add_argument("-s", "--single-process", help="Do not wrap process and just exec the child process.", action="store_true")
    return parser.parse_args()


def move_logs(args):
    date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    for name in ('stdout', 'stderr'):
        filename = getattr(args, name, None)
        if not filename:
            continue
        basename, extension = filename.rsplit('.', 1)
        new_filename = '{0}-{1}.{2}'.format(
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
    uid = subprocess.Popen("id -u {0}".format(pipes.quote(user)),
                           shell=True,
                           stdout=subprocess.PIPE).communicate()[0]
    try:
        return int(uid.strip())
    except ValueError:
        return


def ensure_dir(filename):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        try:
            os.makedirs(dirname)
        except OSError:
            pass


def get_pid(pid_file):
    try:
        with open(pid_file) as f:
            return f.read().strip()
    except:
        return 'n/a'


def open_pidfile(pidfile_path):
    open_flags = (os.O_CREAT | os.O_RDWR)
    open_mode = 0o644
    pidfile_fd = os.open(pidfile_path, open_flags, open_mode)

    try:
        fcntl.flock(pidfile_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as e:
        try:
            os.close(pidfile_fd)
        except:
            pass
        if e.errno in (errno.EACCES, errno.EAGAIN):
            raise LockTaken()

    return os.fdopen(pidfile_fd, 'w')


def write_pid_to_pidfile(pidfile, pid):
    pidfile.seek(0)
    line = "%(pid)d\n" % {'pid': pid}
    pidfile.truncate()
    pidfile.write(line)
    pidfile.flush()


def acquire_pidfile_lock(pidfile_path=None):
    if not pidfile_path: return
    end_time = time.time() + 5.0
    while True:
        try:
            pidfile = open_pidfile(pidfile_path)
            write_pid_to_pidfile(pidfile, os.getpid())
            return pidfile
        except LockTaken:
            if time.time() > end_time:
                raise Exception("Failed to lock")
            time.sleep(0.1)


class LockTaken(Exception):
    pass


if __name__ == '__main__':
    main()
