def error_message(expression: str, location: int, message: str) -> str:
    messages = [f"{expression}\n", f"{' ' * location}^ {message}\n"]
    return "".join(messages)
