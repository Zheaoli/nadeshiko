from typing import TextIO

import click

from nadeshiko.codegen import codegen
from nadeshiko.parse import Parse
from nadeshiko.tokenize import tokenize


@click.command()
@click.argument("filename", type=click.File("r"), default="-")
@click.option("-o", "--output", type=click.File("w"))
def main(filename: TextIO, output: TextIO):
    expression = filename.read()
    assert len(expression) >= 0
    tokens = tokenize(expression)
    prog = Parse(tokens).parse_stmt()
    result = codegen(prog)

    output.write(result)


if __name__ == "__main__":
    main()
