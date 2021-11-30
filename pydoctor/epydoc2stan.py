"""
Convert L{pydoctor.epydoc} parsed markup into renderable content.
"""

from collections import defaultdict
from typing import (
    TYPE_CHECKING, Callable, ClassVar, DefaultDict, Dict, Generator, Iterable,
    Iterator, List, Mapping, Optional, Sequence, Tuple, Union
)
import ast
import itertools

import attr

from pydoctor import model
from pydoctor.epydoc.markup import Field as EpydocField, ParseError, get_parser_by_name
from twisted.web.template import Tag, tags
from pydoctor.epydoc.markup import DocstringLinker, ParsedDocstring
import pydoctor.epydoc.markup.plaintext
from pydoctor.epydoc.markup._pyval_repr import colorize_pyval, colorize_inline_pyval

if TYPE_CHECKING:
    from twisted.web.template import Flattenable

def get_parser(obj: model.Documentable) -> Callable[[str, List[ParseError], bool], ParsedDocstring]:
    """
    Get the C{parse_docstring(str, List[ParseError], bool) -> ParsedDocstring} function. 
    """    
    # Use module's __docformat__ if specified, else use system's.
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


def taglink(o: model.Documentable, page_url: str, label: Optional["Flattenable"] = None) -> Tag:
    if not o.isVisible:
        o.system.msg("html", "don't link to %s"%o.fullName())

    if label is None:
        label = o.fullName()

    url = o.url
    if url.startswith(page_url + '#'):
        # When linking to an item on the same page, omit the path.
        # Besides shortening the HTML, this also avoids the page being reloaded
        # if the query string is non-empty.
        url = url[len(page_url):]

    ret: Tag = tags.a(label, href=url)
    return ret


