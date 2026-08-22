"""Command lexer - tokenize Indonesian VCS command input."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Token:
    """A single token from command input."""

    value: str
    token_type: str  # "word", "quoted_string", "flag", "equals"


def tokenize(input_text: str) -> list[Token]:
    """Tokenize a command string.

    Handles:
    - Quoted strings: "hello world"
    - Flags: --verbose
    - Regular words: simpan, versi
    - Paths with spaces: "my folder/file.py"
    """
    tokens: list[Token] = []
    i = 0
    text = input_text.strip()

    while i < len(text):
        # Skip whitespace
        if text[i].isspace():
            i += 1
            continue

        # Quoted string
        if text[i] == '"':
            i += 1
            start = i
            while i < len(text) and text[i] != '"':
                if text[i] == "\\":
                    i += 1  # Skip escaped character
                i += 1
            value = text[start:i]
            if i < len(text):
                i += 1  # Skip closing quote
            tokens.append(Token(value=value, token_type="quoted_string"))
            continue

        # Flag (--something)
        if text[i] == "-" and i + 1 < len(text) and text[i + 1] == "-":
            start = i
            i += 2
            while i < len(text) and not text[i].isspace():
                i += 1
            tokens.append(Token(value=text[start:i], token_type="flag"))
            continue

        # Regular word
        start = i
        while i < len(text) and not text[i].isspace():
            i += 1
        tokens.append(Token(value=text[start:i], token_type="word"))

    return tokens
