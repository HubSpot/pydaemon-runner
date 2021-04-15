# pydaemon-runner

*Nohup but for python*

## Install

```bash
 $ pip install daemon-runner
```

## Usage

```bash
usage: daemon-runner [-h] [-o STDOUT] [-w CWD] [-e STDERR] [-p PID_FILE]
                     [-u USER] -c ...

Run a command as a daemon

optional arguments:
  -h, --help            show this help message and exit
  -o STDOUT, --stdout STDOUT
                        Standard output destination
  -w CWD, --cwd CWD     Working directory
  -e STDERR, --stderr STDERR
                        Standard error destination
  -p PID_FILE, --pid-file PID_FILE
                        PID file location
  -u USER, --user USER  User to run process
  -c ..., --command ...
                        Command to run
```

## License

Apache 2.0 HubSpot, Inc