class _EpydocLinker(DocstringLinker):

    def __init__(self, obj: model.Documentable):
        self.obj = obj

    def look_for_name(self,
            name: str,
            candidates: Iterable[model.Documentable],
            lineno: int
            ) -> Optional[model.Documentable]:
        part0 = name.split('.')[0]
        potential_targets = []
        for src in candidates:
            if part0 not in src.contents:
                continue
            target = src.resolveName(name)
            if target is not None and target not in potential_targets:
                potential_targets.append(target)
        if len(potential_targets) == 1:
            return potential_targets[0]
        elif len(potential_targets) > 1:
            self.obj.report(
                "ambiguous ref to %s, could be %s" % (
                    name,
                    ', '.join(ob.fullName() for ob in potential_targets)),
                'resolve_identifier_xref', lineno)
        return None

    def look_for_intersphinx(self, name: str) -> Optional[str]:
        """
        Return link for `name` based on intersphinx inventory.

        Return None if link is not found.
        """
        return self.obj.system.intersphinx.getLink(name)

    def link_to(self, identifier: str, label: "Flattenable") -> Tag:
        fullID = self.obj.expandName(identifier)

        target = self.obj.system.objForFullName(fullID)
        if target is not None:
            return taglink(target, self.obj.page_object.url, label)

        url = self.look_for_intersphinx(fullID)
        if url is not None:
            return tags.a(label, href=url)

        return tags.transparent(label)

    def link_xref(self, target: str, label: "Flattenable", lineno: int) -> Tag:
        xref: "Flattenable"
        try:
            resolved = self._resolve_identifier_xref(target, lineno)
        except LookupError:
            xref = label
        else:
            if isinstance(resolved, model.Documentable):
                xref = taglink(resolved, self.obj.page_object.url, label)
            else:
                xref = tags.a(label, href=resolved)
        ret: Tag = tags.code(xref)
        return ret

    def resolve_identifier(self, identifier: str) -> Optional[str]:
        fullID = self.obj.expandName(identifier)

        target = self.obj.system.objForFullName(fullID)
        if target is not None:
            return target.url

        return self.look_for_intersphinx(fullID)

    def _resolve_identifier_xref(self,
            identifier: str,
            lineno: int
            ) -> Union[str, model.Documentable]:
        """
        Resolve a crossreference link to a Python identifier.
        This will resolve the identifier to any reasonable target,
        even if it has to look in places where Python itself would not.

        @param identifier: The name of the Python identifier that
            should be linked to.
        @param lineno: The line number within the docstring at which the
            crossreference is located.
        @return: The referenced object within our system, or the URL of
            an external target (found via Intersphinx).
        @raise LookupError: If C{identifier} could not be resolved.
        """

        # There is a lot of DWIM here. Look for a global match first,
        # to reduce the chance of a false positive.

        # Check if 'identifier' is the fullName of an object.
        target = self.obj.system.objForFullName(identifier)
        if target is not None:
            return target

        # Check if the fullID exists in an intersphinx inventory.
        fullID = self.obj.expandName(identifier)
        target_url = self.look_for_intersphinx(fullID)
        if not target_url:
            # FIXME: https://github.com/twisted/pydoctor/issues/125
            # expandName is unreliable so in the case fullID fails, we
            # try our luck with 'identifier'.
            target_url = self.look_for_intersphinx(identifier)
        if target_url:
            return target_url

        # Since there was no global match, go look for the name in the
        # context where it was used.

        # Check if 'identifier' refers to an object by Python name resolution
        # in our context. Walk up the object tree and see if 'identifier' refers
        # to an object by Python name resolution in each context.
        src: Optional[model.Documentable] = self.obj
        while src is not None:
            target = src.resolveName(identifier)
            if target is not None:
                return target
            src = src.parent

        # Walk up the object tree again and see if 'identifier' refers to an
        # object in an "uncle" object.  (So if p.m1 has a class C, the
        # docstring for p.m2 can say L{C} to refer to the class in m1).
        # If at any level 'identifier' refers to more than one object, complain.
        src = self.obj
        while src is not None:
            target = self.look_for_name(identifier, src.contents.values(), lineno)
            if target is not None:
                return target
            src = src.parent

        # Examine every module and package in the system and see if 'identifier'
        # names an object in each one.  Again, if more than one object is
        # found, complain.
        target = self.look_for_name(
            identifier, self.obj.system.objectsOfType(model.Module), lineno)
        if target is not None:
            return target

        message = f'Cannot find link target for "{fullID}"'
        if identifier != fullID:
            message = f'{message}, resolved from "{identifier}"'
        root_idx = fullID.find('.')
        if root_idx != -1 and fullID[:root_idx] not in self.obj.system.root_names:
            message += ' (you can link to external docs with --intersphinx)'
        self.obj.report(message, 'resolve_identifier_xref', lineno)
        raise LookupError(identifier)


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
            name = self.name

            # Add the stars to the params names just before generating the field stan, not before.
            if isinstance(name, VariableArgument):
                name = f"*{name}"
            elif isinstance(name, KeywordArgument):
                name = f"**{name}"
            
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
        return self.body.to_stan(_EpydocLinker(self.source))

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
        self._linker = _EpydocLinker(self.obj)

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


def reportErrors(obj: model.Documentable, errs: Sequence[ParseError]) -> None:
    if errs and obj.fullName() not in obj.system.docstring_syntax_errors:
        obj.system.docstring_syntax_errors.add(obj.fullName())
        for err in errs:
            obj.report(
                'bad docstring: ' + err.descr(),
                lineno_offset=(err.linenum() or 1) - 1,
                section='docstring'
                )


def parse_docstring(
        obj: model.Documentable,
        doc: str,
        source: model.Documentable,
        ) -> ParsedDocstring:
    """Parse a docstring.
    @param obj: The object we're parsing the documentation for.
    @param doc: The docstring.
    @param source: The object on which the docstring is defined.
        This can differ from C{obj} if the docstring is inherited.
    """

    # the docstring should be parsed using the format of the module it was inherited from
    parser = get_parser(source)
    errs: List[ParseError] = []
    try:
        parsed_doc = parser(doc, errs, obj.system.options.processtypes)
    except Exception as e:
        errs.append(ParseError(f'{e.__class__.__name__}: {e}', 1))
        parsed_doc = pydoctor.epydoc.markup.plaintext.parse_docstring(doc, errs)
    if errs:
        reportErrors(source, errs)
    return parsed_doc


