# epydoc -- Marked-up Representations for Python Values
#
# Copyright (C) 2005 Edward Loper
# Author: Edward Loper <edloper@loper.org>
# URL: <http://epydoc.sf.net>
#

"""
Syntax highlighter for Python values.  Currently provides special
colorization support for:

  - lists, tuples, sets, frozensets, dicts
  - numbers
  - strings
  - compiled regexps
  - a variety of AST expressions

The highlighter also takes care of line-wrapping, and automatically
stops generating repr output as soon as it has exceeded the specified
number of lines (which should make it faster than pprint for large
values).  It does I{not} bother to do automatic cycle detection,
because maxlines is typically around 5, so it's really not worth it.

The syntax-highlighted output is encoded using a
L{ParsedDocstring}, which can then be used to generate output in
a variety of formats.

B{Implementation note}: we use exact tests for builtin classes (list, etc)
rather than using isinstance, because subclasses might override
C{__repr__}.

B{Usage}: 
>>> 
"""

__docformat__ = 'epytext en'

import re
import ast
import functools
import sys
from inspect import signature
from typing import Any, AnyStr, Union, Callable, Dict, Iterable, Sequence, Optional, List, Tuple, cast

import attr
import astor.op_util
from docutils import nodes, utils
from twisted.web.template import Tag

from pydoctor.epydoc import sre_parse36, sre_constants36 as sre_constants
from pydoctor.epydoc.markup import DocstringLinker
from pydoctor.epydoc.markup.restructuredtext import ParsedRstDocstring
from pydoctor.epydoc.docutils import set_node_attributes, wbr, obj_reference
from pydoctor.astutils import node2dottedname, bind_args

def decode_with_backslashreplace(s: bytes) -> str:
    r"""
    Convert the given 8-bit string into unicode, treating any
    character c such that ord(c)<128 as an ascii character, and
    converting any c such that ord(c)>128 into a backslashed escape
    sequence.
        >>> decode_with_backslashreplace(b'abc\xff\xe8')
        'abc\\xff\\xe8'
    """
    # s.encode('string-escape') is not appropriate here, since it
    # also adds backslashes to some ascii chars (eg \ and ').

    return (s
            .decode('latin1')
            .encode('ascii', 'backslashreplace')
            .decode('ascii'))

@attr.s(auto_attribs=True)
class _MarkedColorizerState:
    length: int
    charpos: int
    lineno: int
    linebreakok: bool

class _ColorizerState:
    """
    An object uesd to keep track of the current state of the pyval
    colorizer.  The L{mark()}/L{restore()} methods can be used to set
    a backup point, and restore back to that backup point.  This is
    used by several colorization methods that first try colorizing
    their object on a single line (setting linebreakok=False); and
    then fall back on a multi-line output if that fails.  
    """
    def __init__(self) -> None:
        self.result: List[nodes.Node] = []
        self.charpos = 0
        self.lineno = 1
        self.linebreakok = True
        self.warnings: List[str] = []

    def mark(self) -> _MarkedColorizerState:
        return _MarkedColorizerState(
                    length=len(self.result), 
                    charpos=self.charpos,
                    lineno=self.lineno, 
                    linebreakok=self.linebreakok)

    def restore(self, mark: _MarkedColorizerState) -> List[nodes.Node]:
        """
        Return what's been trimmed from the result.
        """
        (self.charpos, self.lineno, 
        self.linebreakok) = (mark.charpos, mark.lineno, 
                                        mark.linebreakok)
        trimmed = self.result[mark.length:]
        del self.result[mark.length:]
        return trimmed

class _Parentage(ast.NodeTransformer):
    """
    Add C{parent} attribute to ast nodes instances.
    """
    # stolen from https://stackoverflow.com/a/68845448
    parent: Optional[ast.AST] = None

    def visit(self, node: ast.AST) -> ast.AST:
        setattr(node, 'parent', self.parent)
        self.parent = node
        node = super().visit(node)
        if isinstance(node, ast.AST):
            self.parent = getattr(node, 'parent')
        return node

# TODO: add support for comparators when needed. 
class _OperatorDelimiter:
    """
    A context manager that can add enclosing delimiters to nested operators when needed. 
    
    Adapted from C{astor} library, thanks.
    """

    def __init__(self, colorizer: 'PyvalColorizer', state: _ColorizerState, 
                 node: Union[ast.UnaryOp, ast.BinOp, ast.BoolOp]) -> None:

        self.discard = True
        """No parenthesis by default."""

        self.colorizer = colorizer
        self.state = state
        self.marked = state.mark()

        # We use a hack to populate a "parent" attribute on AST nodes.
        # See _Parentage class, applied in PyvalColorizer._colorize_ast()
        parent_node: Optional[ast.AST] = getattr(node, 'parent', None)

        if isinstance(parent_node, (ast.UnaryOp, ast.BinOp, ast.BoolOp)):
            precedence = astor.op_util.get_op_precedence(node.op)
            parent_precedence = astor.op_util.get_op_precedence(parent_node.op)
            # Add parenthesis when precedences are equal to avoid confusions 
            # and correctly handle the Pow special case without too much annoyance.
            if precedence <= parent_precedence:
                self.discard = False

    def __enter__(self) -> '_OperatorDelimiter':
        return self

    def __exit__(self, *exc_info: Any) -> None:
        if not self.discard:
            trimmed = self.state.restore(self.marked)
            self.colorizer._output('(', self.colorizer.GROUP_TAG, self.state)
            self.state.result.extend(trimmed)
            self.colorizer._output(')', self.colorizer.GROUP_TAG, self.state)

