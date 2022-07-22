"""
Convert L{pydoctor.epydoc} parsed markup into renderable content.
"""

from collections import defaultdict
from typing import (
    TYPE_CHECKING, Any, Callable, ClassVar, DefaultDict, Dict, Generator, 
    Iterator, List, Mapping, Optional, Sequence, Tuple, 
)
import ast
import re

import attr

from pydoctor import model, linker
from pydoctor.epydoc.markup import Field as EpydocField, ParseError, get_parser_by_name
from twisted.web.template import Tag, tags
from pydoctor.epydoc.markup import ParsedDocstring
import pydoctor.epydoc.markup.plaintext
from pydoctor.epydoc.markup._pyval_repr import colorize_pyval, colorize_inline_pyval

if TYPE_CHECKING:
    from twisted.web.template import Flattenable

taglink = linker.taglink
"""
Alias to L{pydoctor.linker.taglink()}.
"""

def get_parser(obj: model.Documentable) -> Callable[[str, List[ParseError], bool], ParsedDocstring]:
    """
    Get the C{parse_docstring(str, List[ParseError], bool) -> ParsedDocstring} function. 
    """    
    # Use module's __docformat__ if specified, else use system's. 
    # Except if system's docformat is plaintext, in this case, use plaintext.
    # See https://github.com/twisted/pydoctor/issues/503 for the reason
    # of this behavior. 
    if obj.system.options.docformat == 'plaintext':
        return pydoctor.epydoc.markup.plaintext.parse_docstring
    # the docstring should be parsed using the format of the module it was inherited from
    docformat = obj.module.docformat or obj.system.options.docformat
    
    try:
        return get_parser_by_name(docformat, obj)
    except ImportError as e:
        msg = 'Error trying to import %r parser:\n\n    %s: %s\n\nUsing plain text formatting only.'%(
            docformat, e.__class__.__name__, e)
        obj.system.msg('epydoc2stan', msg, thresh=-1, once=True)
        return pydoctor.epydoc.markup.plaintext.parse_docstring


def get_docstring(
        obj: model.Documentable
        ) -> Tuple[Optional[str], Optional[model.Documentable]]:
    for source in obj.docsources():
        doc = source.docstring
        if doc:
            return doc, source
        if doc is not None:
            # Treat empty docstring as undocumented.
            return None, source
    return None, None

@attr.s(auto_attribs=True)
class FieldDesc:
    """
    Combines informations from multiple L{Field} objects into one.

    Example::

       :param foo: description of parameter foo
       :type foo:  SomeClass

    """
    _UNDOCUMENTED: ClassVar[Tag] = tags.span(class_='undocumented')("Undocumented")

    name: Optional[str] = None
    """Field name, i.e. C{:param <name>:}"""

    type: Optional[Tag] = None
    """Formatted type"""

    body: Optional[Tag] = None

    def format(self) -> Generator[Tag, None, None]:
        """
        @return: Iterator that yields one or two C{tags.td}.
        """
        formatted = self.body or self._UNDOCUMENTED
        fieldNameTd: List[Tag] = []
        if self.name:
            # Add the stars to the params names just before generating the field stan, not before.
            if isinstance(self.name, VariableArgument):
                prefix = "*"
            elif isinstance(self.name, KeywordArgument):
                prefix = "**"
            else:
                prefix = ""

            name = tags.transparent(prefix, insert_break_points(self.name))

            stan_name = tags.span(class_="fieldArg")(name)
            if self.type:
                stan_name(":")
            fieldNameTd.append(stan_name)

        if self.type:
            fieldNameTd.append(self.type)
        if fieldNameTd:
            #  <name>: <type> | <desc>
            yield tags.td(class_="fieldArgContainer")(*fieldNameTd)
            yield tags.td(class_="fieldArgDesc")(formatted)
        else:
            #  <desc>
            yield tags.td(formatted, colspan="2")