def format_docstring(obj: model.Documentable) -> Tag:
    """Generate an HTML representation of a docstring"""

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

    ret: Tag = tags.div
    if parsed_doc is None:
        ret(tags.p(class_='undocumented')("Undocumented"))
    else:
        try:
            stan = parsed_doc.to_stan(_EpydocLinker(source))
        except Exception as e:
            errs = [ParseError(f'{e.__class__.__name__}: {e}', 1)]
            if doc is None:
                stan = tags.p(class_="undocumented")('Broken description')
            else:
                parsed_doc_plain = pydoctor.epydoc.markup.plaintext.parse_docstring(doc, errs)
                stan = parsed_doc_plain.to_stan(_EpydocLinker(source))
            reportErrors(source, errs)
        if stan.tagName:
            ret(stan)
        else:
            ret(*stan.children)

    fh = FieldHandler(obj)
    if isinstance(obj, model.Function):
        fh.set_param_types_from_annotations(obj.annotations)
    if parsed_doc is not None:
        for field in parsed_doc.fields:
            fh.handle(Field.from_epydoc(field, source))
    if isinstance(obj, model.Function):
        fh.resolve_types()
    ret(fh.format())
    return ret

# TODO: FIX https://github.com/twisted/pydoctor/issues/86 
# Use to_node() and compute shortened HTML from node tree with a visitor intead of using the raw source. 
def format_summary(obj: model.Documentable) -> Tag:
    """Generate an shortened HTML representation of a docstring."""

    doc, source = get_docstring(obj)

    if (doc is None or source is not obj) and isinstance(obj, model.Attribute):
        # Attributes can be documented as fields in their parent's docstring.
        parsed_doc = obj.parsed_docstring
    else:
        parsed_doc = None

    if parsed_doc is not None:
        # The docstring was split off from the Attribute's parent docstring.
        source = obj.parent
        assert source is not None
    elif doc is None:
        return format_undocumented(obj)
    else:
        # Tell mypy that if we found a docstring, we also have its source.
        assert source is not None
        # Use up to three first non-empty lines of doc string as summary.
        lines = [
            line.strip()
            for line in itertools.takewhile(
                lambda line: line.strip(),
                itertools.dropwhile(lambda line: not line.strip(), doc.split('\n'))
                )
            ]
        if len(lines) > 3:
            return tags.span(class_='undocumented')("No summary")
        parsed_doc = parse_docstring(obj, ' '.join(lines), source)

    try:
        stan = parsed_doc.to_stan(_EpydocLinker(source))
    except Exception:
        # This problem will likely be reported by the full docstring as well,
        # so don't spam the log.
        return tags.span(class_='undocumented')("Broken description")

    content: Sequence["Flattenable"] = [stan] if stan.tagName else stan.children
    if content and isinstance(content[0], Tag) and content[0].tagName == 'p':
        content = content[0].children
    return Tag('')(*content)


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
        return parsed_type.to_stan(_EpydocLinker(obj))

def get_parsed_type(obj: model.Documentable) -> Optional[ParsedDocstring]:
    parsed_type = obj.parsed_type
    if parsed_type is not None:
        return parsed_type

    annotation: Optional[ast.expr] = getattr(obj, 'annotation', None)
    if annotation is not None:
        return colorize_inline_pyval(annotation)

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
    }
    plurals = {
        model.DocumentableKind.CLASS           : 'Classes', 
        model.DocumentableKind.PROPERTY        : 'Properties',
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
    
    value_repr = doc.to_stan(_EpydocLinker(obj))

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
