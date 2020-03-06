from typing import Any, Dict


def get_nlx_headers(variables: Dict[str, Any]) -> Dict[str, str]:
    headers = {}
    nlx_subject_identifier = variables.get("NLXSubjectIdentifier")
    if nlx_subject_identifier:
        headers["X-NLX-Request-Subject-Identifier"] = nlx_subject_identifier
    nlx_process_id = variables.get("NLXProcessId")
    if nlx_process_id:
        headers["X-NLX-Request-Process-Id"] = nlx_process_id

    return headers
