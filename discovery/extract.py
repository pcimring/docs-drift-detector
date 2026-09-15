from dataclasses import dataclass

from markdown_it import MarkdownIt


@dataclass
class CodeBlock:
    language: str
    code: str
    line: int


def extract_code_blocks(markdown_text: str, language: str) -> list[CodeBlock]:
    md = MarkdownIt()
    tokens = md.parse(markdown_text)
    blocks = []
    for token in tokens:
        if token.type != "fence":
            continue
        info = token.info.strip()
        fence_lang = info.split()[0] if info else ""
        if fence_lang != language:
            continue
        line = token.map[0] + 1 if token.map else 0
        blocks.append(CodeBlock(language=language, code=token.content, line=line))
    return blocks
