from nadeshiko.node import Node, NodeKind, Function


def count() -> int:
    i = 1
    i += 1
    return i


def align_to(offset: int, align: int) -> int:
    return (offset + align - 1) // align * align


def assign_lvar_offsets(prog: Function) -> None:
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
    depth = generate_stmt(result, prog.body, 0)
    assert depth == 0
    result.append(".L.return:\n")
    result.append("  mov %rbp, %rsp\n")
    result.append("  pop %rbp\n")
    result.append("  ret\n")
    return "".join(result)


def generate_stmt(global_stmt: list[str], node: Node, depth: int) -> (list[str], int):
    match node.kind:
        case NodeKind.If:
            c = count()
            depth = generate_asm(global_stmt, node.condition, depth)
            global_stmt.append(f"  cmp $0, %rax\n")
            global_stmt.append(f"  je .L.else{c}\n")
            depth = generate_stmt(global_stmt, node.then, depth)

            global_stmt.append(f"  jmp .L.end{c}\n")
            global_stmt.append(f".L.else{c}:\n")
            if node.els:
                depth = generate_stmt(global_stmt, node.els, depth)
            global_stmt.append(f".L.end{c}:\n")
            return depth
        case NodeKind.ForStmt:
            c = count()
            if node.init:
                depth = generate_stmt(global_stmt, node.init, depth)
            global_stmt.append(f".L.begin{c}:\n")
            if node.condition:
                depth = generate_asm(global_stmt, node.condition, depth)
                global_stmt.append(f"  cmp $0, %rax\n")
                global_stmt.append(f"  je .L.end{c}\n")
            depth = generate_stmt(global_stmt, node.then, depth)
            if node.inc:
                depth = generate_asm(global_stmt, node.inc, depth)
            global_stmt.append(f"  jmp .L.begin{c}\n")
            global_stmt.append(f".L.end{c}:\n")
            return depth
        case NodeKind.ExpressionStmt:
            depth = generate_asm(global_stmt, node.left, depth)
            return depth
        case NodeKind.Return:
            depth = generate_asm(global_stmt, node.left, depth)

            global_stmt.append("  jmp .L.return\n")
            return depth
        case NodeKind.Block:
            node = node.body
            while node:
                depth = generate_stmt(global_stmt, node, depth)
                node = node.next_node
            return depth
    raise ValueError("invalid node type")


def generate_address(global_stmt: list[str], node: Node, depth: int) -> int:
    if node.kind == NodeKind.Variable:
        global_stmt.append(f"  lea {node.var.offset}(%rbp), %rax\n")
        return depth
    if node.kind == NodeKind.Deref:
        depth = generate_asm(global_stmt, node.left, depth)
        return depth
    raise ValueError("invalid node type")


def generate_asm(global_stmt: list[str], node: Node, depth: int) -> int:
    if not node:
        return depth

    def push(depth: int) -> (list[str], depth):
        global_stmt.append("  push %rax\n")
        return depth + 1

    def pop(register: str, depth: int) -> (list[str], depth):
        global_stmt.append(f"  pop %{register}\n")
        return depth - 1

    match node.kind:
        case NodeKind.Number:
            global_stmt.append(f"  mov ${node.value}, %rax\n")
            return depth
        case NodeKind.Neg:
            depth = generate_asm(global_stmt, node.left, depth)
            global_stmt.append(f"  neg %rax\n")
            return depth
        case NodeKind.Variable:
            depth = generate_address(global_stmt, node, depth)
            global_stmt.append(f"  mov (%rax), %rax\n")
            return depth
        case NodeKind.Addr:
            depth = generate_address(global_stmt, node.left, depth)
            return depth
        case NodeKind.Deref:
            depth = generate_asm(global_stmt, node.left, depth)
            global_stmt.append(f"  mov (%rax), %rax\n")
            return depth
        case NodeKind.Assign:
            depth = generate_address(global_stmt, node.left, depth)
            depth = push(depth)
            depth = generate_asm(global_stmt, node.right, depth)
            depth = pop("rdi", depth)
            global_stmt.append("  mov %rax, (%rdi)\n")
            return depth
        case NodeKind.FunctionCall:
            global_stmt.append("  mov $0, %rax\n")
            global_stmt.append(f"  call {node.function_name}\n")
            return depth
    depth = generate_asm(global_stmt, node.right, depth)
    depth = push(depth)
    depth = generate_asm(global_stmt, node.left, depth)
    depth = pop("rdi", depth)
    match node.kind:
        case NodeKind.Add:
            global_stmt.append(f"  add %rdi, %rax\n")
            return depth
        case NodeKind.Sub:
            global_stmt.append(f"  sub %rdi, %rax\n")
            return depth
        case NodeKind.Mul:
            global_stmt.append(f"  imul %rdi, %rax\n")
            return depth
        case NodeKind.Div:
            global_stmt.append(f"  cqo\n")
            global_stmt.append(f"  div %rdi, %rax\n")
            return depth
        case NodeKind.Equal | NodeKind.NotEqual | NodeKind.Less | NodeKind.LessEqual:
            global_stmt.append(f"  cmp %rdi, %rax\n")
            match node.kind:
                case NodeKind.Equal:
                    global_stmt.append("  sete %al\n")
                case NodeKind.NotEqual:
                    global_stmt.append("  setne %al\n")
                case NodeKind.Less:
                    global_stmt.append("  setl %al\n")
                case NodeKind.LessEqual:
                    global_stmt.append("  setle %al\n")
            global_stmt.append("  movzb %al, %rax\n")
            return depth
    raise ValueError("invalid node type")
