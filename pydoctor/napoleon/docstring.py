"""
Classes for google-style and numpy-style docstring conversion. 

Forked from ``sphinx.ext.napoleon.docstring``. 

::

    :copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import ast
import collections
from enum import Enum, auto
import re

from functools import partial
from typing import Any, Callable, Deque, Dict, Iterator, List, Optional, Tuple, Union

import attr

from pydoctor.napoleon.iterators import modify_iter, peek_iter

__docformat__ = "numpy en"

_directive_regex = re.compile(r"\.\. \S+::")
_google_section_regex = re.compile(r"^(\s|\w)+:\s*$")
_google_typed_arg_regex = re.compile(r"(.+?)\(\s*(.*[^\s]+)\s*\)")
_numpy_section_regex = re.compile(r'^[=\-`:\'"~^_*+#<>]{2,}\s*$')
_single_colon_regex = re.compile(r"(?<!:):(?!:)")
_xref_or_code_regex = re.compile(
    r"((?::(?:[a-zA-Z0-9]+[\-_+:.])*[a-zA-Z0-9]+:`.+?`)|" r"(?:``.+?``))"
)
_xref_regex = re.compile(r"(?:(?::(?:[a-zA-Z0-9]+[\-_+:.])*[a-zA-Z0-9]+:)?`.+?`)")
_bullet_list_regex = re.compile(r"^(\*|\+|\-)(\s+\S|\s*$)")
_enumerated_list_regex = re.compile(
    r"^(?P<paren>\()?"
    r"(\d+|#|[ivxlcdm]+|[IVXLCDM]+|[a-zA-Z])"
    r"(?(paren)\)|\.)(\s+\S|\s*$)"
)

@attr.s(auto_attribs=True)
class Field:
    """
    Represent a field with a name and/or a type. Commonly a parameter description. 
    It's also used for ``Returns`` section and other sections structured with fields.
    """

    name: str
    """
    The name of the field, can be empty. Let's note that `Field.name` is not the ``field_name`` 
    in the docutils sense (i.e. "param" or "type" for instance). But the actual parameter name. 
    """

    type: str
    """The enventual type of the parameter/return value. """
    
    content: List[str]
    """The content of the field. """

    lineno: int
    """Line number of the field relative to the begening of the docstring. """

    def __bool__(self) -> bool:
        """
        Returns True if the field has any kind of content. 
        """
        return bool(self.name or self.type or self.content)

def is_obj_identifier(string: str) -> bool:
    """
    Is this string a Python object(s) identifier?

    An object identifier is a valid type string.
    But a valid type can be more complex than an object identifier.
    """
    if string.isidentifier() or _xref_regex.match(string):
        return True
    try:
        # We simply try to load the string object with AST, if it's working
        # we consider the string as a valid Python object identifier.
        # Let's say 2048 is the maximum number of caracters
        # that we'll try to parse here since 99% of the time it will
        # suffice, and we don't want to add too much of expensive processing.
        ast.parse(string[:2048])
    except SyntaxError:
        return False
    else:
        return True


def is_type(string: str) -> bool:
    """
    Is this string a type expression that can be parsed
    by `TypeDocstring` without generating any warnings?

    :note: Some string will be parsed without warnings
           even if `is_type` returns `False`.

    :see: `TypeDocstring`
    """
    return (
        is_obj_identifier(string)
        or len(TypeDocstring(string, warns_on_unknown_tokens=True).warnings) == 0
    )
    # The sphinx's implementation allow regular sentences inside type string.
    # But automatically detect that type of construct seems technically hard.
    # Arg warns_on_unknown_tokens allows to narow the checks and match only docstrings
    # that we are 100% sure are type expression.


def is_google_typed_arg(string: str, parse_type: bool = True) -> bool:
    """
    Is this string a valid type expression and/or google-style field name and type expression in parenthesis?

    :note: Behave exactly like `is_type` if ``parse_type=False``.

    Valid strings are like::

        param (list(str), optional)
        list(str), optional
        ValueError

    When ``parse_type=True`` (default), this multi-word field name and type is even recognized::

        multiple words parameter (list(str), optional)

    """
    if is_type(string):
        return True
    else:
        if parse_type:
            match = _google_typed_arg_regex.match(string)
            if match:
                _type = match.group(2)
                if is_type(_type):
                    return True
    return False

class TokenType(Enum):
    LITERAL     = auto()
    OBJ         = auto()
    DELIMITER   = auto()
    CONTROL     = auto()
    REFERENCE   = auto()
    UNKNOWN     = auto()
    ANY         = auto()

@attr.s(auto_attribs=True)
class FreeFormException(Exception):
    """
    Exception to encapsulate the converted lines when numpy-style fields get treated as free form.
    """

    lines: List[str]


class TypeDocstring:
    r"""
    Convert natural language type strings to reStructuredText.

    Syntax is based on `numpydoc <https://numpydoc.readthedocs.io/en/latest/format.html#sections>`_
    type specification with additionnal recognition of `PEP 484 <https://www.python.org/dev/peps/pep-0484/>`_-like type annotations
    (with parentheses or square brackets characters).

    .. list-table:: Exemples of valid type strings and output
        :header-rows: 1

        * - Type string
          - Output

        * - List[str] or list(bytes), optional
          - `List`\ [`str`] or `list`\ (`bytes`), *optional*

        * - {"html", "json", "xml"}, optional
          - ``{"html", "json", "xml"}``, *optional*

        * - list of int or float or None, default: None
          - `list` of `int` or `float` or `None`, *default*: `None`

        * -  \`complicated string\` or \`strIO <twisted.python.compat.NativeStringIO>\`
          - ``complicated string`` or `strIO <twisted.python.compat.NativeStringIO>`

    """
    _natural_language_delimiters_regex_str = (
        r",\sor\s|\sor\s|\sof\s|:\s|\sto\s|,\sand\s|\sand\s"
    )
    _natural_language_delimiters_regex = re.compile(
        f"({_natural_language_delimiters_regex_str})"
    )

    _ast_like_delimiters_regex_str = r",\s|,|[\[]|[\]]|[\(|\)]"
    _ast_like_delimiters_regex = re.compile(f"({_ast_like_delimiters_regex_str})")

    _token_regex = re.compile(
        f"({_natural_language_delimiters_regex_str}"
        f"|{_ast_like_delimiters_regex_str}"
        r'|"(?:\\"|[^"])*"'  # literals "<text>"
        r"|'(?:\\'|[^'])*')"  # literals '<text>'
    )
    _default_regex = re.compile(
        r"^default[^_0-9A-Za-z].*$",
    )

    def __init__(self, annotation: str, warns_on_unknown_tokens: bool = False) -> None:
        self.warnings: List[str] = []
        self._annotation = annotation
        self._warns_on_unknown_tokens = warns_on_unknown_tokens

        _tokens: List[str] = self._tokenize_type_spec(annotation)
        self._tokens: List[Tuple[str, TokenType]] = self._build_tokens(_tokens)

        self._trigger_warnings()

    def _build_tokens(self, _tokens: List[Union[str, Any]]) -> List[Tuple[str, TokenType]]:
        _combined_tokens = self._recombine_set_tokens(_tokens)

        # Save tokens in the form : [("list", TokenType.OBJ), ("(", TokenType.DELIMITER), ("int", TokenType.OBJ), (")", TokenType.DELIMITER)]
        _tokens_with_type_information: List[Tuple[str, TokenType]] = [
            (token, self._token_type(token)) for token in _combined_tokens
        ]

        return _tokens_with_type_information

    def __str__(self) -> str:
        """
        Returns
        -------
        The parsed type in reStructuredText format.
        """
        return self._convert_type_spec_to_rst()
    
    def _trigger_warnings(self) -> None:
        """
        Append some warnings.
        """
        open_parenthesis = 0
        open_square_braces = 0

        for _token, _type in self._tokens:
            if _type is TokenType.DELIMITER and _token in '[]()': 
                if _token == "[": open_square_braces += 1
                elif _token == "(": open_parenthesis += 1
                elif _token == "]": open_square_braces -= 1
                elif _token == ")": open_parenthesis -= 1
        
        if open_parenthesis != 0:
            self.warnings.append("unbalanced parenthesis in type expression")
        if open_square_braces != 0:
            self.warnings.append("unbalanced square braces in type expression")

    @staticmethod
    def _recombine_set_tokens(tokens: List[str]) -> List[str]:
        """
        Merge the special literal choices tokens together.

        Example
        -------
        >>> tokens = ["{", "1", ", ", "2", "}"]
        >>> ann._recombine_set_tokens(tokens)
        ... ["{1, 2}"]
        """
        token_queue = collections.deque(tokens)
        keywords = ("optional", "default")

        def takewhile_set(tokens: Deque[str]) -> Iterator[str]:
            open_obj_delim = 0
            previous_token = None
            while True:
                try:
                    token = tokens.popleft()
                except IndexError:
                    break

                if token == ", ":
                    previous_token = token
                    continue

                if not token.strip():
                    continue

                if token in keywords:
                    tokens.appendleft(token)
                    if previous_token is not None:
                        tokens.appendleft(previous_token)
                    break

                if previous_token is not None:
                    yield previous_token
                    previous_token = None

                if token == "{":
                    open_obj_delim += 1
                elif token == "}":
                    open_obj_delim -= 1

                yield token

                if open_obj_delim == 0:
                    break

        def combine_set(tokens: Deque[str]) -> Iterator[str]:
            while True:
                try:
                    token = tokens.popleft()
                except IndexError:
                    break

                if token == "{":
                    tokens.appendleft("{")
                    yield "".join(takewhile_set(tokens))
                else:
                    yield token

        return list(combine_set(token_queue))

    @classmethod
    def _tokenize_type_spec(cls, spec: str) -> List[str]:
        """
        Split the string in tokens for further processing.
        """

        def postprocess(item: str) -> List[str]:
            if cls._default_regex.match(item):
                default = item[:7]
                # the default value can't be separated by anything other than a single space
                other = item[8:]
                return [default, " ", other]
            elif item == ",":  # Add space after comma if not there
                return [", "]
            else:
                return [item]

        tokens = list(
            item
            for raw_token in cls._token_regex.split(spec)
            for item in postprocess(raw_token)
            if item
        )
        return tokens

    def _token_type(self, token: Union[str, Any]) -> TokenType:
        """
        Find the type of a token. Types are defined in C{TokenType} enum.
        """

        def is_numeric(token: str) -> bool:
            try:
                # use complex to make sure every numeric value is detected as literal
                complex(token)
            except ValueError:
                return False
            else:
                return True

        # If the token is not a string, it's tagged as 'any', 
        # in practice this is used when a docutils.nodes.Element is passed as a token.
        if not isinstance(token, str):
            type_ = TokenType.ANY
        elif (
            self._natural_language_delimiters_regex.match(token)
            or not token.strip()
            or self._ast_like_delimiters_regex.match(token)
        ):
            type_ = TokenType.DELIMITER
        elif (
            is_numeric(token)
            or (token.startswith("{") and token.endswith("}"))
            or (token.startswith('"') and token.endswith('"'))
            or (token.startswith("'") and token.endswith("'"))
        ):
            type_ = TokenType.LITERAL
        elif token.startswith("{"):
            self.warnings.append(f"invalid value set (missing closing brace): {token}")
            type_ = TokenType.LITERAL
        elif token.endswith("}"):
            self.warnings.append(f"invalid value set (missing opening brace): {token}")
            type_ = TokenType.LITERAL
        elif token.startswith("'") or token.startswith('"'):
            self.warnings.append(
                f"malformed string literal (missing closing quote): {token}"
            )
            type_ = TokenType.LITERAL
        elif token.endswith("'") or token.endswith('"'):
            self.warnings.append(
                f"malformed string literal (missing opening quote): {token}"
            )
            type_ = TokenType.LITERAL
        # keyword supported by the reference implementation (numpydoc)
        elif token in (
            "optional",
            "default",
        ):
            type_ = TokenType.CONTROL
        elif _xref_regex.match(token):
            type_ = TokenType.REFERENCE
        elif is_obj_identifier(token):
            type_ = TokenType.OBJ
        else:
            # sphinx.ext.napoleon would consider the type as "obj" even if the string is not a
            # identifier, leading into generating failures when tying to resolve links.
            type_ = TokenType.UNKNOWN

        if type_ is TokenType.UNKNOWN and self._warns_on_unknown_tokens:
            self.warnings.append(f"unknown expresssion in type: {token}")

        return type_

    # add espaced space when necessary
    def _convert_type_spec_to_rst(self) -> str:
        def _convert(
            _token: Tuple[str, TokenType],
            _last_token: Tuple[str, TokenType],
            _next_token: Tuple[str, TokenType],
            _translation: Optional[str] = None,
        ) -> str:
            translation = _translation or "%s"
            if _xref_regex.match(_token[0]) is None:
                converted_token = translation % _token[0]
            else:
                converted_token = _token[0]
            need_escaped_space = False

            if _last_token[1] in token_type_using_rest_markup:
                # the last token has reST markup:
                # we might have to escape

                if not converted_token.startswith(" ") and \
                    not converted_token.endswith(" "):
                    if _next_token != iter_types.sentinel:
                        if _next_token[1] in token_type_using_rest_markup:
                            need_escaped_space = True

                if _token[1] in token_type_using_rest_markup:
                    need_escaped_space = True

            if need_escaped_space:
                converted_token = f"\\ {converted_token}"
            return converted_token

        converters: Dict[
            TokenType, Callable[[Tuple[str, TokenType], Tuple[str, TokenType], Tuple[str, TokenType]], Union[str, Any]]
        ] = {
            TokenType.LITERAL: lambda _token, _last_token, _next_token: _convert(_token, _last_token, _next_token, "``%s``"),
            TokenType.CONTROL: lambda _token, _last_token, _next_token: _convert(_token, _last_token, _next_token, "*%s*"),
            TokenType.DELIMITER: lambda _token, _last_token, _next_token: _convert(_token, _last_token, _next_token),
            TokenType.REFERENCE: lambda _token, _last_token, _next_token: _convert(_token, _last_token, _next_token),
            TokenType.UNKNOWN: lambda _token, _last_token, _next_token: _convert(_token, _last_token, _next_token),
            TokenType.OBJ: lambda _token, _last_token, _next_token: _convert(_token, _last_token, _next_token, "`%s`"),
            TokenType.ANY: lambda _token, _, __: _token,
        }

        # "unknown" could have markup we just don't know!
        token_type_using_rest_markup = [
            TokenType.LITERAL,
            TokenType.OBJ,
            TokenType.CONTROL,
            TokenType.REFERENCE,
            TokenType.UNKNOWN,
        ]

        converted = ""
        last_token: Tuple[Union[str, Any], TokenType] = ("", TokenType.ANY)

        iter_types: peek_iter[Tuple[str, TokenType]] = peek_iter(self._tokens)
        for token, type_ in iter_types:
            next_token = iter_types.peek()
            converted_token = converters[type_]((token, type_), last_token, next_token)
            converted += converted_token
            last_token = (converted_token, type_)

        return converted


class GoogleDocstring:
    """Convert Google style docstrings to reStructuredText.

    Example
    -------

    .. python::
        >>> from pydoctor.napoleon import GoogleDocstring
        >>> docstring = '''One line summary.
        ...
        ... Extended description.
        ...
        ... Args:
        ...   arg1(int): Description of `arg1`
        ...   arg2(str): Description of `arg2`
        ... Returns:
        ...   str: Description of return value.
        ... '''
        >>> print(GoogleDocstring(docstring))
        One line summary.

        Extended description.

        :param arg1: Description of `arg1`
        :type arg1: int
        :param arg2: Description of `arg2`
        :type arg2: str

        :returns: Description of return value.
        :returntype: str
        >>> print(GoogleDocstring(docstring, process_type_fields=True))
        One line summary.

        Extended description.

        :param arg1: Description of `arg1`
        :type arg1: `int`
        :param arg2: Description of `arg2`
        :type arg2: `str`

        :returns: Description of return value.
        :returntype: `str`

    """

    _name_rgx = re.compile(
        r"^\s*((?::(?P<role>\S+):)?`(?P<name>~?[a-zA-Z0-9_.-]+)`|"
        r" (?P<name2>~?[a-zA-Z0-9_.-]+))\s*",
        re.X,
    )

    # overriden
    def __init__(self, docstring: Union[str, List[str]], 
        is_attribute: bool = False, 
        process_type_fields: bool = False,
    ) -> None:
        """
        Parameters
        ----------
        docstring : str or list of str
            The docstring to parse, given either as a string or split into
            individual lines.
        is_attribute: bool
            If the documented object is an attribute,
            it will use the `_parse_attribute_docstring` method.
        process_type_fields: bool
            Whether to process the type fields or to leave them untouched (default) in order to be processed later.
            Value ``process_type_fields=False`` is currently only used in the tests.
        """

        self._is_attribute = is_attribute
        self._process_type_fields = process_type_fields
        
        if isinstance(docstring, str):
            lines = docstring.splitlines()
        else:
            lines = docstring
        self._line_iter: modify_iter[str] = modify_iter(
            lines, modifier=lambda s: s.rstrip()
        )

        self._parsed_lines = []  # type: List[str]
        self._is_in_section = False
        self._section_indent = 0


        self._sections: Dict[str, Callable[[str], List[str]]] = {
            "args": self._parse_parameters_section,
            "arguments": self._parse_parameters_section,
            "attention": partial(self._parse_admonition, "attention"),
            "attributes": self._parse_attributes_section,
            "caution": partial(self._parse_admonition, "caution"),
            "danger": partial(self._parse_admonition, "danger"),
            "error": partial(self._parse_admonition, "error"),
            "example": self._parse_examples_section,
            "examples": self._parse_examples_section,
            "hint": partial(self._parse_admonition, "hint"),
            "important": partial(self._parse_admonition, "important"),
            "keyword args": self._parse_keyword_arguments_section,
            "keyword arguments": self._parse_keyword_arguments_section,
            "methods": self._parse_methods_section,
            "note": partial(self._parse_admonition, "note"),
            "notes": self._parse_notes_section,
            "other parameters": self._parse_parameters_section,  # merge other parameters with main parameters (for now at least).
            "parameters": self._parse_parameters_section,
            "receive": self._parse_parameters_section,  # same as parameters
            "receives": self._parse_parameters_section,  # same as parameters
            "return": self._parse_returns_section,
            "returns": self._parse_returns_section,
            "yield": self._parse_returns_section, # same process as returns section
            "yields": self._parse_returns_section,
            "raise": self._parse_raises_section,
            "raises": self._parse_raises_section,
            "except": self._parse_raises_section,  # add same restructuredtext headers
            "exceptions": self._parse_raises_section,  # add same restructuredtext headers
            "references": self._parse_references_section,
            "see also": self._parse_see_also_section,
            "see": self._parse_see_also_section,  # add "@see:" equivalent
            "tip": partial(self._parse_admonition, "tip"),
            "todo": self._parse_generic_section,  # todos are just rendered as admonition
            "warning": partial(self._parse_admonition, "warning"),
            "warnings": partial(self._parse_admonition, "warning"),
            "warn": self._parse_warns_section,
            "warns": self._parse_warns_section,
        }

        self.warnings: List[Tuple[str, int]] = []
        """
        Warning messages triggered during the conversion.
        """

        self._parse()

    # overriden to enforce rstrip() to value because the result sometime had
    # empty blank line at the end and sometimes not?
    # (probably a inconsistency introduced while porting napoleon to pydoctor)
    def __str__(self) -> str:
        """
        Return the parsed docstring in reStructuredText format.

        Returns
        -------
        str
            Unicode version of the docstring.
        """
        return "\n".join(self.lines()).rstrip()

    def lines(self) -> List[str]:
        """
        Return the parsed lines of the docstring in reStructuredText format.

        Returns
        -------
        list(str)
            The lines of the docstring in a list.
        """
        return self._parsed_lines

    def _consume_indented_block(self, indent: int = 1) -> List[str]:
        lines = []
        line = self._line_iter.peek()
        while not self._is_section_break() and (
            not line or self._is_indented(line, indent)
        ):
            lines.append(next(self._line_iter))
            line = self._line_iter.peek()
        return lines

    def _consume_contiguous(self) -> List[str]:
        lines = []
        while (
            self._line_iter.has_next()
            and self._line_iter.peek()
            and not self._is_section_header()
        ):
            lines.append(next(self._line_iter))
        return lines

    def _consume_empty(self) -> List[str]:
        lines = []
        line = self._line_iter.peek()
        while self._line_iter.has_next() and not line:
            lines.append(next(self._line_iter))
            line = self._line_iter.peek()
        return lines

    # overriden: enforce type pre-processing + made more smart to understand multiline types.
    def _consume_field(
        self, 
        parse_type: bool = True, 
        prefer_type: bool = False,
        **kwargs: Any
    ) -> Field:

        line = next(self._line_iter)
        indent = self._get_indent(line) + 1
        lines = self._dedent(self._consume_indented_block(indent))
        lines.insert(0, line)

        before_colon, colon, _descs = self._partition_multiline_field_on_colon(
            lines, format_validator=partial(is_google_typed_arg, parse_type=parse_type)
        )

        _descs = self.__class__(_descs).lines()

        _name = before_colon
        _type = ""

        if parse_type:
            match = _google_typed_arg_regex.match(before_colon)
            if match:
                _name = match.group(1).strip()
                _type = match.group(2)

        _name = self._escape_args_and_kwargs(_name)

        if prefer_type and not _type:
            _type, _name = _name, _type

        return Field(name=_name, 
                     type=_type, 
                     content=_descs, 
                     lineno=self._line_iter.counter)

    # overriden: Allow any parameters to be passed to _consume_field with **kwargs
    def _consume_fields(
        self,
        parse_type: bool = True,
        prefer_type: bool = False,
        multiple: bool = False,
        **kwargs: Any,
    ) -> List[Field]:
        self._consume_empty()
        fields = []
        while not self._is_section_break():
            f = self._consume_field(parse_type, prefer_type, **kwargs) 
            if multiple and f.name:
                for name in f.name.split(","):
                    fields.append(Field(name=name.strip(), 
                                        type=f.type, 
                                        content=f.content, 
                                        lineno=self._line_iter.counter))
            elif f:
                fields.append(f)
        return fields

    # overriden: add type pre-processing
    def _consume_inline_attribute(self) -> Tuple[str, List[str]]:
        line = next(self._line_iter)
        _type, colon, _desc = self._partition_field_on_colon(line)
        if not colon or not _desc:
            _type, _desc = _desc, _type
            _desc += colon
        _descs = [_desc] + self._dedent(self._consume_to_end())
        _descs = self.__class__(_descs).lines()
        return _type, _descs

    # overriden: alway do type pre-processing.
    # store the section value as type if it matches the is_type() check.
    # note: _name is always empty string.
    def _consume_returns_section(self) -> List[Field]:
        lines = self._dedent(self._consume_to_next_section())
        if lines:

            before_colon, colon, _descs = self._partition_multiline_field_on_colon(
                lines, format_validator=is_type
            )

            _type = ""
            if _descs:
                if colon:
                     # If a colon is detected, this means that the type is explicitely defined
                    _type = before_colon
                else:
                    # multiline free form returns clause
                    _descs.insert(0, before_colon)
            else:
                # single line free form returns clause
                _descs = [before_colon]

            _descs = self.__class__(_descs).lines()
            _name = ""
            return [Field(name=_name,
                      type=_type,
                      content=_descs,
                      lineno=self._line_iter.counter)]
        else:
            return []

    def _consume_section_header(self) -> str:
        section = next(self._line_iter)
        stripped_section = section.strip(":")
        if stripped_section.lower() in self._sections:
            section = stripped_section
        return section

    def _consume_to_end(self) -> List[str]:
        lines = []
        while self._line_iter.has_next():
            lines.append(next(self._line_iter))
        return lines

    def _consume_to_next_section(self) -> List[str]:
        self._consume_empty()
        lines = []
        while not self._is_section_break():
            lines.append(next(self._line_iter))
        return lines + self._consume_empty()

    # new method: handle type pre-processing the same way for google and numpy style.
    def _convert_type(self, _type: str, is_type_field: bool = True, lineno: int = 0) -> str:
        """
        Tokenize the string type and convert it with additional markup and auto linking, 
        with L{TypeDocstring}.
        
        Arguments
        ---------
        _type: bool
            the string type to convert.
        is_type_field: bool
            Whether the string is the content of a ``:type:`` or ``rtype`` field. 
            If this is ``True`` and `GoogleDocstring`'s ``process_type_fields`` is ``False`` (defaults), 
            the type will NOT be converted (instead, it's returned as is) because it will be converted by the code provided by 
            ``ParsedTypeDocstring`` class in a later stage of docstring parsing. 
        """
        if not is_type_field or self._process_type_fields:
            type_spec = TypeDocstring(_type)
            # convert
            _type = str(type_spec)
            # append warnings
            for warn in type_spec.warnings:
                self.warnings.append((warn, lineno))
        return _type

    def _dedent(self, lines: List[str], full: bool = False) -> List[str]:
        if full:
            return [line.lstrip() for line in lines]
        else:
            min_indent = self._get_min_indent(lines)
            return [line[min_indent:] for line in lines]

    # overriden enforce strip_signature_backslash=False
    def _escape_args_and_kwargs(self, name: str) -> str:
        if name[:2] == "**":
            return r"\*\*" + name[2:]
        elif name[:1] == "*":
            return r"\*" + name[1:]
        else:
            return name

    def _fix_field_desc(self, desc: List[str]) -> List[str]:
        if self._is_list(desc):
            desc = [""] + desc
        elif desc[0].endswith("::"):
            desc_block = desc[1:]
            indent = self._get_indent(desc[0])
            block_indent = self._get_initial_indent(desc_block)
            if block_indent > indent:
                desc = [""] + desc
            else:
                desc = ["", desc[0]] + self._indent(desc_block, 4)
        return desc

    def _format_admonition(self, admonition: str, lines: List[str]) -> List[str]:
        lines = self._strip_empty(lines)
        if len(lines) == 1:
            return [f".. {admonition}:: {lines[0].strip()}", ""]
        elif lines:
            lines = self._indent(self._dedent(lines), 3)
            return [f".. {admonition}::", ""] + lines + [""]
        else:
            return [f".. {admonition}::", ""]

    # overriden to avoid extra unecessary blank lines
    def _format_block(
        self, prefix: str, lines: List[str], padding: str = ""
    ) -> List[str]:
        # remove the last line of the block if it's empty
        if not lines[-1]:
            lines.pop(-1)
        if lines:
            if not padding:
                padding = " " * len(prefix)
            result_lines = []
            for i, line in enumerate(lines):
                if i == 0:
                    result_lines.append((prefix + line).rstrip())
                elif line:
                    result_lines.append(padding + line)
                else:
                    result_lines.append("")
            return result_lines
        else:
            return [prefix]

    def _format_docutils_params(
        self,
        fields: List[Field],
        field_role: str = "param",
        type_role: str = "type",
    ) -> List[str]:
        lines = []
        for field in fields:
            desc = self._strip_empty(field.content)
            if any(desc):
                desc = self._fix_field_desc(desc)
                lines.extend(self._format_block(f":{field_role} {field.name}: ", desc))
            else:
                lines.append(f":{field_role} {field.name}:")

            if field.type:
                lines.append(f":{type_role} {field.name}: {self._convert_type(field.type, lineno=field.lineno)}")
        return lines + [""]

    # overriden: Use a style closer to pydoctor's, but it's still not perfect.
    # Manually generate a single field unsing inline restructuredtext markup
    # It's currently used by :
    # - _parse_returns_section()
    # - _parse_yields_section()
    # - _parse_attribute_docstring()
    def _format_field(self, _name: str, _type: str, _desc: List[str], lineno: int = 0) -> List[str]:
        _desc = self._strip_empty(_desc)
        has_desc = any(_desc)
        separator = " - " if has_desc else ""
        if _name:
            if _type:
                field = f"**{_name}**: {self._convert_type(_type, is_type_field=False, lineno=lineno)}{separator}"
            else:
                field = f"**{_name}**{separator}"
        elif _type:
            field = f"{self._convert_type(_type, is_type_field=False, lineno=lineno)}{separator}"
        else:
            field = ""

        if has_desc:
            _desc = self._fix_field_desc(_desc)
            if _desc[0]:
                return [field + _desc[0]] + _desc[1:]
            elif field:
                # Ignore the first line of the field description if if't empty
                return [field] + _desc[1:]
            else:
                return _desc
        else:
            return [field]

    # kept for historical reasons only. Check upstream shpinx's napoleon extension for source code.
    def _format_fields(self, field_type: str, fields: List[Field]) -> List[str]:
        raise NotImplementedError()

    def _get_current_indent(self, peek_ahead: int = 0) -> int:
        line = self._line_iter.peek(peek_ahead + 1)[peek_ahead]
        while line != self._line_iter.sentinel:
            if line:
                return self._get_indent(line)
            peek_ahead += 1
            line = self._line_iter.peek(peek_ahead + 1)[peek_ahead]
        return 0

    def _get_indent(self, line: str) -> int:
        for i, s in enumerate(line):
            if not s.isspace():
                return i
        return len(line)

    def _get_initial_indent(self, lines: List[str]) -> int:
        for line in lines:
            if line:
                return self._get_indent(line)
        return 0

    def _get_min_indent(self, lines: List[str]) -> int:
        min_indent = None
        for line in lines:
            if line:
                indent = self._get_indent(line)
                if min_indent is None:
                    min_indent = indent
                # mypy get error: Statement is unreachable  [unreachable]
                elif indent < min_indent:  # type: ignore
                    min_indent = indent
        return min_indent or 0

    def _indent(self, lines: List[str], n: int = 4) -> List[str]:
        return [(" " * n) + line for line in lines]

    def _is_indented(self, line: str, indent: int = 1) -> bool:
        for i, s in enumerate(line):
            if i >= indent:
                return True
            elif not s.isspace():
                return False
        return False

    def _is_list(self, lines: List[str]) -> bool:
        if not lines:
            return False
        if _bullet_list_regex.match(lines[0]):
            return True
        if _enumerated_list_regex.match(lines[0]):
            return True
        if len(lines) < 2 or lines[0].endswith("::"):
            return False
        indent = self._get_indent(lines[0])
        next_indent = indent
        for line in lines[1:]:
            if line:
                next_indent = self._get_indent(line)
                break
        return next_indent > indent

    def _is_section_header(self) -> bool:
        section = self._line_iter.peek().lower()
        match = _google_section_regex.match(section)
        if match and section.strip(":") in self._sections:
            header_indent = self._get_indent(section)
            section_indent = self._get_current_indent(peek_ahead=1)
            return section_indent > header_indent
        return False

    def _is_section_break(self) -> bool:
        line = self._line_iter.peek()
        return bool(
            not self._line_iter.has_next()
            or self._is_section_header()
            or (
                self._is_in_section
                and line
                and not self._is_indented(line, self._section_indent)
            )
        )

    # overriden: call _parse_attribute_docstring if self._is_attribute is True
    # and add empty blank lines when required
    def _parse(self) -> None:
        self._parsed_lines = self._consume_empty()

        if self._is_attribute:
            # Implicit stop using StopIteration no longer allowed in
            # Python 3.7; see PEP 479
            res = []  # type: List[str]
            try:
                res = self._parse_attribute_docstring()
            except StopIteration:
                pass
            self._parsed_lines.extend(res)

        while self._line_iter.has_next():
            if self._is_section_header():
                try:
                    section = self._consume_section_header()
                    self._is_in_section = True
                    self._section_indent = self._get_current_indent()
                    lines = self._sections[section.lower()](section)
                finally:
                    self._is_in_section = False
                    self._section_indent = 0

                    # Automatically adding a blank line at the begining of the
                    # section if it is not already there.
                    # Fixes https://github.com/twisted/pydoctor/issues/366
                    if self._parsed_lines and self._parsed_lines[-1].strip():
                        lines.insert(0, "")

            else:
                if not self._parsed_lines:
                    lines = self._consume_contiguous() + self._consume_empty()
                else:
                    lines = self._consume_to_next_section()

            self._parsed_lines.extend(lines)

    def _parse_admonition(self, admonition: str, section: str) -> List[str]:
        # type (str, str) -> List[str]
        lines = self._consume_to_next_section()
        return self._format_admonition(admonition, lines)

    def _parse_attribute_docstring(self) -> List[str]:
        _type, _desc = self._consume_inline_attribute()
        lines = self._format_field("", "", _desc)
        if _type:
            lines.extend(["", f":type: {self._convert_type(_type)}"])
        return lines

    # overriden: enforce napoleon_use_ivar=True and ignore noindex option
    # Skip annotations handling
    # overriden 'vartype' is not a pydoctor field, we just use 'type' everywhere
    # TODO: add 'vartype' and 'kwtype' as aliases of 'type' and use them here to output
    #       the most correct reStructuredText.
    def _parse_attributes_section(self, section: str) -> List[str]:
        lines = []
        for f in self._consume_fields():
            field = f":ivar {f.name}: "
            lines.extend(self._format_block(field, f.content))
            if f.type:
                lines.append(f":type {f.name}: {self._convert_type(f.type, lineno=f.lineno)}")

        lines.append("")
        return lines

    def _parse_examples_section(self, section: str) -> List[str]:
        labels = {
            "example": "Example",
            "examples": "Examples",
        }
        label = labels.get(section.lower(), section)
        return self._parse_generic_section(label)

    # overriden: admonition are the default
    def _parse_generic_section(self, section: str) -> List[str]:
        lines = self._strip_empty(self._consume_to_next_section())
        lines = self._dedent(lines)
        header = f".. admonition:: {section}"
        lines = self._indent(lines, 3)
        if lines:
            return [header, ""] + lines + [""]
        else:
            return [header, ""]

    # overriden 'kwtype' is not a pydoctor field, we just use 'type' everywhere
    # + enforce napoleon_use_keyword = True
    def _parse_keyword_arguments_section(self, section: str) -> List[str]:
        fields = self._consume_fields()
        return self._format_docutils_params(
            fields, field_role="keyword", type_role="type"
        )

    # overriden: ignore noindex options + hack something that renders ok as is
    def _parse_methods_section(self, section: str) -> List[str]:
        def _init_methods_section() -> None:
            if not lines:
                lines.extend([".. admonition:: Methods", ""])

        lines = []  # type: List[str]
        for field in self._consume_fields(parse_type=False):
            _init_methods_section()
            lines.append(f"   {self._convert_type(field.name, is_type_field=False, lineno=field.lineno)}")
            if field.content:
                lines.extend(self._indent(field.content, 7))
            lines.append("")
        return lines

    # overriden: admonition are the default + no translation
    def _parse_notes_section(self, section: str) -> List[str]:
        return self._parse_generic_section("Notes")

    # overriden: no translation + enforce napoleon_use_param = True
    def _parse_parameters_section(self, section: str) -> List[str]:
        # Allow to declare multiple parameters at once (ex: x, y: int)
        fields = self._consume_fields(multiple=True)
        return self._format_docutils_params(fields)

    # overriden: This function has now the ability to take the prefer_type=False parameter.
    # This is used by Warns section, so the warns section can be like::
    #   :warns RuntimeWarning: If whatever
    # This allows sections to have compatible syntax as raises syntax BUT not mandatory).
    # If prefer_type=False: If something in the type place of the type
    #   but no description, assume type contains the description, and there is not type in the docs.
    def _parse_raises_section(
        self, section: str, field_type: str = "raises", prefer_type: bool = True
    ) -> List[str]:
        fields = self._consume_fields(parse_type=False, prefer_type=True)
        lines = []  # type: List[str]
        for field in fields:
            _type, _desc = field.type, field.content
            m = self._name_rgx.match(_type)
            if m and m.group("name"):
                _type = m.group("name")
            elif _xref_regex.match(_type):
                pos = _type.find("`")
                _type = _type[pos + 1 : -1]
            _type = " " + _type if _type else ""
            _desc = self._strip_empty(_desc)
            _descs = " " + "\n    ".join(_desc) if any(_desc) else ""
            if _type and not _descs and not prefer_type:
                _descs = _type
                _type = ""
            lines.append(f":{field_type}{_type}:{_descs}")
        if lines:
            lines.append("")
        return lines

    # overriden: no translation
    def _parse_references_section(self, section: str) -> List[str]:
        return self._parse_generic_section("References")

    # overridden: add if any(field): condition not to display empty returns sections
    # this method is used for yields section, too.
    def _parse_returns_section(self, section: str) -> List[str]:
        section = section.lower() + ('s' if not section.endswith('s') else "")
        fields = self._consume_returns_section()
        multi = len(fields) > 1
        if multi:
            use_rtype = False
        else:
            use_rtype = True

        lines = []  # type: List[str]
        for f in fields:
            if use_rtype:
                field = self._format_field(f.name, "", f.content, lineno=f.lineno)
            else:
                field = self._format_field(f.name, f.type, f.content, lineno=f.lineno)

            if multi:
                if lines:
                    lines.extend(self._format_block(" "*(len(section)+2)+" * ", field))
                else:
                    lines.extend(self._format_block(f":{section}: * ", field))
            else:
                if any(field):
                    lines.extend(self._format_block(f":{section}: ", field))
                if f.type and use_rtype:
                    lines.extend([f":{section.rstrip('s')}type: {self._convert_type(f.type, lineno=f.lineno)}", ""])
        if lines and lines[-1]:
            lines.append("")
        return lines

    def _parse_see_also_section(self, section: str) -> List[str]:
        return self._parse_admonition("seealso", section)

    # overriden: no translation + use compatible syntax with raises, but as well as standard field syntax.
    # This mean the the :warns: field can have an argument like: :warns RessourceWarning:
    def _parse_warns_section(self, section: str) -> List[str]:
        return self._parse_raises_section(
            section, field_type="warns", prefer_type=False
        )


    def _partition_field_on_colon(self, line: str) -> Tuple[str, str, str]:
        before_colon = []
        after_colon = []
        colon = ""
        found_colon = False
        for i, source in enumerate(_xref_or_code_regex.split(line)):
            if found_colon:
                after_colon.append(source)
            else:
                m = _single_colon_regex.search(source)
                if (i % 2) == 0 and m:
                    found_colon = True
                    colon = source[m.start() : m.end()]
                    before_colon.append(source[: m.start()])
                    after_colon.append(source[m.end() :])
                else:
                    before_colon.append(source)

        return ("".join(before_colon).strip(), colon, "".join(after_colon).strip())

    # new method: make multiple lines type work seemlessly - for google-style only.
    def _partition_multiline_field_on_colon(
        self, lines: List[str], format_validator: Callable[[str], bool]
    ) -> Tuple[str, str, List[str]]:
        """
        Partition multiple lines on colon. If the type or name span multiple lines, they will be automatically joined.

        Parameters
        ----------
        lines
            Lines to split
        format_validator
            Validator returning `bool` indicates if the value of before_colon is sane.
            If the value is not sane, fall back to `_partition_field_on_colon` behaviour with a warning.
            Note
            ----
            The validator will be called with a one line string as the argument.
            Note
            ----
            Only used for multiline fields.

        Returns
        -------
        before_colon: str
            depending on the context this might be the first
            line of the description or the name with the optional type or the type.
        colon: str
        description: list(str)
            Can contains lines with only white spaces.
        """

        before_colon, colon, after_colon_start = self._partition_field_on_colon(
            lines[0]
        )

        # save before colon string
        before_colon_start = before_colon

        raw_descs = lines[1:]
        _descs = []
        multiline = False

        if not colon:
            # the first line of the field is not complete or malformed.
            if raw_descs:
                # try to complete type info from next lines.
                partinioned_lines = [
                    self._partition_field_on_colon(l) for l in raw_descs
                ]
                for i, p_line in enumerate(partinioned_lines):
                    multiline = True
                    before, colon, after = p_line
                    before_colon += before
                    if colon:
                        if after:
                            _descs.append(after)
                        # If the type spans several lines, it's natural (but bot required) to add indentation
                        # again after to delimit the description
                        _descs.extend(self._dedent(raw_descs[i + 1 :]))
                        # break if colon is detected
                        break

        else:
            # we got a colon on the first line
            if after_colon_start:
                # there is something after the colon, add to to the desc
                _descs = [after_colon_start] + raw_descs
            else:
                _descs = raw_descs

        if not colon:
            # If not colon id detected on any lines, roll back to original behaviour
            before_colon = before_colon_start
            _descs = raw_descs
            multiline = False

        # check format only if multiline
        if multiline and not format_validator(before_colon):
            # If fails check, fall back to original behaviour, with a warning.
            self.warnings.append(
                (
                    f"invalid type: '{before_colon}'. Probably missing colon.",
                    self._line_iter.counter - len(raw_descs),
                )
            )
            before_colon = before_colon_start
            if after_colon_start:
                _descs = [after_colon_start] + raw_descs
            else:
                _descs = raw_descs

        return (before_colon, colon, _descs)

    def _strip_empty(self, lines: List[str]) -> List[str]:
        if lines:
            start = -1
            for i, line in enumerate(lines):
                if line:
                    start = i
                    break
            if start == -1:
                lines = []
            end = -1
            for i in reversed(range(len(lines))):
                line = lines[i]
                if line:
                    end = i
                    break
            if start > 0 or end + 1 < len(lines):
                lines = lines[start : end + 1]
        return lines


