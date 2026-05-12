from langgraph.graph import StateGraph, END
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import time
from pipeline.state import ComplianceState
from pipeline.nodes.pii_agent import pii_check_node
from pipeline.nodes.confidential_agent import confidential_check_node
from pipeline.nodes.encoding_agent import encoding_check_node
from pipeline.nodes.abusive_agent import abusive_check_node
from pipeline.nodes.aggregator import aggregator_node
from pipeline.nodes import call_groq_pii, call_groq_confidential, call_groq_abusive


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


def call_with_retry_multi_key(fn, state_copy, retries=3):
    """Wrapper to retry function calls with exponential backoff on 429 errors."""
    for i in range(retries):
        try:
            return fn(state_copy)
        except Exception as e:
            if "429" in str(e) and i < retries - 1:
                time.sleep(2 ** i)  # 1s, 2s, 4s backoff
            else:
                raise


def parallel_scan_node(state: ComplianceState) -> ComplianceState:
    """
    Parallel scan node: Runs PII, Confidential, and Abusive agents in parallel per page.
    Each agent uses its own API key for maximum throughput.
    Encoding agent runs synchronously after (deterministic, no API call).
    """
    all_pii_findings = []
    all_confidential_findings = []
    all_abusive_findings = []
    all_encoding_findings = []

    non_empty_pages = [p for p in state["pages"] if not p["is_empty"]]
    empty_pages = [p for p in state["pages"] if p["is_empty"]]

    def scan_single_page(page):
        """Scan a single page with all 3 LLM agents in parallel using different API keys."""
        page_num = page["page_number"]
        single_page_state = {**state, "pages": [page]}

        page_pii_findings = []
        page_confidential_findings = []
        page_abusive_findings = []
        page_encoding_findings = []

        # Run 3 LLM agents in parallel for this page, each with its own API key
        with ThreadPoolExecutor(max_workers=3) as agent_executor:
            futures = {}

            # Submit all 3 LLM agents with their respective API keys
            futures[agent_executor.submit(call_with_retry_multi_key, pii_check_node, copy.deepcopy(single_page_state))] = "pii"
            futures[agent_executor.submit(call_with_retry_multi_key, confidential_check_node, copy.deepcopy(single_page_state))] = "confidential"
            futures[agent_executor.submit(call_with_retry_multi_key, abusive_check_node, copy.deepcopy(single_page_state))] = "abusive"

            # Collect results as they complete
            for future in as_completed(futures):
                agent_type = futures[future]
                try:
                    result_state = future.result()
                    if agent_type == "pii":
                        page_pii_findings.extend(result_state.get("pii_findings", []))
                    elif agent_type == "confidential":
                        page_confidential_findings.extend(result_state.get("confidential_findings", []))
                    elif agent_type == "abusive":
                        page_abusive_findings.extend(result_state.get("abusive_findings", []))
                except Exception as e:
                    # Log error but don't fail the entire scan
                    error_finding = {
                        "page_number": page_num,
                        "check_type": agent_type.upper(),
                        "severity": "LOW",
                        "description": f"Agent error: {str(e)[:50]}",
                        "evidence": "Error during parallel execution",
                        "flagged": True
                    }
                    if agent_type == "pii":
                        page_pii_findings.append(error_finding)
                    elif agent_type == "confidential":
                        page_confidential_findings.append(error_finding)
                    elif agent_type == "abusive":
                        page_abusive_findings.append(error_finding)

        # Run encoding check synchronously (deterministic, no API call)
        encoding_result = encoding_check_node(copy.deepcopy(single_page_state))
        page_encoding_findings.extend(encoding_result.get("encoding_findings", []))

        return {
            "page_num": page_num,
            "pii_findings": page_pii_findings,
            "confidential_findings": page_confidential_findings,
            "abusive_findings": page_abusive_findings,
            "encoding_findings": page_encoding_findings
        }

    # Process all non-empty pages in parallel with max_workers=3
    # This respects Groq free tier TPM limit across all 3 keys
    page_results = []
    with ThreadPoolExecutor(max_workers=3) as page_executor:
        future_to_page = {page_executor.submit(scan_single_page, page): page for page in non_empty_pages}

        for future in as_completed(future_to_page):
            result = future.result()
            page_results.append(result)

    # Aggregate findings from all pages
    for result in page_results:
        all_pii_findings.extend(result["pii_findings"])
        all_confidential_findings.extend(result["confidential_findings"])
        all_abusive_findings.extend(result["abusive_findings"])
        all_encoding_findings.extend(result["encoding_findings"])

    # Add empty pages (no findings)
    for page in empty_pages:
        pass  # Empty pages have no findings

    # Update state with all findings
    state["pii_findings"] = all_pii_findings
    state["confidential_findings"] = all_confidential_findings
    state["abusive_findings"] = all_abusive_findings
    state["encoding_findings"] = all_encoding_findings

    return state


def build_smart_compliance_graph():
    """
    Parallel compliance graph with 3 API keys:
    - Runs PII, Confidential, Abusive agents in parallel per page
    - Each agent uses its own API key (3× rate limit)
    - Pages also run in parallel with max_workers=3
    - Encoding agent runs synchronously (deterministic, no API call)
    - Aggregator runs at the end
    """
    graph = StateGraph(ComplianceState)

    graph.add_node("parallel_scan", parallel_scan_node)
    graph.add_node("aggregator", aggregator_node)

    graph.set_entry_point("parallel_scan")
    graph.add_edge("parallel_scan", "aggregator")
    graph.add_edge("aggregator", END)

    return graph.compile()
