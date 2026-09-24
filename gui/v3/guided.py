from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, cast, override

import streamlit as st

MAX_PROJECTION_YEARS = 50

DISPATCHER_F = "dispatcher"
TYPE_F = "type"
NAME_F = "name"
QUESTION_F = "question"
OPTIONS_F = "options"
DEFAULT_F = "default"
CONSTRAINTS_F = "constraints"
HELP_F = "help"
QUESTIONS_F = "questions"
PARENT_F = "parent"

QUESTION_DEF = {
    "Q1": {
        QUESTION_F: "How would you like to use the model[en]",
        TYPE_F: "choice",
        NAME_F: "goal",
        OPTIONS_F: {
            "R1": {
                "text": "When can I retire?[en]|Quand puis-je partir à la retraite?[fr]|Quando puedo irme de retra?[es]",
                "help": "Choose that option if you want to evaluate the risk of retiring too early or if you want to know if you can retire comfortably.[en]|Choisissez cette option si vous souhaitez évaluer le risque de partir trop tôt ou si vous souhaitez savoir si vous pouvez partir confortablement.[fr]|Elige esta opción si quieres evaluar el riesgo de irte demasiado pronto o si quieres saber si puedes irte confortablemente.[es]",
            },
            "R2": {
                "text": "How much pension income can I generate?[en]|Combien de revenu de pension puis-je générer?[fr]|Cuánto ingreso de pension puedo generar?[es]",
                "help": "How much pension income can I generate?[en]|Combien de revenu de pension puis-je générer?[fr]|Cuánto ingreso de pension puedo generar?[es]",
            },
            "R3": {
                "text": "How much do I need to save for retirement?[en]|Combien dois-je épargner pour ma retraite?[fr]|Cuánto necesito ahorrar para mi retra?[es]",
                "help": "How much do I need to save for retirement?[en]|Combien dois-je épargner pour ma retraite?[fr]|Cuánto necesito ahorrar para mi retra?[es]",
            },
            "R4": {
                "text": "Something else[en]|Autre[fr]|Algo más[es]",
                "help": "Something else[en]|Autre[fr]|Algo más[es]",
            },
        },
    },
    "Q2": {
        QUESTION_F: "In what currency do you want to the model to use[en]|Quelle devise souhaitez-vous que le modèle utilise?[fr]|Qué moneda desea que el modelo utilice?[es]",
        TYPE_F: "text",
        NAME_F: "currency",
        DEFAULT_F: "USD",
    },
    "Q3": {
        QUESTION_F: "What is your total wealth[en]|Quel est votre patrimoine total?[fr]|Cuál es tu patrimonio total?[es]",
        TYPE_F: "amount",
        NAME_F: "total_wealth",
        CONSTRAINTS_F: "MustBePositive",
    },
    "Q4": {
        QUESTION_F: "How many years do you want to project[en]|Combien d'années souhaitez-vous projeter?[fr]|Cuántos años deseas proyectar?[es]",
        TYPE_F: "integer",
        NAME_F: "projection_years",
        CONSTRAINTS_F: "projection_years_constraint",
    },
    "Q5": {
        QUESTION_F: "How much annual retirement income do you want[en]|Combien de revenu de pension annuel souhaitez-vous?[fr]|Cuánto ingreso de pension anual deseas?[es]",
        TYPE_F: "amount",
        NAME_F: "target_annual_retirement_income",
        CONSTRAINTS_F: "MustBePositive",
    },
    "Q6": {
        QUESTION_F: "How much are you saving annually[en]|Combien épargnez-vous annuellement?[fr]|Cuánto ahorras anualmente?[es]",
        TYPE_F: "amount",
        NAME_F: "annual_savings",
        CONSTRAINTS_F: "MustBePositive",
    },
}


