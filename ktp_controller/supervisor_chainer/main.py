# Standard library imports
import contextlib
import dataclasses
import datetime
import json
import os
import select
import signal
import subprocess
import sys
import types
import typing


def _write_stdout(s: str) -> None:
    # only eventlistener protocol messages may be sent to stdout
    sys.stdout.write(s)
    sys.stdout.flush()


def _write_stderr(s: str) -> None:
    utcnow = datetime.datetime.utcnow().replace(tzinfo=datetime.UTC)
    sys.stderr.write(f"{utcnow.isoformat(timespec='seconds')}  {s}")
    sys.stderr.flush()


class _guaranteed_result(contextlib.AbstractContextManager[None]):
    def __init__(self, *, do_log: bool = False):
        super().__init__()
        self.__do_log = do_log

    def __enter__(self) -> None:
        if self.__do_log:
            _write_stderr("\n")
        return

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> bool:
        if exc_type is None:
            if self.__do_log:
                _write_stderr("Event handled successfully.\n")
            _write_stdout("RESULT 2\nOK")
        else:
            _write_stderr("Event handling failed.\n")
            _write_stderr(f"{exc_type}: {exc_value}\n")
            _write_stdout(r"RESULT 4\FAIL")
        return True


@dataclasses.dataclass
class _ProcStateBackoff:
    name: typing.Literal["backoff"] = "backoff"
    is_terminating: typing.Literal[False] = False


@dataclasses.dataclass
class _ProcStateExited:
    is_expected: bool
    name: typing.Literal["exited"] = "exited"
    is_terminating: typing.Literal[True] = True


@dataclasses.dataclass
class _ProcStateFatal:
    name: typing.Literal["fatal"] = "fatal"
    is_terminating: typing.Literal[True] = True


@dataclasses.dataclass
class _ProcStateRunning:
    name: typing.Literal["running"] = "running"
    is_terminating: typing.Literal[False] = False


@dataclasses.dataclass
class _ProcStateStarting:
    name: typing.Literal["starting"] = "starting"
    is_terminating: typing.Literal[False] = False


@dataclasses.dataclass
class _ProcStateStopped:
    name: typing.Literal["stopped"] = "stopped"
    is_terminating: typing.Literal[True] = True


@dataclasses.dataclass
class _ProcStateUnknown:
    name: typing.Literal["unknown"] = "unknown"
    is_terminating: typing.Literal[False] = False


@dataclasses.dataclass
class _Proc:
    name: str
    state: (
        _ProcStateBackoff
        | _ProcStateExited
        | _ProcStateFatal
        | _ProcStateRunning
        | _ProcStateStarting
        | _ProcStateStopped
        | _ProcStateUnknown
    )


@dataclasses.dataclass
class Event:
    name: str
    proc: _Proc | None


def _read_event(*, do_log: bool = True) -> Event:
    while True:
        ready_to_read, _, _ = select.select([sys.stdin], [], [], 0.5)
        if ready_to_read:
            break

    # read header line and print it to stderr
    header_line = sys.stdin.readline()

    # read event payload and print it to stderr
    headers = dict([x.split(":") for x in header_line.split()])
    if do_log:
        _write_stderr(f"Headers: {json.dumps(headers)}\n")

    payload_data = sys.stdin.read(int(headers["len"]))
    payload = dict([x.split(":") for x in payload_data.split()])
    if do_log:
        _write_stderr(f"Payload: {json.dumps(payload)}\n")

    name = headers["eventname"]

    _ProcState = (
        _ProcStateBackoff
        | _ProcStateExited
        | _ProcStateFatal
        | _ProcStateRunning
        | _ProcStateStarting
        | _ProcStateStopped
        | _ProcStateUnknown
    )

    try:
        proc_state_class: type[_ProcState] = {
            "PROCESS_STATE_BACKOFF": _ProcStateBackoff,
            "PROCESS_STATE_EXITED": _ProcStateExited,
            "PROCESS_STATE_FATAL": _ProcStateFatal,
            "PROCESS_STATE_RUNNING": _ProcStateRunning,
            "PROCESS_STATE_STARTING": _ProcStateStarting,
            "PROCESS_STATE_STOPPED": _ProcStateStopped,
            "PROCESS_STATE_UNKNOWN": _ProcStateUnknown,
        }[headers["eventname"]]
    except KeyError:
        # Not process state event
        return Event(name=name, proc=None)

    process_state: _ProcState
    if proc_state_class == _ProcStateExited:
        is_expected = bool(int(payload["expected"]))
        process_state = _ProcStateExited(is_expected=is_expected)
    else:
        # All non-exited proc state classes take no constructor arguments.
        no_arg_class = typing.cast(
            type[
                _ProcStateBackoff
                | _ProcStateFatal
                | _ProcStateRunning
                | _ProcStateStarting
                | _ProcStateStopped
                | _ProcStateUnknown
            ],
            proc_state_class,
        )
        process_state = no_arg_class()

    proc = _Proc(name=payload["processname"], state=process_state)

    return Event(name=name, proc=proc)


