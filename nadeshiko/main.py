from typing import TextIO

import click

from nadeshiko.codegen import codegen
from nadeshiko.parse import Parse
from nadeshiko.tokenize import tokenize


@click.command()
@click.argument("filename", type=click.Path(), default="-")
@click.option("-o", "--output", type=click.File("w"))
def main(filename: str, output: TextIO):
    with open(filename, "r") as fp:
        expression = fp.read()
    assert len(expression) >= 0
    tokens = tokenize(expression)
    prog = Parse(tokens).parse_stmt()
    result = codegen(filename, prog)

    output.write(result)


if __name__ == "__main__":
    main()