class RaisesDesc(FieldDesc):
    """Description of an exception that can be raised by function/method."""

    def format(self) -> Generator[Tag, None, None]:
        assert self.type is not None  # TODO: Why can't it be None?
        yield tags.td(tags.code(self.type), class_="fieldArgContainer")
        yield tags.td(self.body or self._UNDOCUMENTED)

def format_desc_list(label: str, descs: Sequence[FieldDesc]) -> Iterator[Tag]:
    """
    Format list of L{FieldDesc}. Used for param, returns, raises, etc.

    Generates a 2-columns layout as follow::

        +------------------------------------+
        | <label>                            |
        | <name>: <type> |     <desc>        |
        | <name>: <type> |     <desc>        |
        +------------------------------------+

    If the fields don't have type or name information,
    generates the same output as L{format_field_list}::

        +------------------------------------+
        | <label>                            |
        | <desc ... >                        |
        +------------------------------------+

    @arg label: Section "mini heading"
    @arg descs: L{FieldDesc}s
    @returns: Each row as iterator or None if no C{descs} id provided.
    """
    if not descs:
        return
    # <label>
    row = tags.tr(class_="fieldStart")
    row(tags.td(class_="fieldName", colspan="2")(label))
    # yield the first row.
    yield row
    # yield descriptions.
    for d in descs:
        row = tags.tr()
        # <name>: <type> |     <desc>
        # or
        # <desc ... >
        row(d.format())
        yield row

@attr.s(auto_attribs=True)
class Field:
    """Like L{pydoctor.epydoc.markup.Field}, but without the gross accessor
    methods and with a formatted body.

    Example::

        @note: some other information
    """

    tag: str
    """Field tag, i.e. C{:<tag>:} """
    arg: Optional[str]
    """Field argument, i.e. C{:param <argument>:}"""
    source: model.Documentable
    lineno: int
    body: ParsedDocstring

    @classmethod
    def from_epydoc(cls, field: EpydocField, source: model.Documentable) -> 'Field':
        return cls(
            tag=field.tag(),
            arg=field.arg(),
            source=source,
            lineno=field.lineno,
            body=field.body()
            )

    def format(self) -> Tag:
        """Present this field's body as HTML."""
        return self.body.to_stan(self.source.docstring_linker)

    def report(self, message: str) -> None:
        self.source.report(message, lineno_offset=self.lineno, section='docstring')


def format_field_list(singular: str, plural: str, fields: Sequence[Field]) -> Iterator[Tag]:
    """
    Format list of L{Field} object. Used for notes, see also, authors, etc.

    Generates a 2-columns layout as follow::

        +------------------------------------+
        | <label>                            |
        | <desc ... >                        |
        +------------------------------------+

    @returns: Each row as iterator
    """
    if not fields:
        return

    label = singular if len(fields) == 1 else plural
    row = tags.tr(class_="fieldStart")
    row(tags.td(class_="fieldName", colspan="2")(label))
    yield row

    for field in fields:
        row = tags.tr()
        row(tags.td(colspan="2")(field.format()))
        yield row

class VariableArgument(str):
    """
    Encapsulate the name of C{vararg} parameters.
    """

class KeywordArgument(str):
    """
    Encapsulate the name of C{kwarg} parameters.
    """