def _supervisorctl(command: str, conf_filepath: str, *args: str) -> bool:
    with open(os.devnull, "wb") as devnull:
        try:
            subprocess.check_call(
                ["supervisorctl", "-c", conf_filepath, command, *list(args)],
                stdout=devnull,
            )
        except subprocess.CalledProcessError:
            return False
        return True


class _Chainer:
    def __init__(self, conf_filepath: str, args: list[str]):
        self.__conf_filepath = conf_filepath
        self.__next_procs: list[str] = []
        self.__waits: dict[str, bool] = {}
        self.__has_been_running: dict[str, bool] = {}
        self.__do_shutdown = False
        self.__expected_exits: dict[str, bool] = {}
        self.__is_terminated = False

        _write_stderr(f"Parsing arguments: {args}\n")

        if args[-1] == "SHUTDOWN":
            args.pop(-1)
            self.__do_shutdown = True

        for arg in args:
            if arg == "WAIT":
                self.__waits[self.__next_procs[-1]] = True
                continue
            self.__waits[arg] = False
            self.__has_been_running[arg] = False
            self.__next_procs.append(arg)

        self.__proc = self.__next_procs.pop(0)

    def __terminate(self, signum: int, frame_stack: types.FrameType | None) -> None:
        self.__is_terminated = True

    def run(self) -> str:
        while True:
            # transition from ACKNOWLEDGED to READY
            _write_stdout("READY\n")

            with _guaranteed_result():
                _write_stderr(f"Current process: {self.__proc!r}\n")
                _write_stderr(f"Next processes: {self.__next_procs!r}\n")
                _write_stderr(f"Has been running: {self.__has_been_running!r}\n")
                _write_stderr(f"Waits: {self.__waits!r}\n")

                event = _read_event()

                _write_stderr(f"Got event: {event}\n")

                if event.proc is None:
                    _write_stderr("Not a process state event, ignoring.\n")
                    continue

                if self.__proc != event.proc.name:
                    continue

                if event.proc.state.name == "running":
                    self.__has_been_running[event.proc.name] = True

                if not self.__has_been_running[event.proc.name]:
                    _write_stderr(
                        f"Process {event.proc.name!r} has not been running yet.\n"
                    )
                    continue

                if event.proc.state.name == "exited":
                    self.__expected_exits[event.proc.name] = (
                        event.proc.state.is_expected
                    )

                if (
                    not event.proc.state.is_terminating
                    and self.__waits[event.proc.name]
                ):
                    _write_stderr(
                        f"Process {event.proc.name!r} is not terminating and we want to wait for it to terminate first.\n"
                    )
                    continue

                _write_stderr(
                    f"Process {event.proc.name!r} is terminating or it's not to be waited.\n"
                )

                if len(self.__next_procs) == 0:
                    _write_stderr(
                        f"Process {event.proc.name!r} was the last process in the chain, stopping event handling...\n"
                    )
                    break

                self.__proc = self.__next_procs.pop(0)
                _write_stderr(f"Starting process {self.__proc!r}.\n")
                _supervisorctl("start", self.__conf_filepath, self.__proc)

        _write_stderr("\n")
        _write_stderr("Stopped event handling.\n")
        _write_stderr("\n")
        _write_stderr("\n")
        _write_stderr("    +==========================================+\n")
        _write_stderr("    |                                          |\n")
        _write_stderr("    | KTP Controller is now fully initialized! |\n")
        _write_stderr("    |                                          |\n")
        _write_stderr("    +==========================================+\n")
        _write_stderr("\n")

        result = "ok" if all(self.__expected_exits.values()) else "fail"

        if self.__do_shutdown:
            _write_stderr("Shutting down the supervisor...\n")
            _supervisorctl("shutdown", self.__conf_filepath)
        else:
            signal.signal(signal.SIGTERM, self.__terminate)
            while not self.__is_terminated:
                # transition from ACKNOWLEDGED to READY
                _write_stdout("READY\n")

                with _guaranteed_result(do_log=False):
                    event = _read_event(do_log=False)

        return result


def run() -> int:
    result = "fail"
    try:
        try:
            os.unlink("chain_result")
        except FileNotFoundError:
            pass

        result = _Chainer(sys.argv[1], sys.argv[2:]).run()
    finally:
        with open("chain_result.tmp", "wb") as f:
            f.write(f"{result}\n".encode("ascii"))
        os.rename("chain_result.tmp", "chain_result")
        _write_stderr(f"Wrote {result!r} 'chain_result' file.\n")

    status = 0 if result == "ok" else 1
    _write_stderr(f"Exit with status {status}.\n")
    return status
