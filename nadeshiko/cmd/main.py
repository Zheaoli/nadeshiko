import typer


def main(expression: str):
    output_asm = [f"  .global main\n",
                  f"main:\n"]
    assert len(expression) >= 0
    output_asm.append(f"  mov ${expression[0]}, %rax\n")
    index = 1
    while index < len(expression):
        match expression[index]:
            case '+':
                output_asm.append(f"  add ${expression[index + 1]}, %rax\n")
            case '-':
                output_asm.append(f"  sub ${expression[index + 1]}, %rax\n")
            case _:
                raise ValueError(f"Invalid expression: {expression}")
        index += 2
    output_asm.append(f"  ret\n")

    print("".join(output_asm), flush=True)


if __name__ == '__main__':
    typer.run(main)