class FieldHandler:

    def __init__(self, obj: model.Documentable):
        self.obj = obj
        self._linker = self.obj.docstring_linker

        self.types: Dict[str, Optional[Tag]] = {}

        self.parameter_descs: List[FieldDesc] = []
        self.return_desc: Optional[FieldDesc] = None
        self.yields_desc: Optional[FieldDesc] = None 
        self.raise_descs: List[RaisesDesc] = []
        self.warns_desc: List[FieldDesc] = [] 
        self.seealsos: List[Field] = []
        self.notes: List[Field] = []
        self.authors: List[Field] = []
        self.sinces: List[Field] = []
        self.unknowns: DefaultDict[str, List[FieldDesc]] = defaultdict(list)

    def set_param_types_from_annotations(
            self, annotations: Mapping[str, Optional[ast.expr]]
            ) -> None:
        formatted_annotations = {
            name: None if value is None
                       else colorize_inline_pyval(value).to_stan(self._linker)
            for name, value in annotations.items()
            }
        ret_type = formatted_annotations.pop('return', None)
        self.types.update(formatted_annotations)
        if ret_type is not None:
            # In most cases 'None' is not an actual return type, but the absence
            # of a returned value. Not storing it is the easiest way to prevent
            # it from being presented.
            ann_ret = annotations['return']
            assert ann_ret is not None  # ret_type would be None otherwise
            if not _is_none_literal(ann_ret):
                self.return_desc = FieldDesc(type=ret_type)

    @staticmethod
    def _report_unexpected_argument(field:Field) -> None:
        if field.arg is not None:
            field.report('Unexpected argument in %s field' % (field.tag,))

    def handle_return(self, field: Field) -> None:
        self._report_unexpected_argument(field)
        if not self.return_desc:
            self.return_desc = FieldDesc()
        self.return_desc.body = field.format()
    handle_returns = handle_return

    def handle_yield(self, field: Field) -> None:
        self._report_unexpected_argument(field)
        if not self.yields_desc:
            self.yields_desc = FieldDesc()
        self.yields_desc.body = field.format()
    handle_yields = handle_yield

    def handle_returntype(self, field: Field) -> None:
        self._report_unexpected_argument(field)
        if not self.return_desc:
            self.return_desc = FieldDesc()
        self.return_desc.type = field.format()
    handle_rtype = handle_returntype

    def handle_yieldtype(self, field: Field) -> None:
        self._report_unexpected_argument(field)
        if not self.yields_desc:
            self.yields_desc = FieldDesc()
        self.yields_desc.type = field.format()
    handle_ytype = handle_yieldtype

    def _handle_param_name(self, field: Field) -> Optional[str]:
        name = field.arg
        if name is None:
            field.report('Parameter name missing')
            return None
        
        name = name.lstrip('*')
        annotations = None
        if isinstance(field.source, model.Function):
            annotations = field.source.annotations
        elif isinstance(field.source, model.Class):
            # Constructor parameters can be documented on the class.
            annotations = field.source.constructor_params
        # This might look useless, but it's needed in order to keep the 
        # right str type: str, VariableArgument or KeyowrdArgument. And then add the stars accordingly.
        if annotations is not None:
            for param_name, _ in annotations.items():
                if param_name == name:
                    name = param_name
        return name

    def _handle_param_not_found(self, name: str, field: Field) -> None:
        """Figure out if the parameter might exist despite not being found
        in this documentable's code, warn if not.
        """
        source = field.source
        if source is not self.obj:
            # Docstring is inherited, so it may not represent this exact method.
            return
        if isinstance(source, model.Class):
            if None in source.baseobjects:
                # Class has a computed base class, which could define parameters
                # we can't discover.
                # For example, this class might use
                # L{twisted.python.components.proxyForInterface()}.
                return
            if name in source.constructor_params:
                # Constructor parameters can be documented on the class.
                return
        field.report('Documented parameter "%s" does not exist' % (name,))

    def handle_type(self, field: Field) -> None:
        if isinstance(self.obj, model.Attribute):
            if field.arg is not None:
                field.report('Field in variable docstring should not include a name')
            self.obj.parsed_type = field.body
            return
        elif isinstance(self.obj, model.Function):
            name = self._handle_param_name(field)
            if name is not None and name not in self.types and not any(
                    # Don't warn about keywords or about parameters we already
                    # reported a warning for.
                    desc.name == name for desc in self.parameter_descs
                    ):
                self._handle_param_not_found(name, field)
        else:
            # Note: extract_fields() will issue warnings about missing field
            #       names, so we can silently ignore them here.
            # TODO: Processing the fields once in extract_fields() and again
            #       in format_docstring() adds complexity and can cause
            #       inconsistencies.
            name = field.arg
        if name is not None:
            self.types[name] = field.format()

    def handle_param(self, field: Field) -> None:
        name = self._handle_param_name(field)
        if name is not None:
            if any(desc.name == name for desc in self.parameter_descs):
                field.report('Parameter "%s" was already documented' % (name,))
            self.parameter_descs.append(FieldDesc(name=name, body=field.format()))
            if name not in self.types:
                self._handle_param_not_found(name, field)

    handle_arg = handle_param

    def handle_keyword(self, field: Field) -> None:
        name = self._handle_param_name(field)
        if name is not None:
            # TODO: How should this be matched to the type annotation?
            self.parameter_descs.append(FieldDesc(name=name, body=field.format()))
            if name in self.types:
                field.report('Parameter "%s" is documented as keyword' % (name,))


    def handled_elsewhere(self, field: Field) -> None:
        # Some fields are handled by extract_fields below.
        pass

    handle_ivar = handled_elsewhere
    handle_cvar = handled_elsewhere
    handle_var = handled_elsewhere

    def handle_raises(self, field: Field) -> None:
        name = field.arg
        if name is None:
            field.report('Exception type missing')
            typ_fmt = tags.span(class_='undocumented')("Unknown exception")
        else:
            typ_fmt = self._linker.link_to(name, name)
        self.raise_descs.append(RaisesDesc(type=typ_fmt, body=field.format()))
    handle_raise = handle_raises
    handle_except = handle_raises

    # Warns is just like raises but the syntax is more relax i.e. warning type not required. 
    def handle_warns(self, field: Field) -> None:
        if field.arg is None:
            typ_fmt = None
        else:
            typ_fmt = self._linker.link_to(field.arg, field.arg)
        self.warns_desc.append(FieldDesc(type=typ_fmt, body=field.format()))

    handle_warn = handle_warns
    
    def handle_seealso(self, field: Field) -> None:
        self.seealsos.append(field)
    handle_see = handle_seealso

    def handle_note(self, field: Field) -> None:
        self.notes.append(field)

    def handle_author(self, field: Field) -> None:
        self.authors.append(field)

    def handle_since(self, field: Field) -> None:
        self.sinces.append(field)

    def handleUnknownField(self, field: Field) -> None:
        name = field.tag
        field.report(f"Unknown field '{name}'" )
        self.unknowns[name].append(FieldDesc(name=field.arg, body=field.format()))

    def handle(self, field: Field) -> None:
        m = getattr(self, 'handle_' + field.tag, self.handleUnknownField)
        m(field)

    def resolve_types(self) -> None:
        """Merge information from 'param' fields and AST analysis."""

        params = {param.name: param for param in self.parameter_descs}
        any_info = bool(params)

        # We create a new parameter_descs list to ensure the parameter order
        # matches the AST order.
        new_parameter_descs = []
        for index, (name, type_doc) in enumerate(self.types.items()):
            try:
                param = params.pop(name)
            except KeyError:
                if index == 0 and name in ('self', 'cls'):
                    continue
                param = FieldDesc(name=name, type=type_doc)
                any_info |= type_doc is not None
            else:
                param.type = type_doc
            new_parameter_descs.append(param)

        # Add any leftover parameters, which includes documented **kwargs keywords
        # and non-existing (but documented) parameters.
        new_parameter_descs += params.values()

        # Only replace the descriptions if at least one parameter is documented
        # or annotated.
        if any_info:
            self.parameter_descs = new_parameter_descs

    def format(self) -> Tag:
        r: List[Tag] = []

        r += format_desc_list('Parameters', self.parameter_descs)
        if self.return_desc:
            r += format_desc_list('Returns', [self.return_desc])
        if self.yields_desc:
            r += format_desc_list('Yields', [self.yields_desc])

        r += format_desc_list("Raises", self.raise_descs)
        r += format_desc_list("Warns", self.warns_desc)
        for s_p_l in (('Author', 'Authors', self.authors),
                      ('See Also', 'See Also', self.seealsos),
                      ('Present Since', 'Present Since', self.sinces),
                      ('Note', 'Notes', self.notes)):
            r += format_field_list(*s_p_l)
        for kind, fieldlist in self.unknowns.items():
            r += format_desc_list(f"Unknown Field: {kind}", fieldlist)

        if any(r):
            return tags.table(class_='fieldTable')(r)
        else:
            return tags.transparent


