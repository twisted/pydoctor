"""
Collection of helper functions related to L{docutils}.
"""
from typing import Iterable, Iterator, Optional, List

from docutils import nodes

def set_nodes_parent(nodes: Iterable[nodes.Node], parent: nodes.Node) -> Iterator[None]:
    """
    Set the parent of the nodes to the defined C{parent} node and return an 
    iterator containing the modified nodes.
    """
    for node in nodes:
        node.parent = parent
        yield node

def set_node_attributes(node: nodes.Node, lineno: int, document: nodes.document, children: Optional[List[nodes.Node]] = None) -> nodes.Node:
    """
    Set the attributes to the Node. 
    This is required to manually construct a docutils document that is consistent.
    """
    node.line = lineno
    node.document = document

    if children:
        node.extend(set_nodes_parent(children, node))

    return node