NAVIGATION_DEF = {
    "nodes": {
        "Node1": {
            TYPE_F: "step",
            NAME_F: "Your Goal[en]|Votre objectif[fr]|Tu objetivo[es]",
            QUESTIONS_F: ["Q1", "Q2", "Q3"],
        },
        "Node2": {
            TYPE_F: "branch",
            DISPATCHER_F: "dispatch_node2",
            PARENT_F: "Node1",
        },
        "Node3": {
            TYPE_F: "step",
            NAME_F: "In & out[en]|Entrée & sortie[fr]|Entrada & salida[es]",
            QUESTIONS_F: ["Q5", "Q6"],
            PARENT_F: "Node2",
        },
    }
}


def dispatch_node2(state: dict[str, str]) -> str | None:
    goal: str = state["goal"]
    branching = {"R1": "Node3", "R2": "Node4", "R3": "Node5", "R4": "Node6"}
    if goal in branching:
        return branching[goal]
    else:
        raise ValueError(f"Invalid goal: {goal}")


class Constraint(ABC):
    @abstractmethod
    def validate(self, answer: str) -> tuple[bool, str]:
        raise NotImplementedError


class MustBePositive(Constraint):
    @override
    def validate(self, answer: str) -> tuple[bool, str]:
        test: bool = float(answer) > 0
        explanation: str = "" if test else "Net wealth must be positive"
        return test, explanation


class ProjectionYearsConstraint(Constraint):
    @override
    def validate(self, answer: str) -> tuple[bool, str]:
        test = int(answer) > 0 and int(answer) <= MAX_PROJECTION_YEARS
        explanation = (
            ""
            if test
            else f"Projection years must be between 1 and {MAX_PROJECTION_YEARS}"
        )
        return test, explanation


class Question(ABC):
    def __init__(self, name: str, question: str):
        self.name: str = name
        self.question: str = question

    @abstractmethod
    def validate(self, answer: str) -> tuple[bool, str]:
        raise NotImplementedError

    @staticmethod
    def createFromDefinition(
        question_name: str, definition: dict[str, Any]
    ) -> Question:
        qtype = definition.get(TYPE_F)
        question: str = definition.get("question", "Question not defined")
        if qtype == "choice":
            return MultipleChoiceQuestion(
                question_name, question, definition["options"]
            )
        elif qtype == "amount":
            return AmountQuestion(question_name, question)
        elif qtype == "integer":
            return IntegerQuestion(question_name, question)
        elif qtype == "yesno":
            return YesNoQuestion(question_name, question)
        elif qtype == "text":
            return TextQuestion(question_name, question)
        else:
            raise ValueError(f"Invalid question type: {qtype}")


class MultipleChoiceQuestion(Question):
    def __init__(self, name: str, question: str, options: list[str]):
        super().__init__(name, question)
        self.options = options

    @override
    def validate(self, answer: str) -> tuple[bool, str]:
        test: bool = answer.lower() in self.options
        explanation: str = "" if test else "Invalid option"
        return test, explanation


class YesNoQuestion(Question):
    def __init__(self, name: str, question: str):
        super().__init__(name, question)
        self.options = ["Yes", "No"]

    @override
    def validate(self, answer: str) -> tuple[bool, str]:
        test: bool = answer.lower() in ["yes", "no"]
        explanation: str = "" if test else "Invalid option"
        return test, explanation


class AmountQuestion(Question):
    def __init__(self, name: str, question: str):
        super().__init__(name, question)

    @override
    def validate(self, answer: str) -> tuple[bool, str]:
        try:
            _ = float(answer)
            return True, ""
        except ValueError:
            return False, "Invalid amount"


class IntegerQuestion(Question):
    def __init__(self, name: str, question: str):
        super().__init__(name, question)

    @override
    def validate(self, answer: str) -> tuple[bool, str]:
        test: bool = answer.isdigit()
        explanation: str = "" if test else "Invalid integer"
        return test, explanation


class TextQuestion(Question):
    def __init__(self, name: str, question: str):
        super().__init__(name, question)

    @override
    def validate(self, answer: str) -> tuple[bool, str]:
        test: bool = True
        explanation: str = ""
        return test, explanation