def _is_none_literal(node: ast.expr) -> bool:
    """Does this AST node represent the literal constant None?"""
    return isinstance(node, (ast.Constant, ast.NameConstant)) and node.value is None


def reportErrors(obj: model.Documentable, errs: Sequence[ParseError], section:str='docstring') -> None:
    if errs and obj.fullName() not in obj.system.docstring_syntax_errors:
        obj.system.docstring_syntax_errors.add(obj.fullName())
        for err in errs:
            obj.report(
                f'bad {section}: ' + err.descr(),
                lineno_offset=(err.linenum() or 1) - 1,
                section=section
                )


def parse_docstring(
        obj: model.Documentable,
        doc: str,
        source: model.Documentable,
        markup: Optional[str]=None,
        section: str='docstring',
        ) -> ParsedDocstring:
    """Parse a docstring.
    @param obj: The object we're parsing the documentation for.
    @param doc: The docstring.
    @param source: The object on which the docstring is defined.
        This can differ from C{obj} if the docstring is inherited.
    @param markup: Parse the docstring with the given markup, ignoring system's options.
        Useful for creating L{ParsedDocstring}s from restructuredtext for instance.
    @param section: A custom section to use.
    """

    parser = get_parser(source) if not markup else get_parser_by_name(markup, obj)
    errs: List[ParseError] = []
    try:
        parsed_doc = parser(doc, errs, obj.system.options.processtypes)
    except Exception as e:
        errs.append(ParseError(f'{e.__class__.__name__}: {e}', 1))
        parsed_doc = pydoctor.epydoc.markup.plaintext.parse_docstring(doc, errs)
    if errs:
        reportErrors(source, errs, section=section)
    return parsed_doc

