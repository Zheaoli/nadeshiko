from nadeshiko.context import UNIQUE_COUNT_ID
from nadeshiko.node import Node, NodeKind, Obj
from nadeshiko.type import Type, TypeKind

ARGS_REGISTER_64 = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
ARGS_REGISTER_8 = ["dil", "sil", "dl", "cl", "r8b", "r9b"]


def count() -> int:
    i = UNIQUE_COUNT_ID.get()
    UNIQUE_COUNT_ID.set(i + 1)
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


def emit_data_section(prog: list[Obj], global_stmt: list[str]):
    for obj in prog:
        if obj.is_function:
            continue
        global_stmt.append(f"  .data\n")
        global_stmt.append(f"  .global {obj.name}\n")
        global_stmt.append(f"{obj.name}:\n")
        if obj.init_data != "":
            for i in range(len(obj.init_data)):
                global_stmt.append(f"  .byte {ord(obj.init_data[i])}\n")
        else:
            global_stmt.append(f"  .zero {obj.object_type.size}\n")


def emit_text(prog: list[Obj], global_stmt: list[str]):
    for obj in prog:
        if not obj.is_function:
            continue
        global_stmt.append(f"  .global {obj.name}\n")
        global_stmt.append(f"  .text\n")
        global_stmt.append(f"{obj.name}:\n")
        temp = [
            f"  push %rbp\n",
            f"  mov %rsp, %rbp\n",
            f"  sub ${obj.stack_size}, %rsp\n",
        ]
        global_stmt.extend(temp)
        for i in range(len(obj.params)):
            if obj.params[i].object_type.size == 1:
                global_stmt.append(
                    f"  mov %{ARGS_REGISTER_8[i]}, {obj.params[i].offset}(%rbp)\n"
                )
            else:
                global_stmt.append(
                    f"  mov %{ARGS_REGISTER_64[i]}, {obj.params[i].offset}(%rbp)\n"
                )
        depth = generate_stmt(global_stmt, obj, obj.body, 0)
        assert depth == 0
        global_stmt.append(f".L.return.{obj.name}:\n")
        global_stmt.append("  mov %rbp, %rsp\n")
        global_stmt.append("  pop %rbp\n")
        global_stmt.append("  ret\n")


def codegen(prog: list["Obj"]) -> str:
    assign_local_var_offsets(prog)
    final_result = []
    emit_data_section(prog, final_result)
    emit_text(prog, final_result)
    return "".join(final_result)


def generate_stmt(
    global_stmt: list[str], current_function: Obj, node: Node, depth: int
) -> (list[str], int):
    match node.kind:
        case NodeKind.If:
            c = count()
            depth = generate_asm(global_stmt, current_function, node.condition, depth)
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
                depth = generate_asm(
                    global_stmt, current_function, node.condition, depth
                )
                global_stmt.append(f"  cmp $0, %rax\n")
                global_stmt.append(f"  je .L.end{c}\n")
            depth = generate_stmt(global_stmt, current_function, node.then, depth)
            if node.inc:
                depth = generate_asm(global_stmt, current_function, node.inc, depth)
            global_stmt.append(f"  jmp .L.begin{c}\n")
            global_stmt.append(f".L.end{c}:\n")
            return depth
        case NodeKind.ExpressionStmt:
            depth = generate_asm(global_stmt, current_function, node.left, depth)
            return depth
        case NodeKind.Return:
            depth = generate_asm(global_stmt, current_function, node.left, depth)
            global_stmt.append(f"  jmp .L.return.{current_function.name}\n")
            return depth
        case NodeKind.Block:
            node = node.body
            while node:
                depth = generate_stmt(global_stmt, current_function, node, depth)
                node = node.next_node
            return depth
    raise ValueError("invalid node type")


def generate_address(
    global_stmt: list[str], current_function: Obj, node: Node, depth: int
) -> int:
    if node.kind == NodeKind.Variable:
        if node.var.is_local:
            global_stmt.append(f"  lea {node.var.offset}(%rbp), %rax\n")
        else:
            global_stmt.append(f"  lea {node.var.name}(%rip), %rax\n")
        return depth
    if node.kind == NodeKind.Deref:
        depth = generate_asm(global_stmt, current_function, node.left, depth)
        return depth
    raise ValueError("invalid node type")


def generate_asm(
    global_stmt: list[str], current_function: Obj, node: Node, depth: int
) -> int:
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
        if node_type.size == 1:
            global_stmt.append(f"  movsbq (%rax), %rax\n")
        else:
            global_stmt.append(f"  mov (%rax), %rax\n")

    def store(depth: int, ty: Type) -> int:
        depth = pop("rdi", depth)
        if ty.size == 1:
            global_stmt.append("  mov %al, (%rdi)\n")
        else:
            global_stmt.append("  mov %rax, (%rdi)\n")
        return depth

    match node.kind:
        case NodeKind.Number:
            global_stmt.append(f"  mov ${node.value}, %rax\n")
            return depth
        case NodeKind.Neg:
            depth = generate_asm(global_stmt, current_function, node.left, depth)
            global_stmt.append(f"  neg %rax\n")
            return depth
        case NodeKind.Variable:
            depth = generate_address(global_stmt, current_function, node, depth)
            load(node.node_type)
            return depth
        case NodeKind.Addr:
            depth = generate_address(global_stmt, current_function, node.left, depth)
            return depth
        case NodeKind.Deref:
            depth = generate_asm(global_stmt, current_function, node.left, depth)
            load(node.node_type)
            return depth
        case NodeKind.Assign:
            depth = generate_address(global_stmt, current_function, node.left, depth)
            depth = push(depth)
            depth = generate_asm(global_stmt, current_function, node.right, depth)
            depth = store(depth, node.node_type)
            return depth
        case NodeKind.StmtExpression:
            node = node.body
            while node:
                depth = generate_stmt(global_stmt, current_function, node, depth)
                node = node.next_node
            return depth
        case NodeKind.FunctionCall:
            for item in node.function_args:
                depth = generate_asm(global_stmt, current_function, item, depth)
                depth = push(depth)
            for i in range(len(node.function_args) - 1, -1, -1):
                depth = pop(ARGS_REGISTER_64[i], depth)
            global_stmt.append("  mov $0, %rax\n")
            global_stmt.append(f"  call {node.function_name}\n")
            return depth
    depth = generate_asm(global_stmt, current_function, node.right, depth)
    depth = push(depth)
    depth = generate_asm(global_stmt, current_function, node.left, depth)
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