class _Maxlines(Exception):
    """A control-flow exception that is raised when PyvalColorizer
    exeeds the maximum number of allowed lines."""

class _Linebreak(Exception):
    """A control-flow exception that is raised when PyvalColorizer
    generates a string containing a newline, but the state object's
    linebreakok variable is False."""

class ColorizedPyvalRepr(ParsedRstDocstring):
    """
    @ivar is_complete: True if this colorized repr completely describes
       the object.
    """
    def __init__(self, document: nodes.document, is_complete: bool, warnings: List[str]) -> None:
        super().__init__(document, ())
        self.is_complete = is_complete
        self.warnings = warnings
        """
        List of warnings
        """
    
    def to_stan(self, docstring_linker: DocstringLinker, compact:bool=False) -> Tag:
        return Tag('code')(super().to_stan(docstring_linker))

def colorize_pyval(pyval: Any, linelen:Optional[int], maxlines:int, linebreakok:bool=True) -> ColorizedPyvalRepr:
    """
    @return: A L{ColorizedPyvalRepr} describing the given pyval.
    """
    return PyvalColorizer(linelen=linelen, maxlines=maxlines, linebreakok=linebreakok).colorize(pyval)

def colorize_inline_pyval(pyval: Any) -> ColorizedPyvalRepr:
    """
    Used to colorize type annotations and parameters default values.
    @returns: C{L{colorize_pyval}(pyval, linelen=None, linebreakok=False)}
    """
    return colorize_pyval(pyval, linelen=None, maxlines=1, linebreakok=False)

def _get_str_func(pyval:  AnyStr) -> Callable[[str], AnyStr]:
    func = cast(Callable[[str], AnyStr], str if isinstance(pyval, str) else \
        functools.partial(bytes, encoding='utf-8', errors='replace'))
    return func
def _str_escape(s: str) -> str:
    """
    Encode a string such that it's correctly represented inside simple quotes.
    """
    # displays unicode caracters as is.
    def enc(c: str) -> str:
        if c == "'":
            c = r"\'"
        elif c == '\t': 
            c = r'\t'
        elif c == '\r': 
            c = r'\r'
        elif c == '\n': 
            c = r'\n'
        elif c == '\f': 
            c = r'\f'
        elif c == '\v': 
            c = r'\v'
        elif c == "\\": 
            c = r'\\'
        return c

    # Escape it
    s = ''.join(map(enc, s))

    # Ensures there is no funcky caracters (like surrogate unicode strings)
    try:
        s.encode('utf-8')
    except UnicodeEncodeError:
        # Otherwise replace them with backslashreplace
        s = s.encode('utf-8', 'backslashreplace').decode('utf-8')
    
    return s

def _bytes_escape(b: bytes) -> str:
    return repr(b)[2:-1]