def ensure_parsed_docstring(obj: model.Documentable) -> Optional[model.Documentable]:
    """
    Currently, it's not 100% clear at what point the L{Documentable.parsed_docstring} attribute is set.
    It can be set from the ast builder or later processing step.
    
    This function ensures that the C{parsed_docstring} attribute of a documentable is set to it's final value. 

    @returns: 
        - If the C{obj.parsed_docstring} is set to a L{ParsedDocstring} instance: 
          The source object of the docstring (might be different 
          from C{obj} if the documentation is inherited).
        - If the object is undocumented: C{None}.
    """
    doc, source = get_docstring(obj)

    # Use cached or split version if possible.
    parsed_doc = obj.parsed_docstring

    if source is None:
        if parsed_doc is None:
            # We don't use 'source' if parsed_doc is None, but mypy is not that
            # sophisticated, so we fool it by assigning a dummy object.
            source = obj
        else:
            # A split field is documented by its parent.
            source = obj.parent
            assert source is not None

    if parsed_doc is None and doc is not None:
        parsed_doc = parse_docstring(obj, doc, source)
        obj.parsed_docstring = parsed_doc
    
    if obj.parsed_docstring is not None:
        return source
    else:
        return None


class ParsedStanOnly(ParsedDocstring):
    """
    A L{ParsedDocstring} directly constructed from stan, for caching purposes.
    
    L{to_stan} method simply returns back what's given to L{ParsedStanOnly.__init__}. 
    """
    def __init__(self, stan: Tag):
        super().__init__(fields=[])
        self._fromstan = stan
    def has_body(self) -> bool:
        return True
    def to_stan(self, docstring_linker: Any, compact:bool=False) -> Tag:
        return self._fromstan
    def to_node(self) -> Any:
        raise NotImplementedError()