class NumpyDocstring(GoogleDocstring):
    """
    Convert NumPy style docstrings to reStructuredText.

    Example
    -------
    
    .. python::
        >>> from pydoctor.napoleon import NumpyDocstring
        >>> docstring = '''One line summary.
        ...
        ... Extended description.
        ...
        ... Parameters
        ... ----------
        ... arg1 : int
        ...     Description of `arg1`
        ... arg2 : str
        ...     Description of `arg2`
        ... Returns
        ... -------
        ... str
        ...     Description of return value.
        ... '''
        >>> print(NumpyDocstring(docstring))
        One line summary.

        Extended description.

        :param arg1: Description of `arg1`
        :type arg1: int
        :param arg2: Description of `arg2`
        :type arg2: str

        :returns: Description of return value.
        :returntype: str
        >>> print(NumpyDocstring(docstring, process_type_fields=True))
        One line summary.

        Extended description.

        :param arg1: Description of `arg1`
        :type arg1: `int`
        :param arg2: Description of `arg2`
        :type arg2: `str`

        :returns: Description of return value.
        :returntype: `str`

    """

    def _escape_args_and_kwargs(self, name: str) -> str:
        func = super()._escape_args_and_kwargs

        if ", " in name:
            return ", ".join(func(param) for param in name.split(", "))
        else:
            return func(name)

    # overriden: remove lookup annotations and resolving https://github.com/sphinx-doc/sphinx/issues/7077
    def _consume_field(
        self,
        parse_type: bool = True,
        prefer_type: bool = False,
        allow_free_form: bool = False,
        **kwargs: Any,
    ) -> Field:
        """
        Raise
        -----
        FreeFormException
           If allow_free_form=True and the type do not match `is_type` check.
           See `_convert_type_and_maybe_consume_free_form_field`.
        """

        line = next(self._line_iter)
        if parse_type:
            _name, _, _type = self._partition_field_on_colon(line)
        else:
            _name, _type = line, ""
        _name, _type = _name.strip(), _type.strip()
        _name = self._escape_args_and_kwargs(_name)

        if _name and not _type and prefer_type:
            _type, _name = _name, _type

        indent = self._get_indent(line) + 1

        # Solving this https://github.com/sphinx-doc/sphinx/issues/7077 if allow_free_form = True

        # We determine if the current line contains the type if the following-up line is indented
        # (that would be the description)
        # formatted with types or not, for that we check if the second line of the field

        next_line = self._line_iter.peek()

        if next_line != self._line_iter.sentinel:
            next_line_indent = self._get_indent(next_line) + 1
            if next_line_indent > indent:
                # Normal case.
                _desc = self._dedent(self._consume_indented_block(indent))
                _desc = self.__class__(_desc).lines()

                return Field(name=_name, 
                             type=_type, 
                             content=_desc, 
                             lineno=self._line_iter.counter)

        # The field either do not provide description and data contains the name and type informations,
        # or the _name and _type variable contains directly the description. i.e.

        # Returns
        # -------
        # fox_speed: float

        # Or

        # Returns
        # -------
        # The computed speed of the fox

        _type = self._convert_type_and_maybe_consume_free_form_field(
            _name, _type, allow_free_form=allow_free_form
        )  # Can raise FreeFormException
        return Field(name=_name, 
                     type=_type, 
                     content=[],
                     lineno=self._line_iter.counter)

    # allow to pass any args to super()._consume_fields(). Used for allow_free_form=True
    def _consume_fields(
        self,
        parse_type: bool = True,
        prefer_type: bool = False,
        multiple: bool = False,
        **kwargs: Any,
    ) -> List[Field]:
        try:
            return super()._consume_fields(
                parse_type=parse_type,
                prefer_type=prefer_type,
                multiple=multiple,
                **kwargs,
            )
        except FreeFormException as e:
            return [Field(name="", 
                          type="", 
                          content=e.lines, 
                          lineno=self._line_iter.counter)]

    # Pass allow_free_form = True
    def _consume_returns_section(self) -> List[Field]:
        return self._consume_fields(prefer_type=True, allow_free_form=True)

    def _consume_section_header(self) -> str:
        section = next(self._line_iter)
        if not _directive_regex.match(section):
            # Consume the header underline
            next(self._line_iter)
        return section

    def _is_section_break(self) -> bool:
        line1, line2 = self._line_iter.peek(2)
        return bool(
            not self._line_iter.has_next()
            or self._is_section_header()
            or ["", ""] == [line1, line2]
            or (
                self._is_in_section
                and line1
                and not self._is_indented(line1, self._section_indent)
            )
        )

    def _is_section_header(self) -> bool:
        section, underline = self._line_iter.peek(2)
        section = section.lower()
        if section in self._sections and isinstance(underline, str):
            return bool(_numpy_section_regex.match(underline))
        return False

    def _convert_type_and_maybe_consume_free_form_field(
        self, _name: str, _type: str, allow_free_form: bool = False
    ) -> str:
        """
        Same as `_convert_type`, but can raise `FreeFormException`.
        Raises
        ------
        FreeFormException
            If allow_free_form=True and _type do not match `is_type` check.
        """
        if is_type(_type) or not allow_free_form:
            return _type
        else:
            # Else we consider it as free form
            _desc = self.__class__(self._consume_to_next_section()).lines()
            raise FreeFormException(lines=[_name + _type] + _desc)

    def _parse_see_also_section(self, section: str) -> List[str]:
        lines = self._consume_to_next_section()
        try:
            return self._parse_numpydoc_see_also_section(lines)
        except ValueError:
            return self._format_admonition("seealso", lines)

    # overriden: do not use interpreted text role in links
    def _parse_numpydoc_see_also_section(self, content: List[str]) -> List[str]:
        """
        Derived from the NumpyDoc implementation of ``_parse_see_also``.
        
        Parses this kind of see also sections::
        
            See Also
            --------
            func_name : Descriptive text
                continued text
            another_func_name : Descriptive text
            func_name1, func_name2, :meth:`func_name`, func_name3
        """
        items: List[Tuple[str, List[str], Optional[str]]] = []

        def parse_item_name(text: str) -> Tuple[str, str]:
            """Match ':role:`name`' or 'name'"""
            m = self._name_rgx.match(text)
            if m:
                g = m.groups()
                if g[1] is None:
                    return g[3], None  # type: ignore [unreachable]
                else:
                    return g[2], g[1]
            raise ValueError(f"{text} is not a item name")

        def push_item(name: Optional[str], rest: List[str]) -> None:
            if not name:
                return
            name, role = parse_item_name(name)
            items.append((name, list(rest), role))
            del rest[:]

        current_func = None
        rest = []  # type: List[str]

        for line in content:
            if not line.strip():
                continue

            m = self._name_rgx.match(line)
            if m and line[m.end() :].strip().startswith(":"):
                push_item(current_func, rest)
                current_func, line = line[: m.end()], line[m.end() :]
                rest = [line.split(":", 1)[1].strip()]
                if not rest[0]:
                    rest = []
            elif not line.startswith(" "):
                push_item(current_func, rest)
                current_func = None
                if "," in line:
                    for func in line.split(","):
                        if func.strip():
                            push_item(func, [])
                elif line.strip():
                    current_func = line
            elif current_func is not None:
                rest.append(line.strip())
        push_item(current_func, rest)

        if not items:
            return []

        lines = []  # type: List[str]
        last_had_desc = True
        for name, desc, role in items:
            # do not use interpreted text role
            link = f"`{name}`"

            if desc or last_had_desc:
                lines += [""]
                lines += [link]
            else:
                lines[-1] += f", {link}"
            if desc:
                lines += self._indent([" ".join(desc)])
                last_had_desc = True
            else:
                last_had_desc = False
        lines += [""]

        return self._format_admonition("seealso", lines)