class PyvalColorizer:
    """
    Syntax highlighter for Python values.
    """

    def __init__(self, linelen:Optional[int], maxlines:int, linebreakok:bool=True):
        self.linelen: Optional[int] = linelen if linelen!=0 else None
        self.maxlines: Union[int, float] = maxlines if maxlines!=0 else float('inf')
        self.linebreakok = linebreakok

    #////////////////////////////////////////////////////////////
    # Colorization Tags & other constants
    #////////////////////////////////////////////////////////////

    GROUP_TAG = None # was 'variable-group'     # e.g., "[" and "]"
    COMMA_TAG = None # was 'variable-op'        # The "," that separates elements
    COLON_TAG = None # was 'variable-op'        # The ":" in dictionaries
    CONST_TAG = None                 # None, True, False
    NUMBER_TAG = None                # ints, floats, etc
    QUOTE_TAG = 'variable-quote'     # Quotes around strings.
    STRING_TAG = 'variable-string'   # Body of string literals
    LINK_TAG = 'variable-link'       # Links to other documentables, extracted from AST names and attributes.
    ELLIPSIS_TAG = 'variable-ellipsis'
    LINEWRAP_TAG = 'variable-linewrap'
    UNKNOWN_TAG = 'variable-unknown'

    RE_CHAR_TAG = None
    RE_GROUP_TAG = 're-group'
    RE_REF_TAG = 're-ref'
    RE_OP_TAG = 're-op'
    RE_FLAGS_TAG = 're-flags'

    ELLIPSIS = nodes.inline('...', '...', classes=[ELLIPSIS_TAG])
    LINEWRAP = nodes.inline('', chr(8629), classes=[LINEWRAP_TAG])
    UNKNOWN_REPR = nodes.inline('??', '??', classes=[UNKNOWN_TAG])
    WORD_BREAK_OPPORTUNITY = wbr()
    NEWLINE = nodes.Text('\n')

    GENERIC_OBJECT_RE = re.compile(r'^<(?P<descr>.*) at (?P<addr>0x[0-9a-f]+)>$', re.IGNORECASE)

    RE_COMPILE_SIGNATURE = signature(re.compile)

    def colorize(self, pyval: Any) -> ColorizedPyvalRepr:
        """
        Entry Point.
        """
        # Create an object to keep track of the colorization.
        state = _ColorizerState()
        state.linebreakok = self.linebreakok
        # Colorize the value.  If we reach maxlines, then add on an
        # ellipsis marker and call it a day.
        try:
            self._colorize(pyval, state)
        except (_Maxlines, _Linebreak):
            if self.linebreakok:
                state.result.append(self.NEWLINE)
                state.result.append(self.ELLIPSIS)
            else:
                if state.result[-1] is self.LINEWRAP:
                    state.result.pop()
                self._trim_result(state.result, 3)
                state.result.append(self.ELLIPSIS)
            is_complete = False
        else:
            is_complete = True
        
        # Put it all together.
        document = utils.new_document('pyval_repr')
        # This ensure the .parent and .document attributes of the child nodes are set correcly.
        set_node_attributes(document, children=[set_node_attributes(node, document=document) for node in state.result])
        return ColorizedPyvalRepr(document, is_complete, state.warnings)
    
    def _colorize(self, pyval: Any, state: _ColorizerState) -> None:

        pyvaltype = type(pyval)
        
        # Individual "is" checks are required here to be sure we don't consider 0 as True and 1 as False!
        if pyval is False or pyval is True or pyval is None or pyval is NotImplemented:
            # Link built-in constants to the standard library.
            # Ellipsis is not included here, both because its code syntax is
            # different from its constant's name and because its documentation
            # is not relevant to annotations.
            self._output(str(pyval), self.CONST_TAG, state, link=True)
        elif pyvaltype is int or pyvaltype is float or pyvaltype is complex:
            self._output(str(pyval), self.NUMBER_TAG, state)
        elif pyvaltype is str:
            self._colorize_str(pyval, state, '', escape_fcn=_str_escape)
        elif pyvaltype is bytes:
            self._colorize_str(pyval, state, b'b', escape_fcn=_bytes_escape)
        elif pyvaltype is tuple:
            # tuples need an ending comma when they contains only one value.
            self._multiline(self._colorize_iter, pyval, state, prefix='(', 
                            suffix=(',' if len(pyval) <= 1 else '')+')')
        elif pyvaltype is set:
            self._multiline(self._colorize_iter, pyval,
                            state, prefix='set([', suffix='])')
        elif pyvaltype is frozenset:
            self._multiline(self._colorize_iter, pyval,
                            state, prefix='frozenset([', suffix='])')
        elif pyvaltype is dict:
            self._multiline(self._colorize_dict,
                            list(pyval.items()),
                            state, prefix='{', suffix='}')
        elif pyvaltype is list:
            self._multiline(self._colorize_iter, pyval, state, prefix='[', suffix=']')
        elif issubclass(pyvaltype, ast.AST):
            self._colorize_ast(pyval, state)
        else:
            # Unknow live object
            try:
                pyval_repr = repr(pyval)
                if not isinstance(pyval_repr, str):
                    pyval_repr = str(pyval_repr) #type: ignore[unreachable]
            except Exception:
                state.warnings.append(f"Cannot colorize object of type '{pyval.__class__.__name__}', repr() raised an exception.")
                state.result.append(self.UNKNOWN_REPR)
            else:
                match = self.GENERIC_OBJECT_RE.search(pyval_repr)
                if match:
                    self._output(f"<{match.groupdict().get('descr')}>", None, state)
                else:
                    self._output(pyval_repr, None, state)

    def _trim_result(self, result: List[nodes.Node], num_chars: int) -> None:
        while num_chars > 0:
            if not result: 
                return
            if isinstance(result[-1], nodes.Element):
                if len(result[-1].children) >= 1:
                    data = result[-1][-1].astext()
                    trim = min(num_chars, len(data))
                    result[-1][-1] = nodes.Text(data[:-trim])
                    if not result[-1][-1].astext(): 
                        if len(result[-1].children) == 1:
                            result.pop()
                        else:
                            result[-1].pop()
                else:
                    trim = 0
                    result.pop()
                num_chars -= trim
            else:
                # Must be Text if it's not an Element
                trim = min(num_chars, len(result[-1]))
                result[-1] = nodes.Text(result[-1].astext()[:-trim])
                if not result[-1].astext(): 
                    result.pop()
                num_chars -= trim

    #////////////////////////////////////////////////////////////
    # Object Colorization Functions
    #////////////////////////////////////////////////////////////

    def _insert_comma(self, indent: int, state: _ColorizerState) -> None:
        if state.linebreakok:
            self._output(',', self.COMMA_TAG, state)
            self._output('\n'+' '*indent, None, state)
        else:
            self._output(', ', self.COMMA_TAG, state)

    def _multiline(self, func: Callable[..., None], pyval: Iterable[Any], state: _ColorizerState, **kwargs: Any) -> None:
        """
        Helper for container-type colorizers.  First, try calling
        C{func(pyval, state, **kwargs)} with linebreakok set to false;
        and if that fails, then try again with it set to true.
        """
        linebreakok = state.linebreakok
        mark = state.mark()

        try:
            state.linebreakok = False
            func(pyval, state, **kwargs)
            state.linebreakok = linebreakok

        except _Linebreak:
            if not linebreakok:
                raise
            state.restore(mark)
            func(pyval, state, **kwargs)

    def _colorize_iter(self, pyval: Iterable[Any], state: _ColorizerState, 
                       prefix: Optional[AnyStr] = None, 
                       suffix: Optional[AnyStr] = None) -> None:
        if prefix is not None:
            self._output(prefix, self.GROUP_TAG, state)
        indent = state.charpos
        for i, elt in enumerate(pyval):
            if i>=1:
                self._insert_comma(indent, state)
            # word break opportunity for inline values
            state.result.append(self.WORD_BREAK_OPPORTUNITY)
            self._colorize(elt, state)
        if suffix is not None:
            self._output(suffix, self.GROUP_TAG, state)

    def _colorize_dict(self, items: Iterable[Tuple[Any, Any]], state: _ColorizerState, prefix: str, suffix: str) -> None:
        self._output(prefix, self.GROUP_TAG, state)
        indent = state.charpos
        for i, (key, val) in enumerate(items):
            if i>=1:
                self._insert_comma(indent, state)
            state.result.append(self.WORD_BREAK_OPPORTUNITY)
            self._colorize(key, state)
            self._output(': ', self.COLON_TAG, state)
            self._colorize(val, state)
        self._output(suffix, self.GROUP_TAG, state)
    
    def _colorize_str(self, pyval: AnyStr, state: _ColorizerState, prefix: AnyStr, 
                      escape_fcn: Callable[[AnyStr], str]) -> None:
        
        str_func = _get_str_func(pyval)

        #  Decide which quote to use.
        if str_func('\n') in pyval and state.linebreakok:
            quote = str_func("'''")
        else: 
            quote = str_func("'")
        
        # Open quote.
        self._output(prefix, None, state)
        self._output(quote, self.QUOTE_TAG, state)

        # Divide the string into lines.
        if state.linebreakok:
            lines = pyval.split(str_func('\n'))
        else:
            lines = [pyval]
        # Body
        for i, line in enumerate(lines):
            if i>0:
                self._output(str_func('\n'), None, state)

            # It's not redundant when line is bytes
            line = cast(AnyStr, escape_fcn(line)) # type:ignore[redundant-cast]
            
            self._output(line, self.STRING_TAG, state)
        # Close quote.
        self._output(quote, self.QUOTE_TAG, state)

    #////////////////////////////////////////////////////////////
    # Support for AST
    #////////////////////////////////////////////////////////////

    # Nodes not explicitely handled that would be nice to handle.
    #   f-strings, 
    #   comparators, 
    #   generator expressions, 
    #   Slice and ExtSlice

    @staticmethod
    def _is_ast_constant(node: ast.AST) -> bool:
        return isinstance(node, (ast.Num, ast.Str, ast.Bytes, 
                                 ast.Constant, ast.NameConstant, ast.Ellipsis))
    @staticmethod
    def _get_ast_constant_val(node: ast.AST) -> Any:
        # Deprecated since version 3.8: Replaced by Constant
        if isinstance(node, ast.Num): 
            return(node.n)
        if isinstance(node, (ast.Str, ast.Bytes)):
           return(node.s)
        if isinstance(node, (ast.Constant, ast.NameConstant)):
            return(node.value)
        if isinstance(node, ast.Ellipsis):
            return(...)
        
    def _colorize_ast_constant(self, pyval: ast.AST, state: _ColorizerState) -> None:
        val = self._get_ast_constant_val(pyval)
        # Handle elipsis
        if val != ...:
            self._colorize(val, state)
        else:
            self._output('...', self.ELLIPSIS_TAG, state)

    def _colorize_ast(self, pyval: ast.AST, state: _ColorizerState) -> None:
        # Set nodes parent in order to check theirs precedences and add delimiters when needed.
        if not getattr(pyval, 'parent', None):
            _Parentage().visit(pyval)

        if self._is_ast_constant(pyval): 
            self._colorize_ast_constant(pyval, state)
        elif isinstance(pyval, ast.UnaryOp):
            self._colorize_ast_unary_op(pyval, state)
        elif isinstance(pyval, ast.BinOp):
            self._colorize_ast_binary_op(pyval, state)
        elif isinstance(pyval, ast.BoolOp):
            self._colorize_ast_bool_op(pyval, state)
        elif isinstance(pyval, ast.List):
            self._multiline(self._colorize_iter, pyval.elts, state, prefix='[', suffix=']')
        elif isinstance(pyval, ast.Tuple):
            self._multiline(self._colorize_iter, pyval.elts, state, prefix='(', suffix=')')
        elif isinstance(pyval, ast.Set):
            self._multiline(self._colorize_iter, pyval.elts, state, prefix='set([', suffix='])')
        elif isinstance(pyval, ast.Dict):
            items = list(zip(pyval.keys, pyval.values))
            self._multiline(self._colorize_dict, items, state, prefix='{', suffix='}')
        elif isinstance(pyval, ast.Name):
            self._colorize_ast_name(pyval, state)
        elif isinstance(pyval, ast.Attribute):
            self._colorize_ast_attribute(pyval, state)
        elif isinstance(pyval, ast.Subscript):
            self._colorize_ast_subscript(pyval, state)
        elif isinstance(pyval, ast.Call):
            self._colorize_ast_call(pyval, state)
        elif isinstance(pyval, ast.Starred):
            self._output('*', None, state)
            self._colorize_ast(pyval.value, state)
        elif isinstance(pyval, ast.keyword):
            if pyval.arg is not None:
                self._output(pyval.arg, None, state)
                self._output('=', None, state)
            else:
                self._output('**', None, state)
            self._colorize_ast(pyval.value, state)
        else:
            self._colorize_ast_generic(pyval, state)
    
    def _colorize_ast_unary_op(self, pyval: ast.UnaryOp, state: _ColorizerState) -> None:
        with _OperatorDelimiter(self, state, pyval):
            if isinstance(pyval.op, ast.USub):
                self._output('-', None, state)
            elif isinstance(pyval.op, ast.UAdd):
                self._output('+', None, state)
            elif isinstance(pyval.op, ast.Not):
                self._output('not ', None, state)
            elif isinstance(pyval.op, ast.Invert):
                self._output('~', None, state)
            else:
                state.warnings.append(f"Unknow unrary operator: {pyval}")
                self._colorize_ast_generic(pyval, state)

            self._colorize(pyval.operand, state)
    
    def _colorize_ast_binary_op(self, pyval: ast.BinOp, state: _ColorizerState) -> None:
        with _OperatorDelimiter(self, state, pyval):
            # Colorize first operand
            self._colorize(pyval.left, state)

            # Colorize operator
            if isinstance(pyval.op, ast.Sub):
                self._output('-', None, state)
            elif isinstance(pyval.op, ast.Add):
                self._output('+', None, state)
            elif isinstance(pyval.op, ast.Mult):
                self._output('*', None, state)
            elif isinstance(pyval.op, ast.Div):
                self._output('/', None, state)
            elif isinstance(pyval.op, ast.FloorDiv):
                self._output('//', None, state)
            elif isinstance(pyval.op, ast.Mod):
                self._output('%', None, state)
            elif isinstance(pyval.op, ast.Pow):
                self._output('**', None, state)
            elif isinstance(pyval.op, ast.LShift):
                self._output('<<', None, state)
            elif isinstance(pyval.op, ast.RShift):
                self._output('>>', None, state)
            elif isinstance(pyval.op, ast.BitOr):
                self._output('|', None, state)
            elif isinstance(pyval.op, ast.BitXor):
                self._output('^', None, state)
            elif isinstance(pyval.op, ast.BitAnd):
                self._output('&', None, state)
            elif isinstance(pyval.op, ast.MatMult):
                self._output('@', None, state)
            else:
                state.warnings.append(f"Unknow binary operator: {pyval}")
                self._colorize_ast_generic(pyval, state)

            # Colorize second operand
            self._colorize(pyval.right, state)
    
    def _colorize_ast_bool_op(self, pyval: ast.BoolOp, state: _ColorizerState) -> None:
        with _OperatorDelimiter(self, state, pyval):
            _maxindex = len(pyval.values)-1

            for index, value in enumerate(pyval.values):
                self._colorize(value, state)

                if index != _maxindex:
                    if isinstance(pyval.op, ast.And):
                        self._output(' and ', None, state)
                    elif isinstance(pyval.op, ast.Or):
                        self._output(' or ', None, state)

    def _colorize_ast_name(self, pyval: ast.Name, state: _ColorizerState) -> None:
        self._output(pyval.id, self.LINK_TAG, state, link=True)

    def _colorize_ast_attribute(self, pyval: ast.Attribute, state: _ColorizerState) -> None:
        parts = []
        curr: ast.expr = pyval
        while isinstance(curr, ast.Attribute):
            parts.append(curr.attr)
            curr = curr.value
        if not isinstance(curr, ast.Name):
            self._colorize_ast_generic(pyval, state)
            return
        parts.append(curr.id)
        parts.reverse()
        self._output('.'.join(parts), self.LINK_TAG, state, link=True)

    def _colorize_ast_subscript(self, node: ast.Subscript, state: _ColorizerState) -> None:

        self._colorize(node.value, state)

        sub: ast.AST = node.slice
        if sys.version_info < (3,9) and isinstance(sub, ast.Index):
            # In Python < 3.9, non-slices are always wrapped in an Index node.
            sub = sub.value
        self._output('[', self.GROUP_TAG, state)
        if isinstance(sub, ast.Tuple):
            self._multiline(self._colorize_iter, sub.elts, state)
        else:
            state.result.append(self.WORD_BREAK_OPPORTUNITY)
            self._colorize(sub, state)
       
        self._output(']', self.GROUP_TAG, state)
    
    def _colorize_ast_call(self, node: ast.Call, state: _ColorizerState) -> None:
        
        if node2dottedname(node.func) == ['re', 'compile']:
            # Colorize regexps from re.compile AST arguments.
            self._colorize_ast_re(node, state)
        else:
            # Colorize other forms of callables.
            self._colorize_ast_call_generic(node, state)

    def _colorize_ast_call_generic(self, node: ast.Call, state: _ColorizerState) -> None:
        self._colorize(node.func, state)
        self._output('(', self.GROUP_TAG, state)
        indent = state.charpos
        self._multiline(self._colorize_iter, node.args, state)
        if len(node.keywords)>0:
            if len(node.args)>0:
                self._insert_comma(indent, state)
            self._multiline(self._colorize_iter, node.keywords, state)
        self._output(')', self.GROUP_TAG, state)

    def _colorize_ast_re(self, node:ast.Call, state: _ColorizerState) -> None:
        
        try:
            # Can raise TypeError
            args = bind_args(self.RE_COMPILE_SIGNATURE, node)
        except TypeError:
            self._colorize_ast_call_generic(node, state)
            return
        
        ast_pattern = args.arguments['pattern']

        # Cannot colorize regex
        if not self._is_ast_constant(ast_pattern):
            self._colorize_ast_call_generic(node, state)
            return

        pat = self._get_ast_constant_val(ast_pattern)
        
        # Just in case regex pattern is not valid type
        if not isinstance(pat, (bytes, str)):
            state.warnings.append("Cannot colorize regular expression: pattern must be bytes or str.")
            self._colorize_ast_call_generic(node, state)
            return

        mark = state.mark()
        
        self._output("re.compile", None, state, link=True)
        self._output('(', self.GROUP_TAG, state)
        indent = state.charpos
        
        try:
            # Can raise ValueError or re.error
            # Value of type variable "AnyStr" cannot be "Union[bytes, str]": Yes it can.
            self._colorize_re_pattern_str(pat, state) #type:ignore[type-var]
        except (ValueError, sre_constants.error) as e:
            # Make sure not to swallow control flow errors.
            # Colorize the ast.Call as any other node if the pattern parsing fails.
            state.restore(mark)
            state.warnings.append(f"Cannot colorize regular expression, error: {str(e)}")
            self._colorize_ast_call_generic(node, state)
            return

        ast_flags = args.arguments.get('flags')
        if ast_flags is not None:
            self._insert_comma(indent, state)
            self._colorize_ast(ast_flags, state)

        self._output(')', self.GROUP_TAG, state)

    def _colorize_ast_generic(self, pyval: ast.AST, state: _ColorizerState) -> None:
        try:
            source = astor.to_source(pyval).strip()
        except Exception: #  No defined handler for node of type <type>
            state.result.append(self.UNKNOWN_REPR)
        else:
            # TODO: Maybe try to colorize anyway, without links, with epydoc.doctest ?
            self._output(source, None, state)
        
    #////////////////////////////////////////////////////////////
    # Support for Regexes
    #////////////////////////////////////////////////////////////

    def _colorize_re_pattern_str(self, pat: AnyStr, state: _ColorizerState) -> None:
        # Currently, the colorizer do not render multiline regex patterns correctly because we don't
        # recover the flag values from re.compile() arguments (so we don't know when re.VERBOSE is used for instance). 
        # With default flags, newlines are mixed up with literals \n and probably more fun stuff like that.
        # Turns out the sre_parse.parse() function treats caracters "\n" and "\\n" the same way.
        
        # If the pattern string is composed by mutiple lines, simply use the string colorizer instead.
        # It's more informative to have the proper newlines than the fancy regex colors. 

        # Note: Maybe this decision is driven by a misunderstanding of regular expression.

        str_func = _get_str_func(pat)
        if str_func('\n') in pat:
            if isinstance(pat, bytes):
                self._colorize_str(pat, state, b'b', escape_fcn=_bytes_escape)
            else:
                self._colorize_str(pat, state, '', escape_fcn=_str_escape)
        else:
            if isinstance(pat, bytes):
                self._colorize_re_pattern(pat, state, b'rb')
            else:
                self._colorize_re_pattern(pat, state, 'r')
    
    def _colorize_re_pattern(self, pat: AnyStr, state: _ColorizerState, prefix: AnyStr) -> None:

        # Parse the regexp pattern.
        # The regex pattern strings are always parsed with the default flags.
        # Flag values are displayed as regular ast.Call arguments. 

        tree: sre_parse36.SubPattern = sre_parse36.parse(pat, 0)
        # from python 3.8 SubPattern.pattern is named SubPattern.state, but we don't care right now because we use sre_parse36
        pattern = tree.pattern
        groups = dict([(num,name) for (name,num) in
                       pattern.groupdict.items()])
        flags: int = pattern.flags
        
        # Open quote. Never triple quote regex patterns string, anyway parterns that includes an '\n' caracter are displayed as regular strings.
        quote = "'"
        self._output(prefix, None, state)
        self._output(quote, self.QUOTE_TAG, state)
        
        if flags != sre_constants.SRE_FLAG_UNICODE:
            # If developers included flags in the regex string, display them.
            # By default, do not display the '(?u)'
            self._colorize_re_flags(flags, state)
        
        # Colorize it!
        self._colorize_re_tree(tree.data, state, True, groups)

        # Close quote.
        self._output(quote, self.QUOTE_TAG, state)

    def _colorize_re_flags(self, flags: int, state: _ColorizerState) -> None:
        if flags:
            flags_list = [c for (c,n) in sorted(sre_parse36.FLAGS.items())
                        if (n&flags)]
            flags_str = '(?%s)' % ''.join(flags_list)
            self._output(flags_str, self.RE_FLAGS_TAG, state)

    def _colorize_re_tree(self, tree: Sequence[Tuple[sre_constants._NamedIntConstant, Any]],
                          state: _ColorizerState, noparen: bool, groups: Dict[int, str]) -> None:

        if len(tree) > 1 and not noparen:
            self._output('(', self.RE_GROUP_TAG, state)

        for elt in tree:
            op = elt[0]
            args = elt[1]

            if op == sre_constants.LITERAL: #type:ignore[attr-defined]
                c = chr(cast(int, args))
                # Add any appropriate escaping.
                if c in '.^$\\*+?{}[]|()\'': 
                    c = '\\' + c
                elif c == '\t': 
                    c = r'\t'
                elif c == '\r': 
                    c = r'\r'
                elif c == '\n': 
                    c = r'\n'
                elif c == '\f': 
                    c = r'\f'
                elif c == '\v': 
                    c = r'\v'
                # Keep unicode chars as is, so do nothing if ord(c) > 65535
                elif ord(c) > 255 and ord(c) <= 65535: 
                   c = rb'\u%04x' % ord(c) # type:ignore[assignment]
                elif (ord(c)<32 or ord(c)>=127) and ord(c) <= 65535: 
                    c = rb'\x%02x' % ord(c) # type:ignore[assignment]
                self._output(c, self.RE_CHAR_TAG, state)

            elif op == sre_constants.ANY: #type:ignore[attr-defined]
                self._output('.', self.RE_CHAR_TAG, state)

            elif op == sre_constants.BRANCH: #type:ignore[attr-defined]
                if args[0] is not None:
                    raise ValueError('Branch expected None arg but got %s'
                                     % args[0])
                for i, item in enumerate(args[1]):
                    if i > 0:
                        self._output('|', self.RE_OP_TAG, state)
                    self._colorize_re_tree(item, state, True, groups)

            elif op == sre_constants.IN: #type:ignore[attr-defined]
                if (len(args) == 1 and args[0][0] == sre_constants.CATEGORY): #type:ignore[attr-defined]
                    self._colorize_re_tree(args, state, False, groups)
                else:
                    self._output('[', self.RE_GROUP_TAG, state)
                    self._colorize_re_tree(args, state, True, groups)
                    self._output(']', self.RE_GROUP_TAG, state)

            elif op == sre_constants.CATEGORY: #type:ignore[attr-defined]
                if args == sre_constants.CATEGORY_DIGIT: val = r'\d' #type:ignore[attr-defined]
                elif args == sre_constants.CATEGORY_NOT_DIGIT: val = r'\D' #type:ignore[attr-defined]
                elif args == sre_constants.CATEGORY_SPACE: val = r'\s' #type:ignore[attr-defined]
                elif args == sre_constants.CATEGORY_NOT_SPACE: val = r'\S' #type:ignore[attr-defined]
                elif args == sre_constants.CATEGORY_WORD: val = r'\w' #type:ignore[attr-defined]
                elif args == sre_constants.CATEGORY_NOT_WORD: val = r'\W' #type:ignore[attr-defined]
                else: raise ValueError('Unknown category %s' % args)
                self._output(val, self.RE_CHAR_TAG, state)

            elif op == sre_constants.AT: #type:ignore[attr-defined]
                if args == sre_constants.AT_BEGINNING_STRING: val = r'\A' #type:ignore[attr-defined]
                elif args == sre_constants.AT_BEGINNING: val = '^' #type:ignore[attr-defined]
                elif args == sre_constants.AT_END: val = '$' #type:ignore[attr-defined]
                elif args == sre_constants.AT_BOUNDARY: val = r'\b' #type:ignore[attr-defined]
                elif args == sre_constants.AT_NON_BOUNDARY: val = r'\B' #type:ignore[attr-defined]
                elif args == sre_constants.AT_END_STRING: val = r'\Z' #type:ignore[attr-defined]
                else: raise ValueError('Unknown position %s' % args)
                self._output(val, self.RE_CHAR_TAG, state)

            elif op in (sre_constants.MAX_REPEAT, sre_constants.MIN_REPEAT): #type:ignore[attr-defined]
                minrpt = args[0]
                maxrpt = args[1]
                if maxrpt == sre_constants.MAXREPEAT:
                    if minrpt == 0:   val = '*'
                    elif minrpt == 1: val = '+'
                    else: val = '{%d,}' % (minrpt)
                elif minrpt == 0:
                    if maxrpt == 1: val = '?'
                    else: val = '{,%d}' % (maxrpt)
                elif minrpt == maxrpt:
                    val = '{%d}' % (maxrpt)
                else:
                    val = '{%d,%d}' % (minrpt, maxrpt)
                if op == sre_constants.MIN_REPEAT: #type:ignore[attr-defined]
                    val += '?'

                self._colorize_re_tree(args[2], state, False, groups)
                self._output(val, self.RE_OP_TAG, state)

            elif op == sre_constants.SUBPATTERN: #type:ignore[attr-defined]
                if args[0] is None:
                    self._output(r'(?:', self.RE_GROUP_TAG, state)
                elif args[0] in groups:
                    self._output(r'(?P<', self.RE_GROUP_TAG, state)
                    self._output(groups[args[0]], self.RE_REF_TAG, state)
                    self._output('>', self.RE_GROUP_TAG, state)
                elif isinstance(args[0], int):
                    # This is cheating:
                    self._output('(', self.RE_GROUP_TAG, state)
                else:
                    self._output('(?P<', self.RE_GROUP_TAG, state)
                    self._output(args[0], self.RE_REF_TAG, state)
                    self._output('>', self.RE_GROUP_TAG, state)
                self._colorize_re_tree(args[3], state, True, groups)
                self._output(')', self.RE_GROUP_TAG, state)

            elif op == sre_constants.GROUPREF: #type:ignore[attr-defined]
                self._output('\\%d' % args, self.RE_REF_TAG, state)

            elif op == sre_constants.RANGE: #type:ignore[attr-defined]
                self._colorize_re_tree( ((sre_constants.LITERAL, args[0]),), #type:ignore[attr-defined]
                                        state, False, groups )
                self._output('-', self.RE_OP_TAG, state)
                self._colorize_re_tree( ((sre_constants.LITERAL, args[1]),), #type:ignore[attr-defined]
                                        state, False, groups )

            elif op == sre_constants.NEGATE: #type:ignore[attr-defined]
                self._output('^', self.RE_OP_TAG, state)

            elif op == sre_constants.ASSERT: #type:ignore[attr-defined]
                if args[0] > 0:
                    self._output('(?=', self.RE_GROUP_TAG, state)
                else:
                    self._output('(?<=', self.RE_GROUP_TAG, state)
                self._colorize_re_tree(args[1], state, True, groups)
                self._output(')', self.RE_GROUP_TAG, state)

            elif op == sre_constants.ASSERT_NOT: #type:ignore[attr-defined]
                if args[0] > 0:
                    self._output('(?!', self.RE_GROUP_TAG, state)
                else:
                    self._output('(?<!', self.RE_GROUP_TAG, state)
                self._colorize_re_tree(args[1], state, True, groups)
                self._output(')', self.RE_GROUP_TAG, state)

            elif op == sre_constants.NOT_LITERAL: #type:ignore[attr-defined]
                self._output('[^', self.RE_GROUP_TAG, state)
                self._colorize_re_tree( ((sre_constants.LITERAL, args),), #type:ignore[attr-defined]
                                        state, False, groups )
                self._output(']', self.RE_GROUP_TAG, state)
            else:
                raise ValueError(f"Unsupported element :{elt}")
        if len(tree) > 1 and not noparen:
            self._output(')', self.RE_GROUP_TAG, state)

    #////////////////////////////////////////////////////////////
    # Output function
    #////////////////////////////////////////////////////////////

    def _output(self, s: AnyStr, css_class: Optional[str], 
                state: _ColorizerState, link: bool = False) -> None:
        """
        Add the string C{s} to the result list, tagging its contents
        with the specified C{css_class}. Any lines that go beyond L{PyvalColorizer.linelen} will
        be line-wrapped.  If the total number of lines exceeds
        L{PyvalColorizer.maxlines}, then raise a L{_Maxlines} exception.
        """
        # Make sure the string is unicode.
        if isinstance(s, bytes):
            s = cast(AnyStr, decode_with_backslashreplace(s))
        assert isinstance(s, str)
        # Split the string into segments.  The first segment is the
        # content to add to the current line, and the remaining
        # segments are new lines.
        segments = s.split('\n')

        for i, segment in enumerate(segments):
            # If this isn't the first segment, then add a newline to
            # split it from the previous segment.
            if i > 0:
                if (state.lineno+1) > self.maxlines:
                    raise _Maxlines()
                if not state.linebreakok:
                    raise _Linebreak()
                state.result.append(self.NEWLINE)
                state.lineno += 1
                state.charpos = 0
            
            segment_len = len(segment) 

            # If the segment fits on the current line, then just call
            # markup to tag it, and store the result.
            # Don't break links into separate segments, neither quotes.
            if (self.linelen is None or 
                state.charpos + segment_len <= self.linelen 
                or link is True 
                or css_class in ('variable-quote',)):

                state.charpos += segment_len

                if link is True:
                    element = obj_reference('', segment, refuid=segment)
                elif css_class is not None:
                    element = nodes.inline('', segment, classes=[css_class])
                else:
                    element = nodes.Text(segment)

                state.result.append(element)

            # If the segment doesn't fit on the current line, then
            # line-wrap it, and insert the remainder of the line into
            # the segments list that we're iterating over.  (We'll go
            # the beginning of the next line at the start of the
            # next iteration through the loop.)
            else:
                assert isinstance(self.linelen, int)
                split = self.linelen-state.charpos
                segments.insert(i+1, segment[split:])
                segment = segment[:split]

                if css_class is not None:
                    element = nodes.inline('', segment, classes=[css_class])
                else:
                    element = nodes.Text(segment)
                state.result += [element, self.LINEWRAP]
	
