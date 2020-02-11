"""
Typing definitions for JSON-based APIs.

See https://en.wikipedia.org/wiki/JSON#Data_types_and_syntax
"""
from typing import Dict, List, Union

JSONValue = Union[str, float, bool, List["JSONValue"], "Object", None]

Object = Dict[str, JSONValue]

ProcessVariables = Dict[str, Union[str, int, bool]]
