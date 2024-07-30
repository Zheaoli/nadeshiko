from nadeshiko.node import Node, NodeType


def codegen(node: Node) -> str:
    result = [f"  .global main\n", f"main:\n"]
    while node:
        temp, depth = generate_stmt(node, 0)
        assert depth == 0
        result.extend(temp)
        node = node.next_node
    result.append("  ret\n")
    return "".join(result)


def generate_stmt(node: Node, depth: int) -> (list[str], int):
    if node.kind == NodeType.ExpressionStmt:
        return generate_asm(node.left, depth)
    raise ValueError("invalid node type")


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
