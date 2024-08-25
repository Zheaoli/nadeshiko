import typer

from nadeshiko.codegen import codegen
from nadeshiko.parse import Parse
from nadeshiko.token import TokenType
from nadeshiko.tokenize import tokenize

app = typer.Typer()


@app.command(context_settings={"ignore_unknown_options": True})
def main(expression: str):
    assert len(expression) >= 0
    tokens = tokenize(expression)
    prog = Parse(tokens).parse_stmt()
    result = codegen(prog)

    print(result, flush=True)


if __name__ == "__main__":
    app()
