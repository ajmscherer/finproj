import re
from typing import Literal, cast

Language = Literal["en", "es", "fr", "de", "it", "ja", "pt", "ru", "zh"]

class Verbiage:
    def __init__(self, source:str="Hello, world![en]|Bonjour, le monde![fr]|Hallo, Welt![de]|Ciao, mondo![it]|こんにちは, 世界![ja]|Olá, mundo![pt]|Привет, мир![ru]|你好, 世界![zh]"):
        self.source:dict[Language, str] = {}
        for line in source.split("|"):
            match = re.match(r"^(.*)\[([a-z]+)\]$", line)
            if match:
                text, lang = match.groups()
            else:
                raise ValueError(f"Invalid line: {line}")
            lang = cast(Language, lang)
            self.source[lang] = text
        

    def to(self, language:Language) -> str:
        return self.source[language]


