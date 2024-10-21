from typing import TextIO

import click

from nadeshiko.codegen import codegen
from nadeshiko.parse import Parse
from nadeshiko.tokenize import tokenize


@click.command()
@click.argument("filename", type=click.File("r"), default="-")
def main(filename: TextIO):
    expression = filename.read()
    assert len(expression) >= 0
    tokens = tokenize(expression)
    prog = Parse(tokens).parse_stmt()
    result = codegen(prog)

    print(result, flush=True)


if __name__ == "__main__":
    app()
