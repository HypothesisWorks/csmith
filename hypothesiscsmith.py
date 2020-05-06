import os
import subprocess
import tempfile
import sys
import shutil
import struct
import click

from hypothesis.searchstrategy import SearchStrategy
from hypothesis._strategies import defines_strategy
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.errors import InvalidArgument


HERE = os.path.dirname(__file__)

CSMITH = os.path.join(HERE, "src", "csmith")


class CsmithState(object):
    def __init__(self, data):
        self.__data = data
        self.__write_buffer = bytearray([0] * 4)
        self.__tempdir = None
        self.__proc = self.__pipeout = self.__pipein = None

    def write_result(self, n):
        if self.__pipeout is None:
            self.__pipeout = open(self.__result_channel, "wb")
        out = self.__pipeout
        buf = self.__write_buffer
        struct.pack_into(">L", buf, 0, n)
        out.write(buf)
        out.flush()

    def ack(self):
        self.write_result(0)

    def read_command(self):
        if self.__pipein is None:
            self.__pipein = open(self.__command_channel, "rb")
        pin = self.__pipein
        while True:
            c = pin.read(1)
            if not c:
                continue
            n = c[0]
            return pin.read(n).decode("ascii")

    def cleanup_process(self):
        if self.__proc is not None:
            try:
                self.__proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.__proc.kill()
                self.__proc.wait(timeout=1)

            if self.__proc.returncode != 0:
                raise Exception("Subprocess call terminated abnormally")

    def gen(self):
        assert self.__tempdir is None
        try:
            self.__tempdir = tempfile.mkdtemp()
            env = dict(os.environ)
            self.__command_channel = os.path.join(
                self.__tempdir, "hypothesisfifo.commands"
            )
            self.__result_channel = os.path.join(
                self.__tempdir, "hypothesisfifo.results"
            )
            env["HYPOTHESISFIFOCOMMANDS"] = self.__command_channel
            env["HYPOTHESISFIFORESULTS"] = self.__result_channel
            os.mkfifo(self.__result_channel)
            os.mkfifo(self.__command_channel)
            output_name = os.path.join(self.__tempdir, "gen.c")

            self.__proc = subprocess.Popen(
                [CSMITH, "-o", output_name],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            while True:
                line = self.read_command()
                if line == "TERMINATE":
                    self.ack()
                    self.cleanup_process()
                    break
                elif line == "RAND":
                    value = self.__data.draw_bits(31)
                    self.write_result(value)
                elif line.startswith("START "):
                    _, label = line.split()
                    self.__data.start_example(label.strip())
                    self.ack()
                elif line == "END":
                    self.__data.stop_example()
                    self.ack()
                # Terminated improperly
                elif not line:
                    self.cleanup_process()
                    assert (
                        False
                    ), "Improper response from subprocess that terminated normally"
                    break
                else:
                    raise Exception("Unknown command %r" % (line,))
            with open(output_name) as i:
                return i.read()
        finally:
            for f in (self.__pipeout, self.__pipein):
                if f is not None:
                    f.close()
            if self.__proc is not None:
                self.__proc.kill()
            self.__pipeout = self.__pipein = None
            if self.__tempdir is not None:
                shutil.rmtree(self.__tempdir)


class CsmithStrategy(SearchStrategy):
    def do_draw(self, data):
        return CsmithState(data).gen()


@defines_strategy
def csmith():
    """A strategy for generating C programs, using Csmith."""

    if not os.path.exists(CSMITH):
        subprocess.check_call(["./configure"], cwd=HERE)
        subprocess.check_call(["make"], cwd=HERE)
        assert os.path.exists(CSMITH)

    return CsmithStrategy()


@click.group()
def main():
    """Commands for working with Hypothesis generated Csmith
    programs."""
    pass


@main.command()
@click.argument("filename")
def show(filename):
    """Show the generated program associated with a previous Hypothesis
    representation of it."""
    with open(filename, "rb") as i:
        data = ConjectureData.for_buffer(i.read())

    print(data.draw(csmith()))


if __name__ == "__main__":
    main()
