"""
Classes for google-style and numpy-style docstring conversion. 

Forked from sphinx.ext.napoleon.docstring. 

Napoleon U{upstream  
<https://github.com/sphinx-doc/sphinx/pulls?q=is%3Apr+napoleon>}
should be checked once in a while to make sure we don't miss any important updates. 

:copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""
import ast
import collections
import re
import warnings
from functools import partial
from typing import Any, Callable, Deque, Dict, Generator, List, Mapping, Optional, Tuple, Union

import attr

from . import Config
from .iterators import modify_iter, peek_iter

__docformat__ = "numpy en"

_directive_regex = re.compile(r'\.\. \S+::')
_google_section_regex = re.compile(r'^(\s|\w)+:\s*$')
_google_typed_arg_regex = re.compile(r'(.+?)\(\s*(.*[^\s]+)\s*\)')
_numpy_section_regex = re.compile(r'^[=\-`:\'"~^_*+#<>]{2,}\s*$')
_single_colon_regex = re.compile(r'(?<!:):(?!:)')
_xref_or_code_regex = re.compile(
    r'((?::(?:[a-zA-Z0-9]+[\-_+:.])*[a-zA-Z0-9]+:`.+?`)|'
    r'(?:``.+?``))')
_xref_regex = re.compile(
    r'(?:(?::(?:[a-zA-Z0-9]+[\-_+:.])*[a-zA-Z0-9]+:)?`.+?`)'
)
_bullet_list_regex = re.compile(r'^(\*|\+|\-)(\s+\S|\s*$)')
_enumerated_list_regex = re.compile(
    r'^(?P<paren>\()?'
    r'(\d+|#|[ivxlcdm]+|[IVXLCDM]+|[a-zA-Z])'
    r'(?(paren)\)|\.)(\s+\S|\s*$)')
_token_regex = re.compile(
    r"(,\sor\s|\sor\s|\sof\s|:\s|\sto\s|,\sand\s|\sand\s|,\s"
    r"|[{]|[}]"
    r"|[\[]|[\]]"
    r"|[\(|\)]"
    r'|"(?:\\"|[^"])*"'
    r"|'(?:\\'|[^'])*')"
)
_default_regex = re.compile(
    r"^default[^_0-9A-Za-z].*$",
)
_SINGLETONS = ("None", "True", "False", "Ellipsis")

@attr.s(auto_attribs=True)
class ConsumeFieldsAsFreeForm(Exception):
    lines: List[str]

class NapoleonWarning(SyntaxWarning):
    pass

class GoogleDocstring:
    """Convert Google style docstrings to reStructuredText.
    Parameters
    ----------
    docstring : `str` or `list` of `str`
        The docstring to parse, given either as a string or split into
        individual lines.
    config: `pydoctor.epydoc.markup.napoleon.Config`. 
        The configuration settings to use. If not given, defaults to the
        config object on `app`; or if `app` is not given defaults to the
        a new `pydoctor.epydoc.markup.napoleon.Config` object.
    is_attribute: `bool`
        If the documented object is an attribute, 
        it will use the `_parse_attribute_docstring` method. 
    Example
    -------
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
    <BLANKLINE>
    Extended description.
    <BLANKLINE>
    :param arg1: Description of `arg1`
    :type arg1: int
    :param arg2: Description of `arg2`
    :type arg2: str
    <BLANKLINE>
    :returns: Description of return value.
    :rtype: str
    <BLANKLINE>
    """

    _name_rgx = re.compile(r"^\s*((?::(?P<role>\S+):)?`(?P<name>~?[a-zA-Z0-9_.-]+)`|"
                           r" (?P<name2>~?[a-zA-Z0-9_.-]+))\s*", re.X)

    # overriden
    def __init__(   self, 
                    docstring: Union[str, List[str]],
                    config: Optional[Config] = None,
                    is_attribute: bool = False          ) -> None:

        self._config = config or Config()
        self._is_attribute = is_attribute
        if isinstance(docstring, str):
            lines = docstring.splitlines()
        else:
            lines = docstring
        self._line_iter: modify_iter[str] = modify_iter(lines, modifier=lambda s: s.rstrip())
        self._parsed_lines = []  # type: List[str]
        self._is_in_section = False
        self._section_indent = 0
        if not hasattr(self, '_directive_sections'):
            self._directive_sections = []  # type: List[str]
        if not hasattr(self, '_sections'):
            self._sections : Dict[str, Callable[[str], List[str]]]= {
                'args': self._parse_parameters_section,
                'arguments': self._parse_parameters_section,
                'attention': partial(self._parse_admonition, 'attention'),
                'attributes': self._parse_attributes_section,
                'caution': partial(self._parse_admonition, 'caution'),
                'danger': partial(self._parse_admonition, 'danger'),
                'error': partial(self._parse_admonition, 'error'),
                'example': self._parse_examples_section,
                'examples': self._parse_examples_section,
                'hint': partial(self._parse_admonition, 'hint'),
                'important': partial(self._parse_admonition, 'important'),
                'keyword args': self._parse_keyword_arguments_section,
                'keyword arguments': self._parse_keyword_arguments_section,
                'methods': self._parse_methods_section,
                'note': partial(self._parse_admonition, 'note'),
                'notes': self._parse_notes_section,
                'other parameters': self._parse_parameters_section, # merge other parameters with main parameters (for now at least). 
                'parameters': self._parse_parameters_section,
                'receive': self._parse_receives_section,
                'receives': self._parse_receives_section,
                'return': self._parse_returns_section,
                'returns': self._parse_returns_section,
                'raise': self._parse_raises_section,
                'raises': self._parse_raises_section,
                'except': self._parse_raises_section, # add same restructuredtext headers 
                'exceptions': self._parse_raises_section, # add same restructuredtext headers 
                'references': self._parse_references_section,
                'see also': self._parse_see_also_section,
                'see': self._parse_see_also_section, # add "@see:" equivalent
                'tip': partial(self._parse_admonition, 'tip'),
                'todo': self._parse_generic_section, # todos are just rendered as admonition
                'warning': partial(self._parse_admonition, 'warning'),
                'warnings': partial(self._parse_admonition, 'warning'),
                'warn': self._parse_warns_section,
                'warns': self._parse_warns_section, 
                'yield': self._parse_yields_section,
                'yields': self._parse_yields_section,
                'usage': self._parse_usage_section,
            } 

            self._load_custom_sections()

        self._warnings: List[Tuple[str, int]] = []
        self._parse()

    # overriden to enforce rstrip() to value because the result sometime had 
    # empty blank line at the end and sometimes not? 
    # (probably a inconsistency introduced while porting napoleon to pydoctor)
    def __str__(self) -> str:
        """Return the parsed docstring in reStructuredText format.
        Returns
        -------
        unicode
            Unicode version of the docstring.
        """
        return '\n'.join(self.lines()).rstrip()

    def lines(self) -> List[str]:
        """Return the parsed lines of the docstring in reStructuredText format.
        Returns
        -------
        list(str)
            The lines of the docstring in a list.
        """
        return self._parsed_lines

    def warnings(self) -> List[Tuple[str, int]]:
        """Return any triggered warnings during the conversion. 
        """
        return self._warnings

    def _consume_indented_block(self, indent: int = 1) -> List[str]:
        lines = []
        line = self._line_iter.peek()
        while(not self._is_section_break() and
              (not line or self._is_indented(line, indent))):
            lines.append(next(self._line_iter))
            line = self._line_iter.peek()
        return lines

    def _consume_contiguous(self) -> List[str]:
        lines = []
        while (self._line_iter.has_next() and
               self._line_iter.peek() and
               not self._is_section_header()):
            lines.append(next(self._line_iter))
        return lines

    def _consume_empty(self) -> List[str]:
        lines = []
        line = self._line_iter.peek()
        while self._line_iter.has_next() and not line:
            lines.append(next(self._line_iter))
            line = self._line_iter.peek()
        return lines

    # overriden: enforce type pre-processing: add backtics over the type if not present
    def _consume_field(self, parse_type: bool = True, prefer_type: bool = False
                       ) -> Tuple[str, str, List[str]]:
        line = next(self._line_iter)

        before, colon, after = self._partition_field_on_colon(line)
        _name, _type, _desc = before, '', after

        if parse_type:
            match = _google_typed_arg_regex.match(before)
            if match:
                _name = match.group(1).strip()
                _type = match.group(2)

        _name = self._escape_args_and_kwargs(_name)

        if prefer_type and not _type:
            _type, _name = _name, _type

        if _type:
            _type = self._convert_type(_type)

        indent = self._get_indent(line) + 1
        _descs = [_desc] + self._dedent(self._consume_indented_block(indent))
        _descs = self.__class__(_descs, self._config).lines()
        return _name, _type, _descs

    # overriden: allow white lines in fields def, this was preventing to add white 
    # lines in a numpy section
    # Allow any parameters to be passed to _consume_field with **kwargs
    def _consume_fields(self, parse_type: bool = True, prefer_type: bool = False,
                        multiple: bool = False, **kwargs:Any) -> List[Tuple[str, str, List[str]]]:
        self._consume_empty()
        fields = []
        while not self._is_section_break():
            # error: Too many arguments for "_consume_field" of "GoogleDocstring"  [call-arg]
            _name, _type, _desc = self._consume_field(parse_type, prefer_type, **kwargs) # type: ignore
            if multiple and _name:
                for name in _name.split(","):
                    fields.append((name.strip(), _type, _desc))
            elif _name or _type or _desc:
                fields.append((_name, _type, _desc,))
        return fields

    #overriden: add type pre-processing 
    def _consume_inline_attribute(self) -> Tuple[str, List[str]]:
        line = next(self._line_iter)
        _type, colon, _desc = self._partition_field_on_colon(line)
        if not colon or not _desc:
            _type, _desc = _desc, _type
            _desc += colon
        _descs = [_desc] + self._dedent(self._consume_to_end())
        _descs = self.__class__(_descs, self._config).lines()
        if _type:
            _type = self._convert_type(_type)
        return _type, _descs

    # overriden: enforce type pre-processing: add backtics over the type if not present
    def _consume_returns_section(self) -> List[Tuple[str, str, List[str]]]:
        lines = self._dedent(self._consume_to_next_section())
        if lines:
            before, colon, after = self._partition_field_on_colon(lines[0])
            _name, _type, _desc = '', '', lines

            if colon:
                if after:
                    _desc = [after] + lines[1:]
                else:
                    _desc = lines[1:]

                _type = before

            if _type:
                _type = self._convert_type(_type)

            _desc = self.__class__(_desc, self._config).lines()
            return [(_name, _type, _desc,)]
        else:
            return []

    def _consume_usage_section(self) -> List[str]:
        lines = self._dedent(self._consume_to_next_section())
        return lines

    def _consume_section_header(self) -> str:
        section = next(self._line_iter)
        stripped_section = section.strip(':')
        if stripped_section.lower() in self._sections:
            section = stripped_section
        # error: Returning Any from function declared to return "str"  [no-any-return]
        return section # type: ignore

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

    #new method: handle type pre-processing the same way for google and numpy style. 
    def _convert_type(self, _type:str) -> str:
        """
        Tokenize the string type and convert it with additional markup and auto linking. 
        """
        # handle warnings line number
        linenum=self._line_iter.counter - 1
        # note: the context manager is modifying global state and therefore is not thread-safe.
        with warnings.catch_warnings(record=True) as catch_warnings:
            warnings.simplefilter("always", category=NapoleonWarning)
            # convert
            _type = _convert_type_spec(_type, 
                    aliases=self._config.napoleon_type_aliases or {},)
            # append warnings
            for warning in catch_warnings:
                self._warnings.append((str(warning.message), linenum))
        return _type

    def _dedent(self, lines: List[str], full: bool = False) -> List[str]:
        if full:
            return [line.lstrip() for line in lines]
        else:
            min_indent = self._get_min_indent(lines)
            return [line[min_indent:] for line in lines]
            
    # overriden enforce strip_signature_backslash=False
    def _escape_args_and_kwargs(self, name: str) -> str:
        if name[:2] == '**':
            return r'\*\*' + name[2:]
        elif name[:1] == '*':
            return r'\*' + name[1:]
        else:
            return name

    def _fix_field_desc(self, desc: List[str]) -> List[str]:
        if self._is_list(desc):
            desc = [''] + desc
        elif desc[0].endswith('::'):
            desc_block = desc[1:]
            indent = self._get_indent(desc[0])
            block_indent = self._get_initial_indent(desc_block)
            if block_indent > indent:
                desc = [''] + desc
            else:
                desc = ['', desc[0]] + self._indent(desc_block, 4)
        return desc

    def _format_admonition(self, admonition: str, lines: List[str]) -> List[str]:
        lines = self._strip_empty(lines)
        if len(lines) == 1:
            return ['.. %s:: %s' % (admonition, lines[0].strip()), '']
        elif lines:
            lines = self._indent(self._dedent(lines), 3)
            return ['.. %s::' % admonition, ''] + lines + ['']
        else:
            return ['.. %s::' % admonition, '']

    # overriden to avoid extra unecessary whitespace 
    def _format_block(self, prefix: str, lines: List[str], padding: str = '') -> List[str]:
        # remove the last line of the block if it's empty
        if not lines[-1]: 
            lines.pop(-1)
        if lines:
            if not padding:
                padding = ' ' * len(prefix)
            result_lines = []
            for i, line in enumerate(lines):
                if i == 0:
                    result_lines.append((prefix + line).rstrip())
                elif line:
                    result_lines.append(padding + line)
                else:
                    result_lines.append('')
            return result_lines
        else:
            return [prefix]

    def _format_docutils_params(self, fields: List[Tuple[str, str, List[str]]],
                                field_role: str = 'param', type_role: str = 'type'
                                ) -> List[str]:
        lines = []
        for _name, _type, _desc in fields:
            _desc = self._strip_empty(_desc)
            if any(_desc):
                _desc = self._fix_field_desc(_desc)
                field = ':%s %s: ' % (field_role, _name)
                lines.extend(self._format_block(field, _desc))
            else:
                lines.append(':%s %s:' % (field_role, _name))

            if _type:
                lines.append(':%s %s: %s' % (type_role, _name, _type))
        return lines + ['']

    # overriden not to return useless empty lines 
    # This method should be used as little as posible in pydoctor
    # since it won't generate sections in a consistent manner with other styling
    # But it's still used by multiple returns values for exemple 
    def _format_field(self, _name: str, _type: str, _desc: List[str]) -> List[str]:
        _desc = self._strip_empty(_desc)
        has_desc = any(_desc)
        separator = ' -- ' if has_desc else ''
        if _name:
            if _type:
                if '`' in _type:
                    field = '**%s** (%s)%s' % (_name, _type, separator)
                else:
                    field = '**%s** (*%s*)%s' % (_name, _type, separator)
            else:
                field = '**%s**%s' % (_name, separator)
        elif _type:
            if '`' in _type:
                field = '%s%s' % (_type, separator)
            else:
                field = '*%s*%s' % (_type, separator)
        else:
            field = ''

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

    def _format_fields(self, field_type: str, fields: List[Tuple[str, str, List[str]]]
                       ) -> List[str]:
        field_type = ':%s:' % field_type.strip()
        padding = ' ' * len(field_type)
        multi = len(fields) > 1
        lines = []  # type: List[str]
        for _name, _type, _desc in fields:
            field = self._format_field(_name, _type, _desc)
            if multi:
                if lines:
                    lines.extend(self._format_block(padding + ' * ', field))
                else:
                    lines.extend(self._format_block(field_type + ' * ', field))
            else:
                lines.extend(self._format_block(field_type + ' ', field))
        if lines and lines[-1]:
            lines.append('')
        return lines

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
                elif indent < min_indent: # type: ignore
                    min_indent = indent
        return min_indent or 0

    def _indent(self, lines: List[str], n: int = 4) -> List[str]:
        return [(' ' * n) + line for line in lines]

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
        if len(lines) < 2 or lines[0].endswith('::'):
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
        if match and section.strip(':') in self._sections:
            header_indent = self._get_indent(section)
            section_indent = self._get_current_indent(peek_ahead=1)
            return section_indent > header_indent
        elif self._directive_sections:
            if _directive_regex.match(section):
                for directive_section in self._directive_sections:
                    if section.startswith(directive_section):
                        return True
        return False

    def _is_section_break(self) -> bool:
        line = self._line_iter.peek()
        return (not self._line_iter.has_next() or
                self._is_section_header() or
                (self._is_in_section and
                    line and
                    not self._is_indented(line, self._section_indent)))

    def _load_custom_sections(self) -> None:
        if self._config.napoleon_custom_sections is not None:
            for entry in self._config.napoleon_custom_sections:
                if isinstance(entry, str):
                    # if entry is just a label, add to sections list,
                    # using generic section logic.
                    self._sections[entry.lower()] = self._parse_custom_generic_section
                else:
                    # otherwise, assume entry is container;
                    # [0] is new section, [1] is the section to alias.
                    # in the case of key mismatch, just handle as generic section.
                    self._sections[entry[0].lower()] = \
                        self._sections.get(entry[1].lower(),
                                           self._parse_custom_generic_section)

    # overriden: call _parse_attribute_docstring if self._is_attribute is True
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
                    if _directive_regex.match(section):
                        lines = [section] + self._consume_to_next_section()
                    else:
                        lines = self._sections[section.lower()](section)
                finally:
                    self._is_in_section = False
                    self._section_indent = 0
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
        lines = self._format_field('', '', _desc)
        if _type:
            lines.extend(['', ':type: %s' % _type])
        return lines

    # overriden: enforce napoleon_use_ivar=True and ignore noindex option
    # Skip annotations handling
    def _parse_attributes_section(self, section: str) -> List[str]:
        lines = []
        for _name, _type, _desc in self._consume_fields():
            field = ':ivar %s: ' % _name
            lines.extend(self._format_block(field, _desc))
            if _type:
                lines.append(':type %s: %s' % (_name, _type))
        
        lines.append('')
        return lines

    def _parse_examples_section(self, section: str) -> List[str]:
        labels = {
            'example': 'Example',
            'examples': 'Examples',
        }
        label = labels.get(section.lower(), section)
        return self._parse_generic_section(label)

    # overriden: admonition are the default for all sections where we don't 
    # have a field equivalent 
    def _parse_custom_generic_section(self, section: str) -> List[str]:
        return self._parse_generic_section(section)

    # overriden: admonition are the default
    def _parse_usage_section(self, section: str) -> List[str]:
        header = ['.. admonition:: Usage', '']
        block = ['   .. python::', '']
        lines = self._consume_usage_section()
        lines = self._indent(lines, 6)
        return header + block + lines + ['']

    # overriden: admonition are the default
    def _parse_generic_section(self, section: str) -> List[str]:
        lines = self._strip_empty(self._consume_to_next_section())
        lines = self._dedent(lines)
        header = '.. admonition:: %s' % section
        lines = self._indent(lines, 3)
        if lines:
            return [header, ''] + lines + ['']
        else:
            return [header, '']

    # overriden 'kwtype' is not a pydoctor field, we just use 'type' everywhere
    # + enforce napoleon_use_keyword = True
    def _parse_keyword_arguments_section(self, section: str) -> List[str]:
        fields = self._consume_fields()
        return self._format_docutils_params(
            fields,
            field_role="keyword",
            type_role="type")
        

    # overriden: ignore noindex options + assign a custom role to display methods as others
    def _parse_methods_section(self, section: str) -> List[str]:
    
        def _init_methods_section():
            if not lines:
                # lines.extend(['.. role:: meth','   :class: code py-defname', ])
                lines.extend(['.. admonition:: Methods', ''])

        lines = []  # type: List[str]
        for _name, _, _desc in self._consume_fields(parse_type=False):
            _init_methods_section()
            lines.append('    - %s' % self._convert_type(_name))
            if _desc:
                lines.extend(self._indent(_desc, 6))
            lines.append('')
        return lines

    # overriden: admonition are the default + no translation
    def _parse_notes_section(self, section: str) -> List[str]:
        return self._parse_generic_section('Notes')


    # overriden: no translation + enforce napoleon_use_param = True
    def _parse_parameters_section(self, section: str) -> List[str]:
            # Allow to declare multiple parameters at once (ex: x, y: int)
            fields = self._consume_fields(multiple=True)
            return self._format_docutils_params(fields)
    
    # overriden: This function has now the ability to pass prefer_type=False
    # This is used by Warns section, so the warns section can be like::
    #   :warns RuntimeWarning: If whatever 
    # This allows sections to have compatible syntax as raises syntax BUT not mandatory). 
    # If prefer_type=False: If something in the type place of the type
    #   but no description, assume type contains the description, and there is not type in the docs. 
    def _parse_raises_section(self, section: str, field_type: str = 'raises', prefer_type: bool = True) -> List[str]:
        fields = self._consume_fields(parse_type=False, prefer_type=True)
        lines = []  # type: List[str]
        for _name, _type, _desc in fields:
            m = self._name_rgx.match(_type)
            if m and m.group('name'):
                _type = m.group('name')
            elif _xref_regex.match(_type):
                pos = _type.find('`')
                _type = _type[pos + 1:-1]
            _type = ' ' + _type if _type else ''
            _desc = self._strip_empty(_desc)
            _descs = ' ' + '\n    '.join(_desc) if any(_desc) else ''
            if _type and not _descs and not prefer_type: 
                _descs, _type = _type, _descs
            lines.append(':%s%s:%s' % (field_type, _type, _descs))
        if lines:
            lines.append('')
        return lines

    # overriden: no translation + enforce napoleon_use_param = True
    def _parse_receives_section(self, section: str) -> List[str]:
            # Allow to declare multiple parameters at once (ex: x, y: int)
            fields = self._consume_fields(multiple=True)
            return self._format_docutils_params(fields)


    # overriden: no translation
    def _parse_references_section(self, section: str) -> List[str]:
        return self._parse_generic_section('References')

    # overridden: add if any(field): condition not to display empty returns sections
    def _parse_returns_section(self, section: str) -> List[str]:
        fields = self._consume_returns_section()
        multi = len(fields) > 1
        if multi:
            use_rtype = False
        else:
            use_rtype = True

        lines = []  # type: List[str]
        for _name, _type, _desc in fields:
            if use_rtype:
                field = self._format_field(_name, '', _desc)
            else:
                field = self._format_field(_name, _type, _desc)

            if multi:
                if lines:
                    lines.extend(self._format_block('          * ', field))
                else:
                    lines.extend(self._format_block(':returns: * ', field))
            else:
                if any(field): 
                    lines.extend(self._format_block(':returns: ', field))
                if _type and use_rtype:
                    lines.extend([':rtype: %s' % _type, ''])
        if lines and lines[-1]:
            lines.append('')
        return lines

    def _parse_see_also_section(self, section: str) -> List[str]:
        return self._parse_admonition('seealso', section)

    # overriden: no translation + use compatible syntax with raises, but as well as standard field syntax. 
    # This mean the the :warns: field can have an argument like: :warns RessourceWarning:
    def _parse_warns_section(self, section: str) -> List[str]:
        return self._parse_raises_section(section, field_type='warns', prefer_type=False)

    # overriden: no translation
    def _parse_yields_section(self, section: str) -> List[str]:
        fields = self._consume_returns_section()
        return self._format_fields('Yields', fields)

    def _partition_field_on_colon(self, line: str) -> Tuple[str, str, str]:
        before_colon = []
        after_colon = []
        colon = ''
        found_colon = False
        for i, source in enumerate(_xref_or_code_regex.split(line)):
            if found_colon:
                after_colon.append(source)
            else:
                m = _single_colon_regex.search(source)
                if (i % 2) == 0 and m:
                    found_colon = True
                    colon = source[m.start(): m.end()]
                    before_colon.append(source[:m.start()])
                    after_colon.append(source[m.end():])
                else:
                    before_colon.append(source)

        return ("".join(before_colon).strip(),
                colon,
                "".join(after_colon).strip())


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
                lines = lines[start:end + 1]
        return lines


# preprocessing numpydoc types: https://github.com/sphinx-doc/sphinx/pull/7690
def _recombine_set_tokens(tokens: List[str]) -> List[str]:
    token_queue = collections.deque(tokens)
    keywords = ("optional", "default")

    def takewhile_set(tokens: Deque) -> Generator:
        open_braces = 0
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
                open_braces += 1
            elif token == "}":
                open_braces -= 1

            yield token

            if open_braces == 0:
                break

    def combine_set(tokens: Deque):
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


def _tokenize_type_spec(spec: str) -> List[str]:
    def postprocess(item):
        if _default_regex.match(item):
            default = item[:7]
            # the default value can't be separated by anything other than a single space
            other = item[8:]
            return [default, " ", other]
        else:
            return [item]

    tokens = list(
        item
        for raw_token in _token_regex.split(spec)
        for item in postprocess(raw_token)
        if item
    )
    return tokens


def _token_type(token: str) -> str:
    def is_numeric(token):
        try:
            # use complex to make sure every numeric value is detected as literal
            complex(token)
        except ValueError:
            return False
        else:
            return True

    if token.startswith(" ") or token.endswith(" ") or token in ["[", "]", "(", ")"]:
        type_ = "delimiter"
    elif (
            is_numeric(token) or
            (token.startswith("{") and token.endswith("}")) or
            (token.startswith('"') and token.endswith('"')) or
            (token.startswith("'") and token.endswith("'")) 
    ):
        type_ = "literal"
    elif token.startswith("{"):
        warnings.warn(
            "type pre-processing: invalid value set (missing closing brace): %s"%token, 
            category=NapoleonWarning, 
        )
        type_ = "literal"
    elif token.endswith("}"):
        warnings.warn(
            "type pre-processing: invalid value set (missing opening brace): %s"%token, 
            category=NapoleonWarning, 
        )
        type_ = "literal"
    elif token.startswith("'") or token.startswith('"'):
        warnings.warn(
            "type pre-processing: malformed string literal (missing closing quote): %s"%token, 
            category=NapoleonWarning, 
        )
        type_ = "literal"
    elif token.endswith("'") or token.endswith('"'):
        warnings.warn(
            "type pre-processing: malformed string literal (missing opening quote): %s"%token, 
            category=NapoleonWarning, 
        )
        type_ = "literal"
    elif token in ("optional", "default", ):
        # default is not a official keyword (yet) but supported by the
        # reference implementation (numpydoc) and widely used
        type_ = "control"
    elif _xref_regex.match(token):
        type_ = "reference"
    else:
        type_ = "obj"

    return type_

# overriden: just use simple backticks for cross ref and add espaced space when necessary 
# to able to split on braquets carcaters: need escaped spaces handling to separate reST markup. 
# also use this function to pre-process google-style types. 
def _convert_type_spec(_type: str, aliases: Mapping[str, str] = {}) -> str:

    def _get_alias(_token:str, aliases:Mapping[str, str]):
        alias = aliases.get(_token, _token)
        return alias

    def _convert(_token:Tuple[str, str], _last_token:Tuple[str, str], _next_token:Tuple[str, str], _translation:str=None):
        translation = _translation or "%s"
        if _xref_regex.match(_token[0]) is None:
            converted_token = translation % _token[0]
        else:
            converted_token = _token[0]
        need_escaped_space = False
        
        if _last_token[1] in token_type_using_rest_markup:
            # the last token has reST markup: 
            #   only those three types defines additionnal markup, see `converters`
            # we might have to escape

            if not converted_token.startswith(" ") and not converted_token.endswith(" "):
                if _next_token != iter_types.sentinel:
                    if _next_token[1] in token_type_using_rest_markup:
                        need_escaped_space = True
            
            if _token[1] in token_type_using_rest_markup:
                need_escaped_space = True

        if need_escaped_space:
            converted_token = f"\\ {converted_token}"
        return converted_token

    tokens = _tokenize_type_spec(_type)
    combined_tokens = _recombine_set_tokens(tokens)
    types = [
        (token, _token_type(token))
        for token in combined_tokens
    ]

    converters = {
        "literal": lambda _token, _last_token, _next_token: _convert(_token, _last_token, _next_token, "``%s``"),
        "obj": lambda _token, _last_token, _next_token: _convert((_get_alias(_token[0], aliases), _token[1]), _last_token, _next_token, "`%s`"),
        "control": lambda _token, _last_token, _next_token: _convert(_token, _last_token, _next_token, "*%s*"),
        "delimiter": lambda _token, _last_token, _next_token: _convert(_token, _last_token, _next_token), 
        "reference": lambda _token, _last_token, _next_token: _convert(_token, _last_token, _next_token), 
    }

    token_type_using_rest_markup = ["literal", "obj", "control"]

    converted = ""
    last_token = ("", "")

    iter_types: peek_iter[Tuple[str, str]] = peek_iter(types)
    for token, type_ in iter_types:
        next_token = iter_types.peek()
        converted_token = converters.get(type_)((token, type_), last_token, next_token)
        converted += converted_token
        last_token = (converted_token, type_)

    return converted


class NumpyDocstring(GoogleDocstring):
    """Convert NumPy style docstrings to reStructuredText.
    Parameters
    ----------
    docstring : :obj:`str` or :obj:`list` of :obj:`str`
        The docstring to parse, given either as a string or split into
        individual lines.
    config: :obj:`sphinx.ext.napoleon.Config` or :obj:`sphinx.config.Config`
        The configuration settings to use. If not given, defaults to the
        config object on `app`; or if `app` is not given defaults to the
        a new :class:`sphinx.ext.napoleon.Config` object.
    Other Parameters
    ----------------
    app : :class:`sphinx.application.Sphinx`, optional
        Application object representing the Sphinx process.
    what : :obj:`str`, optional
        A string specifying the type of the object to which the docstring
        belongs. Valid values: "module", "class", "exception", "function",
        "method", "attribute".
    name : :obj:`str`, optional
        The fully qualified name of the object.
    obj : module, class, exception, function, method, or attribute
        The object to which the docstring belongs.
    options : :class:`sphinx.ext.autodoc.Options`, optional
        The options given to the directive: an object with attributes
        inherited_members, undoc_members, show_inheritance and noindex that
        are True if the flag option of same name was given to the auto
        directive.
    Example
    -------
    >>> from sphinx.ext.napoleon import Config
    >>> config = Config(napoleon_use_param=True, napoleon_use_rtype=True)
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
    >>> print(NumpyDocstring(docstring, config))
    One line summary.
    <BLANKLINE>
    Extended description.
    <BLANKLINE>
    :param arg1: Description of `arg1`
    :type arg1: int
    :param arg2: Description of `arg2`
    :type arg2: str
    <BLANKLINE>
    :returns: Description of return value.
    :rtype: str
    <BLANKLINE>
    Methods
    -------
    __str__()
        Return the parsed docstring in reStructuredText format.
        Returns
        -------
        str
            UTF-8 encoded version of the docstring.
    __unicode__()
        Return the parsed docstring in reStructuredText format.
        Returns
        -------
        unicode
            Unicode version of the docstring.
    lines()
        Return the parsed lines of the docstring in reStructuredText format.
        Returns
        -------
        list(str)
            The lines of the docstring in a list.
    warnings()
        List of generated numpy-style warnings. 
        Returns
        -------
        list of tuple[str, int]
            List of tuples (description, linenum)
    """
    def __init__(self, docstring: Union[str, List[str]], config: Optional[Config] = None, is_attribute: bool = False) -> None:
        super().__init__(docstring, config, is_attribute)
    

    def _escape_args_and_kwargs(self, name: str) -> str:
        func = super()._escape_args_and_kwargs

        if ", " in name:
            return ", ".join(func(param) for param in name.split(", "))
        else:
            return func(name)

    # overriden: remove lookup annotations and resolving sphinx/issues/7077
    def _consume_field(self, parse_type: bool = True, prefer_type: bool = False, 
                       allow_free_form: bool = False) -> Tuple[str, str, List[str]]:
        """
        Raise
        -----
        ConsumeFieldsAsFreeForm
            If the type is not obvious and _consume_field(allow_free_form=True), only used for the returns section. 
        """
        def is_obvious_type(_type: str) -> bool:
            if _type.isidentifier() or _xref_regex.match(_type) :
                return True
            try:
                # We simply try to load the string object with AST, if it's working 
                # chances are it's a type annotation like type. 
                # Let's say 2048 is the maximum number of caracters 
                # that we'll try to parse here since 99% of the time it will 
                # suffice, and we don't want to add too much of expensive processing. 
                ast.parse(_type[:2048])
            except SyntaxError:
                return False
            else:
                return True

        def figure_type(_name: str, _type: str) -> str:
            # Here we "guess" if _type contains the type
            if is_obvious_type(_type):
                _type = self._convert_type(_type)
                return _type

            elif allow_free_form: # Else we consider it as free form
                _desc = self.__class__(self._consume_to_next_section(), self._config).lines()
                raise ConsumeFieldsAsFreeForm(lines=[_name + _type] + _desc)
            
            else:
                _type = self._convert_type(_type)
                return _type
                
        line = next(self._line_iter)
        if parse_type:
            _name, _, _type = self._partition_field_on_colon(line)
        else:
            _name, _type = line, ''
        _name, _type = _name.strip(), _type.strip()
        _name = self._escape_args_and_kwargs(_name)

        if _name and not _type and prefer_type:
            _type, _name = _name, _type
        
        indent = self._get_indent(line) + 1

        # Solving this https://github.com/sphinx-doc/sphinx/issues/7077 only if allow_free_form = True
        # to properly solve this issue we need to determine if the section is
        # formatted with types or not, for that we check if the second line of the field is indented 
        # (that would be the description)

        next_line = self._line_iter.peek()

        if next_line != self._line_iter.sentinel:
            next_line_indent = self._get_indent(next_line) + 1
            if next_line_indent > indent:
                _desc = self._dedent(self._consume_indented_block(indent))
                _desc = self.__class__(_desc, self._config).lines()
                _type = self._convert_type(_type)
                # Normal case
                return _name, _type, _desc
        
        return _name, figure_type(_name, _type), []


    def _consume_fields(self, parse_type: bool = True, prefer_type: bool = False, 
                        multiple: bool = False, allow_free_form: bool = False ) -> List[Tuple[str, str, List[str]]]:
        try:
            return super()._consume_fields(parse_type=parse_type, 
                prefer_type=prefer_type, multiple=multiple, allow_free_form=allow_free_form)
        except ConsumeFieldsAsFreeForm as e:
            return [('', '', e.lines)]

    def _consume_returns_section(self) -> List[Tuple[str, str, List[str]]]:
        return self._consume_fields(prefer_type=True, 
            allow_free_form=self._config.napoleon_numpy_returns_allow_free_from)

    def _consume_raises_section(self) -> List[Tuple[str, str, List[str]]]:
        return self._consume_fields(prefer_type=True)
        
    def _consume_section_header(self) -> str:
        section = next(self._line_iter)
        if not _directive_regex.match(section):
            # Consume the header underline
            next(self._line_iter)
        return section

    def _is_section_break(self) -> bool:
        line1, line2 = self._line_iter.peek(2)
        return (not self._line_iter.has_next() or
                self._is_section_header() or
                ['', ''] == [line1, line2] or
                (self._is_in_section and
                    line1 and
                    not self._is_indented(line1, self._section_indent)))

    def _is_section_header(self) -> bool:
        section, underline = self._line_iter.peek(2)
        section = section.lower()
        if section in self._sections and isinstance(underline, str):
            return bool(_numpy_section_regex.match(underline))
        elif self._directive_sections:
            if _directive_regex.match(section):
                for directive_section in self._directive_sections:
                    if section.startswith(directive_section):
                        return True
        return False

    def _parse_see_also_section(self, section: str) -> List[str]:
        lines = self._consume_to_next_section()
        try:
            return self._parse_numpydoc_see_also_section(lines)
        except ValueError:
            return self._format_admonition('seealso', lines)

    def _parse_numpydoc_see_also_section(self, content: List[str]) -> List[str]:
        """
        Derived from the NumpyDoc implementation of _parse_see_also.
        See Also
        --------
        func_name : Descriptive text
            continued text
        another_func_name : Descriptive text
        func_name1, func_name2, :meth:`func_name`, func_name3
        """
        items = []

        def parse_item_name(text: str) -> Tuple[str, str]:
            """Match ':role:`name`' or 'name'"""
            m = self._name_rgx.match(text)
            if m:
                g = m.groups()
                if g[1] is None:
                    return g[3], None
                else:
                    return g[2], g[1]
            raise ValueError("%s is not a item name" % text)

        def push_item(name: str, rest: List[str]) -> None:
            if not name:
                return
            name, role = parse_item_name(name)
            items.append((name, list(rest), role))
            del rest[:]

        def translate(func, description, role):
            translations = self._config.napoleon_type_aliases
            if role is not None or not translations:
                return func, description, role

            translated = translations.get(func, func)
            match = self._name_rgx.match(translated)
            if not match:
                return translated, description, role

            groups = match.groupdict()
            role = groups["role"]
            new_func = groups["name"] or groups["name2"]

            return new_func, description, role

        current_func = None
        rest = []  # type: List[str]

        for line in content:
            if not line.strip():
                continue

            m = self._name_rgx.match(line)
            if m and line[m.end():].strip().startswith(':'):
                push_item(current_func, rest)
                current_func, line = line[:m.end()], line[m.end():]
                rest = [line.split(':', 1)[1].strip()]
                if not rest[0]:
                    rest = []
            elif not line.startswith(' '):
                push_item(current_func, rest)
                current_func = None
                if ',' in line:
                    for func in line.split(','):
                        if func.strip():
                            push_item(func, [])
                elif line.strip():
                    current_func = line
            elif current_func is not None:
                rest.append(line.strip())
        push_item(current_func, rest)

        if not items:
            return []

        # apply type aliases
        items = [
            translate(func, description, role)
            for func, description, role in items
        ]

        lines = []  # type: List[str]
        last_had_desc = True
        for name, desc, role in items:
            
            link = '`%s`' % name
            
            if desc or last_had_desc:
                lines += ['']
                lines += [link]
            else:
                lines[-1] += ", %s" % link
            if desc:
                lines += self._indent([' '.join(desc)])
                last_had_desc = True
            else:
                last_had_desc = False
        lines += ['']

        return self._format_admonition('seealso', lines)