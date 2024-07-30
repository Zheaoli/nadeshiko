import typer

from nadeshiko.codegen import codegen
from nadeshiko.parse import parse_stmt
from nadeshiko.token import TokenType
from nadeshiko.tokenize import tokenize

app = typer.Typer()


@app.command(context_settings={"ignore_unknown_options": True})
def main(expression: str):
    assert len(expression) >= 0
    token = tokenize(expression)
    node = parse_stmt(token)
    result = codegen(node)

    print(result, flush=True)


if __name__ == "__main__":
    app()
