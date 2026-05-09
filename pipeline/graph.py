from langgraph.graph import StateGraph, END
from pipeline.state import ComplianceState
from pipeline.nodes.pii_agent import pii_check_node
from pipeline.nodes.confidential_agent import confidential_check_node
from pipeline.nodes.encoding_agent import encoding_check_node
from pipeline.nodes.abusive_agent import abusive_check_node
from pipeline.nodes.aggregator import aggregator_node


def build_compliance_graph():
    """
    Construct the LangGraph compliance pipeline.
    Flow: pii_check -> confidential_check -> encoding_check -> abusive_check -> aggregator -> END
    """
    graph = StateGraph(ComplianceState)

    graph.add_node("pii_check", pii_check_node)
    graph.add_node("confidential_check", confidential_check_node)
    graph.add_node("encoding_check", encoding_check_node)
    graph.add_node("abusive_check", abusive_check_node)
    graph.add_node("aggregator", aggregator_node)

    graph.set_entry_point("pii_check")
    graph.add_edge("pii_check", "confidential_check")
    graph.add_edge("confidential_check", "encoding_check")
    graph.add_edge("encoding_check", "abusive_check")
    graph.add_edge("abusive_check", "aggregator")
    graph.add_edge("aggregator", END)

    return graph.compile()


def build_smart_compliance_graph():
    """
    Enhanced graph with conditional routing:
    - Short PDFs (<5 pages): All checks in sequence
    - Long PDFs (>5 pages): Skip expensive checks on empty pages
    """
    graph = StateGraph(ComplianceState)

    graph.add_node("pii_check", pii_check_node)
    graph.add_node("confidential_check", confidential_check_node)
    graph.add_node("encoding_check", encoding_check_node)
    graph.add_node("abusive_check", abusive_check_node)
    graph.add_node("aggregator", aggregator_node)

    def should_do_deep_check(state: ComplianceState) -> str:
        non_empty = [p for p in state["pages"] if not p["is_empty"]]
        if len(non_empty) == 0:
            return "aggregator"
        return "confidential_check"

    graph.set_entry_point("pii_check")
    graph.add_conditional_edges(
        "pii_check",
        should_do_deep_check,
        {
            "confidential_check": "confidential_check",
            "aggregator": "aggregator"
        }
    )
    graph.add_edge("confidential_check", "encoding_check")
    graph.add_edge("encoding_check", "abusive_check")
    graph.add_edge("abusive_check", "aggregator")
    graph.add_edge("aggregator", END)

    return graph.compile()
