from urllib.parse import urlparse

from defusedxml import minidom


def parse_xml(raw_xml: str) -> dict:
    parsed_xml = minidom.parseString(raw_xml)  # minidom from defusedxml
    extracted_data = {}

    document_node = parsed_xml.getElementsByTagName("document")
    extracted_data["document"] = document_node[0].firstChild.nodeValue

    ticket_node = parsed_xml.getElementsByTagName("bptlTicketUuid")
    extracted_data["bptl_ticket_uuid"] = ticket_node[0].firstChild.nodeValue

    return extracted_data


def get_xential_base_url(api_root: str) -> str:
    parsed_url = urlparse(api_root)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"
