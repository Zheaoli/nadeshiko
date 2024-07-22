import typer


def main(number: int):
    output_asm = (f"  .global main\n"
                  f"main\n"
                  f"  mov ${number}, %rax\n"
                  f"  ret\n")
    print(output_asm, flush=True)


if __name__ == '__main__':
    typer.run(main)