class Node(ABC):
    def __init__(self, name:str, parent: str | None)-> None:
        self.name: str = name
        self.parent: str | None = parent

    @staticmethod
    def createFromDefinition(
        name: str, Node_definition: dict[str, Any], questions_definition: dict[str, Any]
    ) -> Node:
        parent: str | None = Node_definition.get(PARENT_F, None)
        if Node_definition[TYPE_F] == "step":
            questions = {}
            for qname, qdef in questions_definition.items():
                questions[qname] = Question.createFromDefinition(qname, qdef)
            return StepNode(name=name,parent=parent, questions=questions)
        elif Node_definition[TYPE_F] == "branch":
            dispatcher_name = Node_definition[DISPATCHER_F]
            dispatcher = globals().get(dispatcher_name)
            if not callable(dispatcher):
                raise ValueError(f"Unknown dispatcher: {dispatcher_name}")
            return BranchNode(
                name=name, parent=parent,
                dispatcher=cast(Callable[[dict[str, Any]], str], dispatcher),
            )
        else:
            raise ValueError(f"Invalid node type: {Node_definition['type']}")


class StepNode(Node):
    def __init__(self, name: str, parent: Node | None, questions: dict[str, Question]) -> None:
        super().__init__(name, parent)
        self.questions = questions


class BranchNode(Node):
    def __init__(self, name: str, parent: Node | None, dispatcher: Callable[[dict[str, Any]], str]) -> None:
        super().__init__(name, parent)
        self.dispatcher = dispatcher


class GuidedTour:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.root_node: Node | None = None
        self.current_node: Node | None = None

    def setCurrentNode(self, node: Node| str) -> None:
        if isinstance(node, str):
            node = self.getNodeByName(node)
        self.current_node = node

    def addNode(self, name: str, node: Node, is_start: bool = False) -> None:
        if name in self.nodes:
            raise ValueError(f"Node {name} already exists")
        self.nodes[name] = node
        if is_start:
            self.setRootNode(node)

    def getNodeByName(self, name: str) -> Node:
        if name not in self.nodes:
            raise ValueError(f"Node {name} not found")
        return self.nodes[name]

    def getNodeParent(self, node: Node| str) -> Node | None:
        if isinstance(node, str):
            node = self.getNodeByName(node)
        if node.parent is None:
            return None
        return self.getNodeByName(node.parent)

    def getNodeChildren(self, node: Node| str) -> list[Node]:
        if isinstance(node, Node):
            node_name = node.name
        else:
            node_name = node
        result :list[Node] = []
        for nodec in self.nodes.values():
            if nodec.parent == node_name:
                result.append(nodec)
        return result

    def setRootNode(self, node: Node) -> None:
        if self.root_node is not None:
            raise ValueError(f"Start node already set to {self.root_node.name}")
        self.root_node = node

    def start(self) -> None:
        if self.root_node is None:
            raise ValueError("No start node set")
        self.current_node = self.root_node

    def displayNodeHierarchy(self) -> None:
        for name, node in self.nodes.items():
            print(f"{name}: {node.name}")

    def displayCurrentNode(self) -> None:
        if self.current_node is None:
            raise ValueError("No current node set")
        st.write(self.current_node.name)
        self.setCurrentNode("Node3")

    @staticmethod
    def createFromDefinition(
        node_definition: dict[str, Any], question_definition: dict[str, Any]
    ) -> GuidedTour:
        tour = GuidedTour()
        for name, node_def in node_definition["nodes"].items():
            is_start_node = node_def.get(PARENT_F, None) is None
            node = Node.createFromDefinition(name, node_def, question_definition)
            tour.addNode(name=name, node=node, is_start=is_start_node)
        if not tour.root_node:
            raise ValueError("No start node found")
        return tour


tour = GuidedTour.createFromDefinition(NAVIGATION_DEF, QUESTION_DEF)
tour.start()


def test_guided_tour() -> None:
    n3 = tour.getNodeByName("Node3")
    print(tour.getNodeParent(n3))
    print(tour.getNodeChildren("Node1"))
    tour.displayNodeHierarchy()


if __name__ == "__main__":
    test_guided_tour()
