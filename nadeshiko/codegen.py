from nadeshiko.node import Node, NodeKind, Obj
from nadeshiko.type import Type, TypeKind

FUNCTION_ARGS_REGISTER = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]


def count() -> int:
    i = 1
    i += 1
    return i


def align_to(offset: int, align: int) -> int:
    return (offset + align - 1) // align * align


def assign_local_var_offsets(prog: list[Obj]) -> None:
    for func_obj in prog:
        if not func_obj.is_function:
            continue
        offset = 0
        for obj in func_obj.locals_obj[::-1]:
            offset += obj.object_type.size
            obj.offset = -offset
        func_obj.stack_size = align_to(offset, 16)


def codegen(prog: list["Obj"]) -> str:
    assign_local_var_offsets(prog)
    final_result = []
    for obj in prog:
        if not obj.is_function:
            continue
        result = [
            f"  .global {obj.name}\n",
            f"  .text\n" f"{obj.name}:\n",
            f"  push %rbp\n",
            f"  mov %rsp, %rbp\n",
            f"  sub ${obj.stack_size}, %rsp\n",
        ]
        for i in range(len(obj.params)):
            result.append(
                f"  mov %{FUNCTION_ARGS_REGISTER[i]}, {obj.params[i].offset}(%rbp)\n"
            )

        depth = generate_stmt(result, obj, obj.body, 0)
        assert depth == 0
        result.append(f".L.return.{obj.name}:\n")
        result.append("  mov %rbp, %rsp\n")
        result.append("  pop %rbp\n")
        result.append("  ret\n")
        final_result.extend(result)
    return "".join(final_result)


def generate_stmt(
    global_stmt: list[str], current_function: Obj, node: Node, depth: int
) -> (list[str], int):
    match node.kind:
        case NodeKind.If:
            c = count()
            depth = generate_asm(global_stmt, node.condition, depth)
            global_stmt.append(f"  cmp $0, %rax\n")
            global_stmt.append(f"  je .L.else{c}\n")
            depth = generate_stmt(global_stmt, current_function, node.then, depth)

            global_stmt.append(f"  jmp .L.end{c}\n")
            global_stmt.append(f".L.else{c}:\n")
            if node.els:
                depth = generate_stmt(global_stmt, current_function, node.els, depth)
            global_stmt.append(f".L.end{c}:\n")
            return depth
        case NodeKind.ForStmt:
            c = count()
            if node.init:
                depth = generate_stmt(global_stmt, current_function, node.init, depth)
            global_stmt.append(f".L.begin{c}:\n")
            if node.condition:
                depth = generate_asm(global_stmt, node.condition, depth)
                global_stmt.append(f"  cmp $0, %rax\n")
                global_stmt.append(f"  je .L.end{c}\n")
            depth = generate_stmt(global_stmt, current_function, node.then, depth)
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
            global_stmt.append(f"  jmp .L.return.{current_function.name}\n")
            return depth
        case NodeKind.Block:
            node = node.body
            while node:
                depth = generate_stmt(global_stmt, current_function, node, depth)
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

    def load(node_type: Type):
        if node_type.kind == TypeKind.TYPE_ARRAY:
            return None
        global_stmt.append(f"  mov (%rax), %rax\n")

    def store(depth: int) -> int:
        depth = pop("rdi", depth)
        global_stmt.append("  mov %rax, (%rdi)\n")
        return depth

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
            load(node.node_type)
            return depth
        case NodeKind.Addr:
            depth = generate_address(global_stmt, node.left, depth)
            return depth
        case NodeKind.Deref:
            depth = generate_asm(global_stmt, node.left, depth)
            load(node.node_type)
            return depth
        case NodeKind.Assign:
            depth = generate_address(global_stmt, node.left, depth)
            depth = push(depth)
            depth = generate_asm(global_stmt, node.right, depth)
            depth = store(depth)
            return depth
        case NodeKind.FunctionCall:
            for item in node.function_args:
                depth = generate_asm(global_stmt, item, depth)
                depth = push(depth)
            for i in range(len(node.function_args) - 1, -1, -1):
                depth = pop(FUNCTION_ARGS_REGISTER[i], depth)
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
