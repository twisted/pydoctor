"""
Render types from L{docutils.nodes.document} objects. 

This module provides yet another L{ParsedDocstring} subclass.
"""

from typing import Callable, Dict, List, Tuple, Union

from pydoctor.epydoc.markup import DocstringLinker, ParseError, ParsedDocstring, get_parser_by_name
from pydoctor.node2stan import node2stan
from pydoctor.napoleon.docstring import TokenType, TypeDocstring

from docutils import nodes
from twisted.web.template import Tag, tags

class ParsedTypeDocstring(TypeDocstring, ParsedDocstring):
    """
    Add L{ParsedDocstring} interface on top of L{TypeDocstring} and 
    allow to parse types from L{nodes.Node} objects, providing the C{--process-types} option.
    """
    _tokens: List[Tuple[Union[str, nodes.Node], TokenType]]

    def __init__(self, annotation: Union[nodes.document, str],
                 warns_on_unknown_tokens: bool = False, lineno: int = 0) -> None:
        ParsedDocstring.__init__(self, ())
        if isinstance(annotation, nodes.document):
            TypeDocstring.__init__(self, '', warns_on_unknown_tokens)

            _tokens = self._tokenize_node_type_spec(annotation)
            self._tokens = self._build_tokens(_tokens)
        else:
            TypeDocstring.__init__(self, annotation, warns_on_unknown_tokens)
        
        
        # TODO: do we really need the line number here ?
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

    def _tokenize_node_type_spec(self, spec: nodes.document) -> List[Union[str, nodes.Node]]:
        
        class Tokenizer(nodes.GenericNodeVisitor):
            
            def __init__(self, document: nodes.document) -> None:
                super().__init__(document)
                self.tokens: List[Union[str, nodes.Node]] = []
                self.rest = nodes.document
                self.warnings: List[str] = []

            def default_visit(self, node: nodes.Node) -> None:
                # Tokenize only the first level text in paragraph only,
                # Simply warn and ignore the rest.

                parent = node.parent
                super_parent = parent.parent if parent else None
                
                # first level
                if isinstance(parent, nodes.document) and not isinstance(node, nodes.paragraph):
                    self.warnings.append(f"Unexpected element in type specification field: element '{node.__class__.__name__}'. "
                                            "This field should only contain text or inline markup describing the type (i.e. 'list of dict[str, object], optional')")
                    raise nodes.SkipNode()
                
                # second level
                if isinstance(super_parent, nodes.document):
                    # only text in paragraph nodes are taken into account
                    if isinstance(node, nodes.Text):
                        # Tokenize the Text node with the same method TypeDocstring uses.
                        self.tokens.extend(TypeDocstring._tokenize_type_spec(node.astext()))
                    else:
                        self.tokens.append(node)
                        raise nodes.SkipNode()
    
        tokenizer = Tokenizer(spec)
        spec.walk(tokenizer)
        self._warnings.extend(tokenizer.warnings)
        return tokenizer.tokens

    def _convert_obj_tokens_to_stan(self, tokens: List[Tuple[Union[str, nodes.Node], TokenType]], 
                                    docstring_linker: DocstringLinker) -> List[Tuple[Union[str, Tag, nodes.Node], TokenType]]:
        """
        Convert L{TokenType.OBJ} and PEP 484 like L{TokenType.DELIMITER} type to stan, merge them together. Leave the rest untouched. 

        Exemple:

        >>> tokens = [("list", TokenType.OBJ), ("(", TokenType.DELIMITER), ("int", TokenType.OBJ), (")", TokenType.DELIMITER)]
        >>> ann._convert_obj_tokens_to_stan(tokens, NotFoundLinker())
        ... [(Tag('code', children=['list', '(', 'int', ')']), TokenType.OBJ)]
        
        @param tokens: List of tuples: C{(token, type)}
        """

        combined_tokens: List[Tuple[Union[str, Tag], TokenType]] = []

        open_parenthesis = 0
        open_square_braces = 0

        for _token, _type in tokens:

            if _type is TokenType.OBJ:
                new_token = docstring_linker.link_xref(_token, _token, self._lineno)
                if open_square_braces + open_parenthesis > 0:
                    try: last_processed_token = combined_tokens[-1]
                    except IndexError: 
                        # weird
                        combined_tokens.append((_token, _type))
                    else:
                        if last_processed_token[1] is TokenType.OBJ and isinstance(last_processed_token[0], Tag):
                            # Merge with last Tag
                            last_processed_token[0](*new_token.children)
                        else:
                            # weird
                            combined_tokens.append((new_token, _type))
                else:
                    combined_tokens.append((new_token, _type))

            elif _type is TokenType.DELIMITER: 
                if _token == "[": open_square_braces += 1
                elif _token == "(": open_parenthesis += 1

                if open_square_braces + open_parenthesis > 0:
                    try: last_processed_token = combined_tokens[-1]
                    except IndexError: 
                        # weird
                        combined_tokens.append((_token, _type))
                    else:
                        if last_processed_token[1] is TokenType.OBJ and isinstance(last_processed_token[0], Tag): 
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

        converters: Dict[TokenType, Callable[[Union[str, Tag]], Union[str, Tag]]] = {
            TokenType.LITERAL:      lambda _token: tags.span(_token, class_="literal"),
            TokenType.CONTROL:      lambda _token: tags.em(_token),
            TokenType.REFERENCE:    lambda _token: get_parser_by_name('restructuredtext')(_token, _warnings, False).to_stan(docstring_linker) if isinstance(_token, str) else _token, 
            TokenType.UNKNOWN:      lambda _token: get_parser_by_name('restructuredtext')(_token, _warnings, False).to_stan(docstring_linker) if isinstance(_token, str) else _token, 
            TokenType.OBJ:          lambda _token: _token, # These convertions are done in _convert_obj_tokens_to_stan()
            TokenType.DELIMITER:    lambda _token: _token, 
            TokenType.ANY:          lambda _token: _token, 
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
