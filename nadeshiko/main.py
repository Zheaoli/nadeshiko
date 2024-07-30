import typer

from nadeshiko.codegen import generate_asm
from nadeshiko.parse import parse
from nadeshiko.token import TokenType
from nadeshiko.tokenize import tokenize

app = typer.Typer()


@app.command(context_settings={"ignore_unknown_options": True})
def main(expression: str):
    output_asm = [f"  .global main\n", f"main:\n"]
    assert len(expression) >= 0
    token = tokenize(expression)
    token, node = parse(token)
    assert token.type == TokenType.EOF
    temp, depth = generate_asm(node, 0)
    assert depth == 0
    output_asm.extend(temp)
    output_asm.append(f"  ret\n")
    print("".join(output_asm), flush=True)


if __name__ == "__main__":
    app()
