"""
Render types from L{docutils.nodes.document} objects. 

This module provides yet another L{ParsedDocstring} subclass.
"""
from __future__ import annotations

from typing import Callable, Dict

from pydoctor.epydoc.markup import ParsedDocstring
from pydoctor.epydoc.markup._pyval_repr import PyvalColorizer
from pydoctor.napoleon.docstring import TokenType, ITokenizer, Tokenizer
from pydoctor.epydoc.docutils import new_document, set_node_attributes, code

from docutils import nodes

class NodeTokenizer(ITokenizer[nodes.document]):
    """
    A type tokenizer for annotation as docutils L{document <nodes.document>}.
    """

    def __init__(self, annotation: nodes.document, *, 
                 warns_on_unknown_tokens: bool) -> None:
        # build tokens and warnings
        self.warnings = warnings = [] # type: list[str]
        raw_tokens = Tokenizer.recombine_sets(self.tokenize_document(annotation, warnings))
        self.tokens = Tokenizer.build(raw_tokens, warnings, warns_on_unknown_tokens)
    
    @staticmethod
    def tokenize_document(spec: nodes.document, warnings: list[str]) -> list[str | nodes.Node]:
        def _warn_not_supported(n:nodes.Node) -> None:
            warnings.append("Unexpected element in type specification field: "
                                 f"element '{n.__class__.__name__}'. This value should "
                                 "only contain text or inline markup.")

        tokens: list[str | nodes.Node] = []
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
                tokens.extend(Tokenizer.tokenize_str(child.astext()))
            elif isinstance(child, nodes.Inline):
                tokens.append(child)
            else:
                _warn_not_supported(child)
        
        return tokens


class ParsedTypeDocstring(ParsedDocstring):
    """
    Add L{ParsedDocstring} interface on top of L{TypeDocstring} and 
    allow to parse types from L{nodes.Node} objects, 
    providing the C{--process-types} option.
    """

    FIELDS = ('type', 'rtype', 'ytype', 'returntype', 'yieldtype')

    def __init__(self, annotation: nodes.document, 
                 warns_on_unknown_tokens: bool = False, 
                 lineno: int = 0) -> None:
        super().__init__(fields=())

        tokenizer = NodeTokenizer(annotation, 
                              warns_on_unknown_tokens=warns_on_unknown_tokens)
        self._tokens = tokenizer.tokens
        self.warnings = tokenizer.warnings
        self._lineno = lineno
        self._document = self._parse_tokens()

    @property
    def has_body(self) -> bool:
        return len(self._tokens)>0

    def to_node(self) -> nodes.document:
        return self._document

    _converters: Dict[TokenType, Callable[[str, int], nodes.Node]] = {
            TokenType.LITERAL: lambda _token, _: nodes.inline(
                                         # we're re-using the STRING_TAG css 
                                         # class for the whole literal token, it's the
                                         # best approximation we have for now. 
                _token, _token, classes=[PyvalColorizer.STRING_TAG]),
            TokenType.CONTROL: lambda _token, _: nodes.emphasis(_token, _token),
            TokenType.OBJ: lambda _token, lineno: set_node_attributes(
                nodes.title_reference(_token, _token), lineno=lineno),
        }

    def _parse_tokens(self) -> nodes.document:
        """
        Convert type to docutils document object.
        """

        document = new_document('code')

        converters = self._converters
        lineno = self._lineno

        elements: list[nodes.Node] = []
        default = lambda _token, _: nodes.Text(_token)

        for _tok in self._tokens:
            token, type_ = _tok.value, _tok.type
            assert token is not None
            converted_token: nodes.Node
            
            if type_ is TokenType.ANY:
                assert isinstance(token, nodes.Node)
                converted_token = token
            else:
                assert isinstance(token, str)
                converted_token = converters.get(type_, default)(token, lineno)

            elements.append(set_node_attributes(converted_token, 
                                                    document=document))

        return set_node_attributes(document, children=[
            set_node_attributes(code('', ''), 
                                children=elements, 
                                document=document, 
                                lineno=lineno+1)])
                                # the +1 here is coping with the fact that
                                # Field.lineno are 0-based but the docutils tree 
                                # is supposed to be 1-based

