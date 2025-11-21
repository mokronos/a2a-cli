from a2a.types import Message

def get_text(msg: Message | None) -> str:
    if not msg:
        return ""
    return msg.parts[0].root.text
