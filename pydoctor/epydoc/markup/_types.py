"""
Render types from L{docutils.nodes.document} objects. 

This module holds another L{ParsedDocstring} subclass. 
"""

from typing import Callable, Dict, List, Tuple, Union

from pydoctor.epydoc.markup import DocstringLinker, ParseError, ParsedDocstring, get_parser_by_name
from pydoctor.node2stan import node2stan
from pydoctor.napoleon.docstring import TypeDocstring

from docutils import nodes
from twisted.web.template import Tag

class ParsedTypeDocstring(TypeDocstring, ParsedDocstring):
    """
    Add L{ParsedDocstring} interface on top of L{TypeDocstring} and 
    allow to parse types from L{nodes.document} objects, providing the L{--process-types} option.
    """
    _tokens: List[Tuple[Union[str, nodes.Node], str]]

    def __init__(self, annotation: Union[nodes.document, str],
                 warns_on_unknown_tokens: bool = False, lineno: int = 0) -> None:
        if isinstance(annotation, nodes.document):
            super().__init__('', warns_on_unknown_tokens)

            _tokens = self._tokenize_node_type_spec(annotation)
            self._tokens = self._build_tokens(_tokens)
        else:
            super().__init__(annotation, warns_on_unknown_tokens)
        self._lineno = lineno

    @property
    def has_body(self) -> bool:
        return len(self._tokens)>0

    def to_node(self) -> nodes.document:
        """
        Not implemented.
        """
        raise NotImplementedError()

    def to_stan(self, docstring_linker: DocstringLinker) -> Tag:
        """
        Present the type as a stan tree. 
        """
        return self._convert_type_spec_to_stan(docstring_linker)

    @classmethod
    def _tokenize_node_type_spec(cls, spec: nodes.document) -> List[Union[str, nodes.Node]]:
        
        class Tokenizer(nodes.GenericNodeVisitor):
            
            def __init__(self, document: nodes.document) -> None:
                super().__init__(document)
                self.tokens: List[Union[str, nodes.Node]] = []
                self.rest = nodes.document

            def default_visit(self, node: nodes.Node) -> None:
                # Tokenize only the first level or second level text, pass the rest as is

                parent = node.parent
                super_parent = parent.parent if parent else None

                if isinstance(super_parent, nodes.document):
                    # only text in paragraph nodes are taken into account
                    if isinstance(parent, nodes.TextElement):  
                        if isinstance(node, nodes.Text):
                            # Tokenize
                            self.tokens.extend(cls._tokenize_type_spec(node.astext()))

                        else:
                            self.tokens.append(node)
                            raise nodes.SkipNode()
                    else:
                        self.tokens.append(parent)
                        raise nodes.SkipNode()
    
        tokenizer = Tokenizer(spec)
        spec.walk(tokenizer)
        return tokenizer.tokens

    def _convert_obj_tokens_to_stan(self, tokens: List[Tuple[Union[str, nodes.Node], str]], 
                                    docstring_linker: DocstringLinker) -> List[Tuple[Union[str, Tag, nodes.Node], str]]:
        """
        Convert "obj" and "delimiter" type to L{Tag} objects, merge them together. Leave the rest untouched. 

        Exemple:

        >>> tokens = [("list", "obj"), ("(", "delimiter"), ("int", "obj"), (")", "delimiter")]
        >>> ann._convert_obj_tokens_to_stan(tokens, NotFoundLinker())
        ... [(Tag('code', children=['list', '(', 'int', ')']), 'obj')]
        
        @param tokens: List of tuples: C{(token, type)}
        """

        combined_tokens: List[Tuple[Union[str, Tag], str]] = []

        open_parenthesis = 0
        open_square_braces = 0

        for _token, _type in tokens:

            if _type == "obj":
                new_token = docstring_linker.link_xref(_token, _token, self._lineno)
                if open_square_braces + open_parenthesis > 0:
                    try: last_processed_token = combined_tokens[-1]
                    except IndexError: 
                        # weird
                        combined_tokens.append((_token, _type))
                    else:
                        if last_processed_token[1] == "obj" and isinstance(last_processed_token[0], Tag):
                            # Merge with last Tag
                            last_processed_token[0](*new_token.children)
                        else:
                            # weird
                            combined_tokens.append((new_token, _type))
                else:
                    combined_tokens.append((new_token, _type))

            elif _type == "delimiter": 
                if _token == "[": open_square_braces += 1
                elif _token == "(": open_parenthesis += 1

                if open_square_braces + open_parenthesis > 0:
                    try: last_processed_token = combined_tokens[-1]
                    except IndexError: 
                        # weird
                        combined_tokens.append((_token, _type))
                    else:
                        if last_processed_token[1] == "obj" and isinstance(last_processed_token[0], Tag): 
                            # Merge with last Tag
                            last_processed_token[0](_token)
                        else:
                            # weird
                            combined_tokens.append((_token, _type))
                else:
                    combined_tokens.append((_token, _type))

                if _token == "]": open_square_braces -= 1
                elif _token == ")": open_parenthesis -= 1
            else:
                combined_tokens.append((_token, _type))

        return combined_tokens

    def _convert_type_spec_to_stan(self, docstring_linker: DocstringLinker) -> Tag:
        """
        Convert type to L{Tag} object.
        """

        tokens = self._convert_obj_tokens_to_stan(self._tokens, docstring_linker)

        _warnings: List[ParseError] = []

        converters: Dict[str, Callable[[Union[str, Tag]], Union[str, Tag]]] = {
            "literal":      lambda _token: Tag('span', children=[_token], attributes=dict(class_="literal")),
            "control":      lambda _token: Tag('em', children=[_token]),
            "reference":    lambda _token: get_parser_by_name('restructuredtext')(_token, _warnings, False).to_stan(docstring_linker) if isinstance(_token, str) else _token, 
            "unknown":      lambda _token: get_parser_by_name('restructuredtext')(_token, _warnings, False).to_stan(docstring_linker) if isinstance(_token, str) else _token, 
            "obj":          lambda _token: _token, # These convertions are done in _convert_obj_tokens_to_stan()
            "delimiter":    lambda _token: _token, 
        }

        for w in _warnings:
            self._warnings.append(w.descr())

        converted = Tag('')

        for token, type_ in tokens:
            assert token is not None
            if isinstance(token, nodes.Node):
                token = node2stan(token, docstring_linker)
            assert isinstance(token, (str, Tag))
            converted_token = converters[type_](token)
            converted(converted_token)

        return converted
