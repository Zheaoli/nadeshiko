from nadeshiko.node import Node, NodeType, Function


def align_to(offset: int, align: int) -> int:
    return (offset + align - 1) // align * align


def assign_lvar_offsets(prog: Function) -> int:
    offset = 0
    for obj in prog.locals_obj[::-1]:
        offset += 8
        obj.offset = -offset
    prog.stack_size = align_to(offset, 16)


def codegen(prog: Function) -> str:
    assign_lvar_offsets(prog)
    result = [
        f"  .global main\n",
        f"main:\n",
        f"  push %rbp\n",
        f"  mov %rsp, %rbp\n",
        f"  sub ${prog.stack_size}, %rsp\n",
    ]
    while prog.body:
        temp, depth = generate_stmt(prog.body, 0)
        assert depth == 0
        result.extend(temp)
        prog.body = prog.body.next_node
    result.append("  mov %rbp, %rsp\n")
    result.append("  pop %rbp\n")
    result.append("  ret\n")
    return "".join(result)


def generate_stmt(node: Node, depth: int) -> (list[str], int):
    if node.kind == NodeType.ExpressionStmt:
        return generate_asm(node.left, depth)
    raise ValueError("invalid node type")


def generate_address(node: Node) -> str:
    return f"  lea {node.var.offset}(%rbp), %rax\n"


def generate_asm(node: Node, depth: int) -> (list[str], int):
    result = []
    if not node:
        return result, depth

    def push(depth: int) -> (list[str], depth):
        return ["  push %rax\n"], depth + 1

    def pop(register: str, depth: int) -> (list[str], depth):
        return [f"  pop %{register}\n"], depth - 1

    match node.kind:
        case NodeType.Number:
            result.append(f"  mov ${node.value}, %rax\n")
            return result, depth
        case NodeType.Neg:
            temp_data, depth = generate_asm(node.left, depth)
            result.extend(temp_data)
            result.append(f"  neg %rax\n")
            return result, depth
        case NodeType.Variable:
            result.append(generate_address(node))
            result.append(f"  mov (%rax), %rax\n")
            return result, depth
        case NodeType.Assign:
            result.append(generate_address(node.left))
            temp_data, depth = push(depth)
            result.extend(temp_data)
            temp_data, depth = generate_asm(node.right, depth)
            result.extend(temp_data)
            temp_data, depth = pop("rdi", depth)
            result.extend(temp_data)
            result.append("  mov %rax, (%rdi)\n")
            return result, depth
    temp_data, depth = generate_asm(node.right, depth)
    result.extend(temp_data)
    temp_data, depth = push(depth)
    result.extend(temp_data)
    temp_data, depth = generate_asm(node.left, depth)
    result.extend(temp_data)
    temp_data, depth = pop("rdi", depth)
    result.extend(temp_data)
    match node.kind:
        case NodeType.Add:
            result.append(f"  add %rdi, %rax\n")
            return result, depth
        case NodeType.Sub:
            result.append(f"  sub %rdi, %rax\n")
            return result, depth
        case NodeType.Mul:
            result.append(f"  imul %rdi, %rax\n")
            return result, depth
        case NodeType.Div:
            result.append(f"  cqo\n")
            result.append(f"  div %rdi, %rax\n")
            return result, depth
        case NodeType.Equal | NodeType.NotEqual | NodeType.Less | NodeType.LessEqual:
            result.append(f"  cmp %rdi, %rax\n")
            match node.kind:
                case NodeType.Equal:
                    result.append("  sete %al\n")
                case NodeType.NotEqual:
                    result.append("  setne %al\n")
                case NodeType.Less:
                    result.append("  setl %al\n")
                case NodeType.LessEqual:
                    result.append("  setle %al\n")
            result.append("  movzb %al, %rax\n")
            return result, depth
    raise ValueError("invalid node type")
