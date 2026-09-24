import re
from typing import Literal, cast

Language = Literal["en", "es", "fr", "de", "it", "ja", "pt", "ru", "zh"]

# Languages offered in the page picker. Names are in that language.
LANGUAGE_NAMES: dict[Language, str] = {
    "en": "English",
    "es": "Español(Spanish)",
    "fr": "Français(French)",
    "de": "Deutsch(German)",
    "it": "Italiano(Italian)",
    "ja": "日本語(Japanese)",
    "pt": "Português(Portuguese)",
    "ru": "Русский(Russian)",
    "zh": "中文(Chinese)",
}


class Verbiage:
    def __init__(self, source: str | dict[Language, str]):
        if isinstance(source, str):
            self.source: dict[Language, str] = {}
            for line in source.split("|"):
                match = re.match(r"^(.*)\[([a-z]+)\]$", line)
                if match:
                    text, lang = match.groups()
                else:
                    raise ValueError(f"Invalid line: {line}")
                lang = cast(Language, lang)
                self.source[lang] = text
        else:
            self.source = source
        if "en" not in self.source:
            raise ValueError(f"No English text for {self.source}")

    def to(self, language: Language) -> str:
        if language in self.source:
            return self.source[language]
        else:
            return self.source["en"]
