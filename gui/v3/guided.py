from __future__ import annotations

from abc import ABC
from typing import Any

QUESTION_DEF = {
    "Q1": 
        {
            "question": "How would you like to use the model[en]", 
            "type": "choice", 
            "name": "goal",
            "options": { 
                "R1": "When can I retire?[en]", 
                "R2": "How much pension income can I generate?[en]", 
                "R3": "How much retirement savings do I need?[en]"
                }
                            
        },
    "Q2": {
            "question": "In what currency do you want to see the results[en]",
            "type": "choice",
            "name": "currency",
            "options": ["USD", "EUR", "GBP", "CHF", "JPY", "CNY", "INR", "BRL", "MXN", "ZAR", "RUB", "TRY", "SEK", "NOK", "DKK", "AUD", "CAD", "SGD", "HKD", "NZD", "INR", "BRL", "MXN", "ZAR", "RUB", "TRY", "SEK", "NOK", "DKK", "AUD", "CAD", "SGD", "HKD", "NZD"],
            "default": "USD"
    },
    "Q3": {
            "question": "What is your total wealth[en]",
            "type": "amount",
            "name": "total_wealth",
            "constraints": "MustBePositive"
    },
}


TREE_STRUCTURE = {
    'Node1': { 
                "type": "step",
                "name": "Your Goal",
                "Questions": ["Q1"],
                "Next": "Node2"
            },
    "Node2": {
        "type": "branch",
        "dispatecher": "dispatch_node2",
        },

    }


class Constraint(ABC):
    def validate(self, answer: str) -> tuple[bool, str]:
        raise NotImplementedError

class MustBePositive(Constraint):
    def validate(self, answer: str) -> tuple[bool, str]:
        test = float(answer) > 0
        explanation = "" if test else "Net wealth must be positive"
        return test, explanation

class Question(ABC):
    def __init__(self, question: str):
        self.id = id
        self.question = question

    def validate(self, answer: str) -> bool:
        raise NotImplementedError

    @staticmethod
    def createFromDefinition(definition: dict[str, Any]) -> Question:
        qtype = definition.get("type")
        question: str = definition.get("question", "Question not defined")
        if qtype == "choice":
            return MultipleChoiceQuestion(question, definition["options"])
        elif qtype == "amount":
            return AmountQuestion(question)
        elif qtype == "yesno":
            return YesNoQuestion(question)
        else:
            raise ValueError(f"Invalid question type: {qtype}")

class MultipleChoiceQuestion(Question):
    def __init__(self, question: str, options: list[str]):
        super().__init__(question)
        self.options = options

    def validate(self, answer: str) -> bool:
        return answer.lower() in self.options


class YesNoQuestion(Question):
    def __init__(self, question: str):
        super().__init__(question)
        self.options = ["Yes", "No"]

    def validate(self, answer: str) -> bool:
        return answer.lower() in ["yes", "no"]


class AmountQuestion(Question):
    def __init__(self, question: str):
        super().__init__(question)

    def validate(self, answer: str) -> bool:
        try:
            float(answer)
            return True
        except ValueError:
            return False


class GuidedTour:
    def __init__(self) -> None:
        self.nodes =[]

    @staticmethod
    def createFromDefinition(definition: dict) -> GuidedTour:
