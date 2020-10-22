"""
Convert epydoc markup into renderable content.
"""

from collections import defaultdict
from importlib import import_module
from typing import (
    Callable, DefaultDict, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
)
from urllib.parse import quote
import ast
import builtins
import itertools
import os
import sys

import astor
import attr

from pydoctor import model
from pydoctor.epydoc.markup import Field as EpydocField, ParseError
from twisted.web.template import Tag, tags
from pydoctor.epydoc.markup import DocstringLinker, ParsedDocstring
import pydoctor.epydoc.markup.plaintext


def _find_stdlib_dir() -> str:
    """Find the standard library location for the currently running
    Python interpreter.
    """

    # When running in a virtualenv, when some (but not all) modules
    # may be symlinked. We want the actual installation location of
    # the standard library, not the location of the virtualenv.
    os_mod_path = os.__file__
    if os_mod_path.endswith('.pyc') or os_mod_path.endswith('.pyo'):
        os_mod_path = os_mod_path[:-1]
    return os.path.dirname(os.path.realpath(os_mod_path))

STDLIB_DIR = _find_stdlib_dir()
STDLIB_URL = 'https://docs.python.org/3/library/'


def link(o: model.Documentable) -> str:
    return quote(o.fullName()+'.html')


def get_parser(obj: model.Documentable) -> Callable[[str, List[ParseError]], ParsedDocstring]:
    formatname = obj.system.options.docformat
    try:
        mod = import_module('pydoctor.epydoc.markup.' + formatname)
    except ImportError as e:
        msg = 'Error trying to import %r parser:\n\n    %s: %s\n\nUsing plain text formatting only.'%(
            formatname, e.__class__.__name__, e)
        obj.system.msg('epydoc2stan', msg, thresh=-1, once=True)
        mod = pydoctor.epydoc.markup.plaintext
    return getattr(mod, 'parse_docstring') # type: ignore[no-any-return]


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


def stdlib_doc_link_for_name(name: str) -> Optional[str]:
    parts = name.split('.')
    for i in range(len(parts), 0, -1):
        sub_parts = parts[:i]
        filename = '/'.join(sub_parts)
        sub_name = '.'.join(sub_parts)
        if sub_name == 'os.path' \
               or os.path.exists(os.path.join(STDLIB_DIR, filename) + '.py') \
               or os.path.exists(os.path.join(STDLIB_DIR, filename, '__init__.py')) \
               or os.path.exists(os.path.join(STDLIB_DIR, 'lib-dynload', filename) + '.so') \
               or sub_name in sys.builtin_module_names:
            return STDLIB_URL + sub_name + '.html#' + name
    part0 = parts[0]
    if part0 in builtins.__dict__ and not part0.startswith('__'):
        bltin = builtins.__dict__[part0]
        if isinstance(bltin, type):
            if issubclass(bltin, BaseException):
                return STDLIB_URL + 'exceptions.html#' + name
            else:
                return STDLIB_URL + 'stdtypes.html#' + name
        elif callable(bltin):
            return STDLIB_URL + 'functions.html#' + name
        else:
            return STDLIB_URL + 'constants.html#' + name
    return None


class _EpydocLinker(DocstringLinker):

    def __init__(self, obj: model.Documentable):
        self.obj = obj

    def _objLink(self, obj: model.Documentable) -> str:
        if obj.documentation_location is model.DocLocation.PARENT_PAGE:
            p = obj.parent
            if isinstance(p, model.Module) and p.name == '__init__':
                p = p.parent
            return link(p) + '#' + quote(obj.name)
        elif obj.documentation_location is model.DocLocation.OWN_PAGE:
            return link(obj)
        else:
            raise AssertionError(
                f"Unknown documentation_location: {obj.documentation_location}")

    def look_for_name(self,
            name: str,
            candidates: Iterable[model.Documentable]
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
            return potential_targets[0] # type: ignore[no-any-return]
        elif len(potential_targets) > 1:
            self.obj.report(
                "ambiguous ref to %s, could be %s" % (
                    name,
                    ', '.join(ob.fullName() for ob in potential_targets)),
                section='resolve_identifier_xref')
        return None

    def look_for_intersphinx(self, name: str) -> Optional[str]:
        """
        Return link for `name` based on intersphinx inventory.

        Return None if link is not found.
        """
        return self.obj.system.intersphinx.getLink(name) # type: ignore[no-any-return]

    def resolve_identifier_xref(self, fullID: str) -> str:

        # There is a lot of DWIM here. Look for a global match first,
        # to reduce the chance of a false positive.

        # Check if fullID is the fullName of an object.
        target = self.obj.system.objForFullName(fullID)
        if target is not None:
            return self._objLink(target)

        # Check to see if fullID names a builtin or standard library module.
        fullerID = self.obj.expandName(fullID)
        linktext = stdlib_doc_link_for_name(fullerID)
        if linktext is not None:
            return linktext

        # Check if the fullID exists in an intersphinx inventory.
        target_name = self.look_for_intersphinx(fullerID)
        if not target_name:
            # FIXME: https://github.com/twisted/pydoctor/issues/125
            # expandName is unreliable so in the case fullerID fails, we
            # try our luck with fullID.
            target_name = self.look_for_intersphinx(fullID)
        if target_name:
            return target_name

        # Since there was no global match, go look for the name in the
        # context where it was used.

        # Check if fullID refers to an object by Python name resolution
        # in our context. Walk up the object tree and see if fullID refers
        # to an object by Python name resolution in each context.
        src: Optional[model.Documentable] = self.obj
        while src is not None:
            target = src.resolveName(fullID)
            if target is not None:
                return self._objLink(target)
            src = src.parent

        # Walk up the object tree again and see if fullID refers to an
        # object in an "uncle" object.  (So if p.m1 has a class C, the
        # docstring for p.m2 can say L{C} to refer to the class in m1).
        # If at any level fullID refers to more than one object, complain.
        src = self.obj
        while src is not None:
            target = self.look_for_name(fullID, src.contents.values())
            if target is not None:
                return self._objLink(target)
            src = src.parent

        # Examine every module and package in the system and see if fullID
        # names an object in each one.  Again, if more than one object is
        # found, complain.
        target = self.look_for_name(fullID, itertools.chain(
            self.obj.system.objectsOfType(model.Module),
            self.obj.system.objectsOfType(model.Package)))
        if target is not None:
            return self._objLink(target)

        if fullID == fullerID:
            self.obj.report(
                "invalid ref to '%s' not resolved" % (fullID,),
                section='resolve_identifier_xref')
        else:
            self.obj.report(
                "invalid ref to '%s' resolved as '%s'" % (fullID, fullerID),
                section='resolve_identifier_xref')
        raise LookupError(fullID)


@attr.s(auto_attribs=True)
class FieldDesc:

    kind: str
    name: Optional[str] = None
    type: Optional[Tag] = None
    body: Optional[Tag] = None

    def format(self) -> Tag:
        if self.body is None:
            body = tags.transparent
        else:
            body = self.body
        if self.type is not None:
            body = body, ' (type: ', self.type, ')'
        return tags.transparent(body)


def format_desc_list(label: str, descs: Sequence[FieldDesc]) -> List[Tag]:
    if not descs:
        return []
    r: List[Tag] = []
    first = True
    for d in descs:
        if first:
            row = tags.tr(class_="fieldStart")
            row(tags.td(class_="fieldName")(label))
            first = False
        else:
            row = tags.tr()
            row(tags.td())
        if d.name is None:
            row(tags.td(colspan="2")(d.format()))
        else:
            row(tags.td(class_="fieldArg")(d.name), tags.td(d.format()))
        r.append(row)
    return r


class Field:
    """Like pydoctor.epydoc.markup.Field, but without the gross accessor
    methods and with a formatted body.
    """

    def __init__(self, field: EpydocField, source: model.Documentable):
        self.tag = field.tag()
        self.arg = field.arg()
        self.source = source
        self.lineno = field.lineno
        self.body = field.body().to_stan(_EpydocLinker(source))

    def __repr__(self) -> str:
        r = repr(self.body)
        if len(r) > 25:
            r = r[:20] + '...' + r[-2:]
        return "<%s %r %r %d %s>"%(self.__class__.__name__,
                                   self.tag, self.arg, self.lineno, r)

    def report(self, message: str) -> None:
        self.source.report(message, lineno_offset=self.lineno, section='docstring')


def format_field_list(singular: str, plural: str, fields: Sequence[Field]) -> List[Tag]:
    if not fields:
        return []
    if len(fields) > 1:
        label = plural
    else:
        label = singular
    rows: List[Tag] = []
    first = True
    for field in fields:
        if first:
            row = tags.tr(class_="fieldStart")
            row(tags.td(class_="fieldName")(label))
            first=False
        else:
            row = tags.tr()
            row(tags.td())
        row(tags.td(colspan="2")(field.body))
        rows.append(row)
    return rows


class FieldHandler:

    def __init__(self, obj: model.Documentable):
        self.obj = obj

        self.types: Dict[str, Optional[Tag]] = {}

        self.parameter_descs: List[FieldDesc] = []
        self.return_desc: Optional[FieldDesc] = None
        self.raise_descs: List[FieldDesc] = []
        self.seealsos: List[Field] = []
        self.notes: List[Field] = []
        self.authors: List[Field] = []
        self.sinces: List[Field] = []
        self.unknowns: List[FieldDesc] = []

    def set_param_types_from_annotations(
            self, annotations: Mapping[str, Optional[ast.expr]]
            ) -> None:
        linker = _EpydocLinker(self.obj)
        formatted_annotations = {
            name: None if value is None else AnnotationDocstring(value).to_stan(linker)
            for name, value in annotations.items()
            }
        ret_type = formatted_annotations.pop('return', None)
        self.types.update(formatted_annotations)
        if ret_type is not None:
            self.return_desc = FieldDesc(kind='return', type=ret_type)

    def handle_return(self, field: Field) -> None:
        if field.arg is not None:
            field.report('Unexpected argument in %s field' % (field.tag,))
        if not self.return_desc:
            self.return_desc = FieldDesc(kind='return')
        self.return_desc.body = field.body
    handle_returns = handle_return

    def handle_returntype(self, field: Field) -> None:
        if field.arg is not None:
            field.report('Unexpected argument in %s field' % (field.tag,))
        if not self.return_desc:
            self.return_desc = FieldDesc(kind='return')
        self.return_desc.type = field.body
    handle_rtype = handle_returntype

    def _handle_param_name(self, field: Field) -> Optional[str]:
        name = field.arg
        if name is None:
            field.report('Parameter name missing')
            return None
        if name and name.startswith('*'):
            field.report('Parameter name "%s" should not include asterixes' % (name,))
            return name.lstrip('*')
        else:
            return name

    def add_info(self, desc_list: List[FieldDesc], name: Optional[str], field: Field) -> None:
        desc_list.append(FieldDesc(kind=field.tag, name=name, body=field.body))

    def handle_type(self, field: Field) -> None:
        if isinstance(self.obj, model.Function):
            name = self._handle_param_name(field)
        else:
            # Note: extract_fields() will issue warnings about missing field
            #       names, so we can silently ignore them here.
            # TODO: Processing the fields once in extract_fields() and again
            #       in format_docstring() adds complexity and can cause
            #       inconsistencies.
            name = field.arg
        if name is not None:
            self.types[name] = field.body

    def handle_param(self, field: Field) -> None:
        name = self._handle_param_name(field)
        if name is not None:
            self.add_info(self.parameter_descs, name, field)
    handle_arg = handle_param
    handle_keyword = handle_param


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
        self.add_info(self.raise_descs, name, field)
    handle_raise = handle_raises

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
        field.report('Unknown field "%s"' % (field.tag,))
        self.add_info(self.unknowns, field.arg, field)

    def handle(self, field: Field) -> None:
        m = getattr(self, 'handle_' + field.tag, self.handleUnknownField)
        m(field)

    def resolve_types(self) -> None:
        for pd in self.parameter_descs:
            if pd.name in self.types:
                pd.type = self.types[pd.name]

    def format(self) -> Tag:
        r = []

        r.append(format_desc_list('Parameters', self.parameter_descs))
        if self.return_desc:
            r.append(tags.tr(class_="fieldStart")(tags.td(class_="fieldName")('Returns'),
                               tags.td(colspan="2")(self.return_desc.format())))
        r.append(format_desc_list("Raises", self.raise_descs))
        for s_p_l in (('Author', 'Authors', self.authors),
                      ('See Also', 'See Also', self.seealsos),
                      ('Present Since', 'Present Since', self.sinces),
                      ('Note', 'Notes', self.notes)):
            r.append(format_field_list(*s_p_l))
        unknowns: Dict[str, List[FieldDesc]] = {}
        for fieldinfo in self.unknowns:
            unknowns.setdefault(fieldinfo.kind, []).append(fieldinfo)
        for kind, fieldlist in unknowns.items():
            r.append(format_desc_list(f"Unknown Field: {kind}", fieldlist))

        if any(r):
            return tags.table(class_='fieldTable')(r)
        else:
            return tags.transparent


def reportErrors(obj: model.Documentable, errs: Sequence[ParseError]) -> None:
    if errs and obj.fullName() not in obj.system.docstring_syntax_errors:
        obj.system.docstring_syntax_errors.add(obj.fullName())
        for err in errs:
            obj.report(
                'bad docstring: ' + err.descr(),
                lineno_offset=err.linenum() - 1,
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

    parser = get_parser(obj)
    errs: List[ParseError] = []
    try:
        pdoc = parser(doc, errs)
    except Exception as e:
        errs.append(ParseError(f'{e.__class__.__name__}: {e}', 1))
        pdoc = pydoctor.epydoc.markup.plaintext.parse_docstring(doc, errs)
    if errs:
        reportErrors(source, errs)
    return pdoc


def format_docstring(obj: model.Documentable) -> Tag:
    """Generate an HTML representation of a docstring"""

    doc, source = get_docstring(obj)

    # Use cached or split version if possible.
    pdoc = obj.parsed_docstring

    ret: Tag = tags.div
    if pdoc is None:
        if doc is None:
            ret(class_='undocumented')("Undocumented")
            return ret
        else:
            # Tell mypy that if we found a docstring, we also have its source.
            assert source is not None
        pdoc = parse_docstring(obj, doc, source)
        obj.parsed_docstring = pdoc
    elif source is None:
        # A split field is documented by its parent.
        source = obj.parent

    try:
        stan = pdoc.to_stan(_EpydocLinker(source))
    except Exception as e:
        errs = [ParseError(f'{e.__class__.__name__}: {e}', 1)]
        if doc is None:
            stan = tags.p(class_="undocumented")('Broken description')
        else:
            pdoc_plain = pydoctor.epydoc.markup.plaintext.parse_docstring(doc, errs)
            stan = pdoc_plain.to_stan(_EpydocLinker(source))
        reportErrors(source, errs)
    if stan.tagName:
        ret(stan)
    else:
        ret(*stan.children)

    fields = pdoc.fields
    fh = FieldHandler(obj)
    if isinstance(obj, model.Function):
        fh.set_param_types_from_annotations(obj.annotations)
    for field in fields:
        fh.handle(Field(field, source))
    fh.resolve_types()
    ret(fh.format())
    return ret


def format_summary(obj: model.Documentable) -> Tag:
    """Generate an shortened HTML representation of a docstring."""

    doc, source = get_docstring(obj)
    if doc is None:
        # Attributes can be documented as fields in their parent's docstring.
        if isinstance(obj, model.Attribute):
            pdoc = obj.parsed_docstring
        else:
            pdoc = None
        if pdoc is None:
            return format_undocumented(obj)
        source = obj.parent
        # Since obj is an Attribute, it has a parent.
        assert source is not None
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
        pdoc = parse_docstring(obj, ' '.join(lines), source)

    try:
        stan = pdoc.to_stan(_EpydocLinker(source))
    except Exception:
        # This problem will likely be reported by the full docstring as well,
        # so don't spam the log.
        return tags.span(class_='undocumented')("Broken description")

    content = [stan] if stan.tagName else stan.children
    if content and isinstance(content[0], Tag) and content[0].tagName == 'p':
        content = content[0].children
    return tags.span(*content)


def format_undocumented(obj: model.Documentable) -> Tag:
    """Generate an HTML representation for an object lacking a docstring."""

    subdocstrings: DefaultDict[str, int] = defaultdict(int)
    subcounts: DefaultDict[str, int]  = defaultdict(int)
    for subob in obj.contents.values():
        k = subob.kind.lower()
        subcounts[k] += 1
        if subob.docstring is not None:
            subdocstrings[k] += 1
    if isinstance(obj, model.Package):
        subcounts['module'] -= 1

    tag: Tag = tags.span(class_='undocumented')
    if subdocstrings:
        plurals = {'class': 'classes'}
        tag(
            "No ", obj.kind.lower(), " docstring; "
            ', '.join(
                f"{subdocstrings[k]}/{subcounts[k]} "
                f"{plurals.get(k, k + 's')}"
                for k in sorted(subcounts)
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
    parsed_type: Optional[ParsedDocstring] = getattr(obj, 'parsed_type', None)
    if parsed_type is not None:
        return parsed_type

    annotation: Optional[ast.expr] = getattr(obj, 'annotation', None)
    if annotation is not None:
        return AnnotationDocstring(annotation)

    return None


class AnnotationDocstring(ParsedDocstring):

    def __init__(self, annotation: ast.expr) -> None:
        ParsedDocstring.__init__(self, ())
        self.annotation = annotation

    def to_stan(self, docstring_linker: DocstringLinker) -> Tag:
        src = astor.to_source(self.annotation).strip()
        ret: Tag = tags.code(src)
        return ret


field_name_to_human_name = {
    'ivar': 'Instance Variable',
    'cvar': 'Class Variable',
    'var': 'Variable',
    }


def extract_fields(obj: model.Documentable) -> None:
    doc, source = get_docstring(obj)
    if doc is None:
        return
    else:
        # Tell mypy that if we found a docstring, we also have its source.
        assert source is not None

    pdoc = parse_docstring(obj, doc, source)
    obj.parsed_docstring = pdoc

    for field in pdoc.fields:
        tag = field.tag()
        if tag in ['ivar', 'cvar', 'var', 'type']:
            arg = field.arg()
            if arg is None:
                source.report("Missing field name in @%s" % (tag,),
                              'docstring', field.lineno)
                continue
            attrobj = obj.contents.get(arg)
            if attrobj is None:
                attrobj = obj.system.Attribute(obj.system, arg, obj)
                attrobj.kind = None
                attrobj.parentMod = obj.parentMod
                obj.system.addObject(attrobj)
            attrobj.setLineNumber(source.docstring_lineno + field.lineno)
            if tag == 'type':
                attrobj.parsed_type = field.body()
            else:
                attrobj.parsed_docstring = field.body()
                attrobj.kind = field_name_to_human_name[tag]
