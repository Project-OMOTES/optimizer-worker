#!/usr/bin/env python3

import pathlib
import argparse
import subprocess
import sys
import os
import signal
from typing import Optional

import psutil


def get_pid(pid_file_path: pathlib.Path) -> int:
    with open(pid_file_path) as pid_file:
        pid = int(pid_file.read().strip())

    return pid


class StartCommand:
    start_command: list
    pid_file_path: str
    stop_command: Optional[str]

    exit_with_signal: int
    process: Optional[subprocess.Popen]

    def __init__(self, start_command: list, pid_file_path: str, stop_command: Optional[str] = None):
        self.start_command = start_command
        self.pid_file_path = pid_file_path
        self.stop_command = stop_command

        self.exit_with_signal = 0
        self.process = None

    def sig_handler(self, sig_num, current_stack_frame):
        print(f'Signal {sig_num} received', flush=True)
        self.exit_with_signal = sig_num
        if self.stop_command is not None:
            print(f'Running stop command {self.stop_command}', flush=True)
            subprocess.run(self.stop_command.split())
        else:
            print(f'Sending signal {sig_num} to child {self.process.pid}', flush=True)
            os.kill(self.process.pid, sig_num)

    def start(self):
        if not self.pid_file_path.exists():
            self.pid_file_path.parent.mkdir(parents=True, exist_ok=True)
        elif self.pid_file_path.is_file():
            pid = get_pid(self.pid_file_path)

            if psutil.pid_exists(pid):
                print(f'Process with pid {pid} already exists. Not doing anything.', flush=True)
                sys.exit(0)

        self.process = subprocess.Popen(self.start_command)
        print(f'Started {self.start_command} with pid {self.process.pid}.', flush=True)

        with open(self.pid_file_path, 'w+') as pid_file:
            pid_file.write(f'{self.process.pid}\n')

        signal.signal(signal.SIGQUIT, self.sig_handler)
        signal.signal(signal.SIGINT, self.sig_handler)
        signal.signal(signal.SIGTERM, self.sig_handler)

        try:
            (_, process_exit_code) = os.waitpid(self.process.pid, 0)

            if not self.exit_with_signal:
                print(f'No signal received. Process died on its own with exit code {process_exit_code}.')
                self.exit_with_signal = process_exit_code
            else:
                print(
                    f'Already have exit code {self.exit_with_signal} from signals so ignored exit code {process_exit_code} from process.')
        finally:
            print(f'Removing pid file for {self.process.pid}', flush=True)
            self.pid_file_path.unlink(missing_ok=True)
            print(f'Exiting with signal {self.exit_with_signal}')
            sys.exit(self.exit_with_signal)


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--pid_file', action="store", required=True)
    arg_parser.add_argument('--stop', action="store", required=False)
    sub_parsers = arg_parser.add_subparsers(dest='action')
    start_parser = sub_parsers.add_parser('start')
    start_parser.add_argument('command', action="store", nargs=argparse.REMAINDER)
    args = arg_parser.parse_args()

    pid_file_path = pathlib.Path(args.pid_file)

    if args.action == 'start':
        start = StartCommand(args.command, pid_file_path, args.stop)
        start.start()
    else:
        arg_parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