def _get_parsed_summary(obj: model.Documentable) -> Tuple[Optional[model.Documentable], ParsedDocstring]:
    """
    Ensures that the L{model.Documentable.parsed_summary} attribute of a documentable is set to it's final value. 
    Do not generate summary twice.
    
    @returns: Tuple: C{source}, C{parsed docstring}
    """
    source = ensure_parsed_docstring(obj)
    
    if obj.parsed_summary is not None:
        return (source, obj.parsed_summary)

    if source is None:
        summary_parsed_doc: ParsedDocstring = ParsedStanOnly(format_undocumented(obj))
    else:
        # Tell mypy that if we found a docstring, we also have its source.
        assert obj.parsed_docstring is not None
        summary_parsed_doc = obj.parsed_docstring.get_summary()
    
    assert summary_parsed_doc is not None
    obj.parsed_summary = summary_parsed_doc

    return (source, summary_parsed_doc)

def format_docstring(obj: model.Documentable) -> Tag:
    """Generate an HTML representation of a docstring"""

    source = ensure_parsed_docstring(obj)

    ret: Tag = tags.div
    if source is None:
        ret(tags.p(class_='undocumented')("Undocumented"))
    else:
        assert obj.parsed_docstring is not None, "ensure_parsed_docstring() did not do it's job"
        try:
            stan = obj.parsed_docstring.to_stan(source.docstring_linker, compact=False)
        except Exception as e:
            errs = [ParseError(f'{e.__class__.__name__}: {e}', 1)]
            if source.docstring is None:
                stan = tags.p(class_="undocumented")('Broken description')
            else:
                parsed_doc_plain = pydoctor.epydoc.markup.plaintext.parse_docstring(source.docstring, errs)
                stan = parsed_doc_plain.to_stan(source.docstring_linker)
            reportErrors(source, errs)
        if stan.tagName:
            ret(stan)
        else:
            ret(*stan.children)

    fh = FieldHandler(obj)
    if isinstance(obj, model.Function):
        fh.set_param_types_from_annotations(obj.annotations)
    if source is not None:
        assert obj.parsed_docstring is not None, "ensure_parsed_docstring() did not do it's job"
        for field in obj.parsed_docstring.fields:
            fh.handle(Field.from_epydoc(field, source))
    if isinstance(obj, model.Function):
        fh.resolve_types()
    ret(fh.format())
    return ret

# TODO: FIX https://github.com/twisted/pydoctor/issues/86 
# Use to_node() and compute shortened HTML from node tree with a visitor intead of using the raw source. 
def format_summary(obj: model.Documentable) -> Tag:
    """Generate an shortened HTML representation of a docstring."""

    source, parsed_doc = _get_parsed_summary(obj)
    if not source:
        source = obj
    try:
        # Disallow same_page_optimization in order to make sure we're not
        # breaking links when including the summaries on other pages.
        with source.docstring_linker.disable_same_page_optimazation():
            stan = parsed_doc.to_stan(source.docstring_linker)
    
    except Exception:
        # This problem will likely be reported by the full docstring as well,
        # so don't spam the log.
        stan = tags.span(class_='undocumented')("Broken description")
        obj.parsed_summary = ParsedStanOnly(stan)

    return stan


def format_undocumented(obj: model.Documentable) -> Tag:
    """Generate an HTML representation for an object lacking a docstring."""

    sub_objects_with_docstring_count: DefaultDict[model.DocumentableKind, int] = defaultdict(int)
    sub_objects_total_count: DefaultDict[model.DocumentableKind, int]  = defaultdict(int)
    for sub_ob in obj.contents.values():
        kind = sub_ob.kind
        if kind is not None:
            sub_objects_total_count[kind] += 1
            if sub_ob.docstring is not None:
                sub_objects_with_docstring_count[kind] += 1

    tag: Tag = tags.span(class_='undocumented')
    if sub_objects_with_docstring_count:
        
        kind = obj.kind
        assert kind is not None # if kind is None, object is invisible
        tag(
            "No ", format_kind(kind).lower(), " docstring; ",
            ', '.join(
                f"{sub_objects_with_docstring_count[kind]}/{sub_objects_total_count[kind]} "
                f"{format_kind(kind, plural=sub_objects_with_docstring_count[kind]>=2).lower()}"
                
                for kind in sorted(sub_objects_total_count, key=(lambda x:x.value))
                ),
            " documented"
            )
    else:
        tag("Undocumented")
    return tag


