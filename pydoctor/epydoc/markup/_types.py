"""
Render types from L{docutils.nodes.document} objects. 

This module provides yet another L{ParsedDocstring} subclass.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Union, cast

from pydoctor.epydoc.markup import ParseError, ParsedDocstring
from pydoctor.epydoc.markup.restructuredtext import parse_docstring
from pydoctor.epydoc.markup._pyval_repr import PyvalColorizer
from pydoctor.napoleon.docstring import TokenType, TypeDocstring
from pydoctor.epydoc.docutils import new_document, set_node_attributes

from docutils import nodes

# TODO: This class should use composition instead of multiple inheritence...
class ParsedTypeDocstring(TypeDocstring, ParsedDocstring):
    """
    Add L{ParsedDocstring} interface on top of L{TypeDocstring} and 
    allow to parse types from L{nodes.Node} objects, providing the C{--process-types} option.
    """

    FIELDS = ('type', 'rtype', 'ytype', 'returntype', 'yieldtype')
    
    #                                                   yes this overrides the superclass type!
    _tokens: list[tuple[str | nodes.Node, TokenType]] # type: ignore

    def __init__(self, annotation: Union[nodes.document, str],
                 warns_on_unknown_tokens: bool = False, lineno: int = 0) -> None:
        ParsedDocstring.__init__(self, ())
        if isinstance(annotation, nodes.document):
            TypeDocstring.__init__(self, '', warns_on_unknown_tokens)

            _tokens = self._tokenize_node_type_spec(annotation)
            self._tokens = cast('list[tuple[str | nodes.Node, TokenType]]', 
                                self._build_tokens(_tokens))
            self._trigger_warnings()
        else:
            TypeDocstring.__init__(self, annotation, warns_on_unknown_tokens)
        
        self._lineno = lineno
        self._document = self._parse_tokens()

    @property
    def has_body(self) -> bool:
        return len(self._tokens)>0

    def to_node(self) -> nodes.document:
        return self._document

    def _tokenize_node_type_spec(self, spec: nodes.document) -> List[Union[str, nodes.Node]]:
        def _warn_not_supported(n:nodes.Node) -> None:
            self.warnings.append(f"Unexpected element in type specification field: element '{n.__class__.__name__}'. "
                                    "This value should only contain text or inline markup.")

        tokens: List[Union[str, nodes.Node]] = []
        # Determine if the content is nested inside a paragraph
        # this is generally the case, except for consolidated fields generate documents.
        if spec.children and isinstance(spec.children[0], nodes.paragraph):
            if len(spec.children)>1:
                _warn_not_supported(spec.children[1])
            children = spec.children[0].children
        else:
            children = spec.children
        
        for child in children:
            if isinstance(child, nodes.Text):
                # Tokenize the Text node with the same method TypeDocstring uses.
                tokens.extend(TypeDocstring._tokenize_type_spec(child.astext()))
            elif isinstance(child, nodes.Inline):
                tokens.append(child)
            else:
                _warn_not_supported(child)
        
        return tokens

    _converters: Dict[TokenType, Callable[[str, list[ParseError], int], nodes.Node]] = {
                                        # we're re-using the variable string css 
                                        # class for the whole literal token, it's the
                                        # best approximation we have for now. 
            TokenType.LITERAL: lambda _token, _, __: \
                nodes.inline(_token, _token, classes=[PyvalColorizer.STRING_TAG]),
            
            TokenType.CONTROL: lambda _token, _, __: \
                nodes.emphasis(_token, _token),
            
            TokenType.REFERENCE: lambda _token, warnings, _: \
                parse_docstring(_token, warnings).to_node(), 
            
            TokenType.UNKNOWN: lambda _token, warnings, _: \
                parse_docstring(_token, warnings).to_node(), 
            
            TokenType.OBJ: lambda _token, _, lineno: \
                set_node_attributes(nodes.title_reference(_token, _token), 
                                    # the +1 here is coping with the fact that
                                    # ParseErrors are 1-based but the doutils
                                    # line we're getting form get_lineno() is zero-based.
                                    lineno=lineno+1),
            
            TokenType.DELIMITER: lambda _token, _, __: \
                nodes.Text(_token),
        }

    def _parse_tokens(self) -> nodes.document:
        """
        Convert type to docutils document object.
        """

        document = new_document('code')
        warnings: List[ParseError] = []
        converters = self._converters
        lineno = self._lineno

        elements: list[nodes.Node] = []

        for token, type_ in self._tokens:
            assert token is not None
            converted_token: nodes.Node
            
            if type_ is TokenType.ANY:
                assert isinstance(token, nodes.Node)
                converted_token = token
            else:
                assert isinstance(token, str)
                converted_token = converters[type_](token, warnings, lineno)

            if isinstance(converted_token, nodes.document):
                elements.extend((set_node_attributes(t, document=document) 
                                 for t in converted_token.children))
            else:
                elements.append(set_node_attributes(converted_token, 
                                                    document=document))
        # warnings should be appended once we have called all converters.
        for w in warnings:
            self.warnings.append(w.descr())

        return set_node_attributes(document, children=[
            set_node_attributes(nodes.inline('', '', classes=['literal']), 
                                children=elements, 
                                lineno=self._lineno)])