def type2stan(obj: model.Documentable) -> Optional[Tag]:
    parsed_type = get_parsed_type(obj)
    if parsed_type is None:
        return None
    else:
        return parsed_type.to_stan(obj.docstring_linker)

def get_parsed_type(obj: model.Documentable) -> Optional[ParsedDocstring]:
    parsed_type = obj.parsed_type
    if parsed_type is not None:
        return parsed_type

    annotation: Optional[ast.expr] = getattr(obj, 'annotation', None)
    if annotation is not None:
        return colorize_inline_pyval(annotation)

    return None

def format_toc(obj: model.Documentable) -> Optional[Tag]:
    # Load the parsed_docstring if it's not already done. 
    ensure_parsed_docstring(obj)

    if obj.parsed_docstring:
        if obj.system.options.sidebartocdepth > 0:
            toc = obj.parsed_docstring.get_toc(depth=obj.system.options.sidebartocdepth)
            if toc:
                return toc.to_stan(obj.docstring_linker)
    return None


field_name_to_kind = {
    'ivar': model.DocumentableKind.INSTANCE_VARIABLE,
    'cvar': model.DocumentableKind.CLASS_VARIABLE,
    'var': model.DocumentableKind.VARIABLE,
    }


def extract_fields(obj: model.Documentable) -> None:
    """Populate Attributes for module/class variables using fields from
    that module/class's docstring.
    Must only be called for objects that have a docstring.
    """

    doc = obj.docstring
    assert doc is not None, obj
    parsed_doc = parse_docstring(obj, doc, obj)
    obj.parsed_docstring = parsed_doc

    for field in parsed_doc.fields:
        tag = field.tag()
        if tag in ['ivar', 'cvar', 'var', 'type']:
            arg = field.arg()
            if arg is None:
                obj.report("Missing field name in @%s" % (tag,),
                           'docstring', field.lineno)
                continue
            attrobj: Optional[model.Documentable] = obj.contents.get(arg)
            if attrobj is None:
                attrobj = obj.system.Attribute(obj.system, arg, obj)
                attrobj.kind = None
                attrobj.parentMod = obj.parentMod
                obj.system.addObject(attrobj)
            attrobj.setLineNumber(obj.docstring_lineno + field.lineno)
            if tag == 'type':
                attrobj.parsed_type = field.body()
            else:
                attrobj.parsed_docstring = field.body()
                attrobj.kind = field_name_to_kind[tag]

def format_kind(kind: model.DocumentableKind, plural: bool = False) -> str:
    """
    Transform a `model.DocumentableKind` Enum value to string. 
    """
    names = {
        model.DocumentableKind.PACKAGE         : 'Package',
        model.DocumentableKind.MODULE          : 'Module',
        model.DocumentableKind.INTERFACE       : 'Interface',
        model.DocumentableKind.CLASS           : 'Class',
        model.DocumentableKind.CLASS_METHOD    : 'Class Method',
        model.DocumentableKind.STATIC_METHOD   : 'Static Method',
        model.DocumentableKind.METHOD          : 'Method',
        model.DocumentableKind.FUNCTION        : 'Function',
        model.DocumentableKind.CLASS_VARIABLE  : 'Class Variable',
        model.DocumentableKind.ATTRIBUTE       : 'Attribute',
        model.DocumentableKind.INSTANCE_VARIABLE : 'Instance Variable',
        model.DocumentableKind.PROPERTY        : 'Property',
        model.DocumentableKind.VARIABLE        : 'Variable',
        model.DocumentableKind.SCHEMA_FIELD    : 'Attribute',
        model.DocumentableKind.CONSTANT        : 'Constant',
        model.DocumentableKind.TYPE_ALIAS      : 'Type Alias',
        model.DocumentableKind.TYPE_VARIABLE   : 'Type Variable',
    }
    plurals = {
        model.DocumentableKind.CLASS           : 'Classes', 
        model.DocumentableKind.PROPERTY        : 'Properties',
        model.DocumentableKind.TYPE_ALIAS      : 'Type Aliases',
    }
    if plural:
        return plurals.get(kind, names[kind] + 's')
    else:
        return names[kind]

def _format_constant_value(obj: model.Attribute) -> Iterator["Flattenable"]:
    # yield the table title, "Value"
    row = tags.tr(class_="fieldStart")
    row(tags.td(class_="fieldName")("Value"))
    # yield the first row.
    yield row
    
    doc = colorize_pyval(obj.value, 
        linelen=obj.system.options.pyvalreprlinelen,
        maxlines=obj.system.options.pyvalreprmaxlines)
    
    value_repr = doc.to_stan(obj.docstring_linker)

    # Report eventual warnings. It warns when a regex failed to parse or the html2stan() function fails.
    for message in doc.warnings:
        obj.report(message)

    # yield the value repr.
    row = tags.tr()
    row(tags.td(tags.pre(class_='constant-value')(value_repr)))
    yield row

def format_constant_value(obj: model.Attribute) -> "Flattenable":
    """
    Should be only called for L{Attribute} objects that have the L{Attribute.value} property set.
    """
    rows = list(_format_constant_value(obj))
    return tags.table(class_='valueTable')(*rows)

def _split_indentifier_parts_on_case(indentifier:str) -> List[str]:

    def split(text:str, sep:str) -> List[str]:
        # We use \u200b as temp token to hack a split that passes the tests.
        return text.replace(sep, '\u200b'+sep).split('\u200b')

    match = re.match('(_{1,2})?(.*?)(_{1,2})?$', indentifier)
    assert match is not None # the regex always matches
    prefix, text, suffix = match.groups(default='')
    text_parts = []
    
    if text.islower() or text.isupper():
        # We assume snake_case or SCREAMING_SNAKE_CASE.
        text_parts = split(text, '_')
    else:
        # We assume camelCase.  We're not using a regex because we also want it
        # to work with non-ASCII characters (and the Python re module does not
        # support checking for Unicode properties using something like \p{Lu}).
        current_part = ''
        previous_was_upper = False
        for c in text:

            if c.isupper() and not previous_was_upper:
                text_parts.append(current_part)
                current_part = ''
            
            current_part += c
            previous_was_upper = c.isupper()
        
        if current_part:
            text_parts.append(current_part)

    if not text_parts: # the name is composed only by underscores
        text_parts = ['']
    
    if prefix:
        text_parts[0] = prefix + text_parts[0]
    if suffix:
        text_parts[-1] = text_parts[-1] + suffix

    return text_parts

def insert_break_points(text: str) -> 'Flattenable':
    """
    Browsers aren't smart enough to recognize word breaking opportunities in
    snake_case or camelCase, so this function helps them out by inserting
    word break opportunities.

    :note: It support full dotted names and will add a wbr tag after each dot.
    """

    # We use tags.wbr instead of zero-width spaces because
    # zero-width spaces can interfer in subtle ways when copy/pasting a name.
    
    r: List['Flattenable'] = []
    parts = text.split('.')
    for i,t in enumerate(parts):
        _parts = _split_indentifier_parts_on_case(t)
        for i_,p in enumerate(_parts):
            r += [p]
            if i_ != len(_parts)-1:
                r += [tags.wbr()]
        if i != len(parts)-1:
            r += [tags.wbr(), '.']
    return tags.transparent(*r)

