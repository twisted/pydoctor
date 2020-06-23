"""
Convert epydoc markup into renderable content.
"""

from __future__ import print_function

import astor

from importlib import import_module
import itertools
import os
import sys

from pydoctor import model
from pydoctor.epydoc.markup import ParseError
from six import string_types
from six.moves import builtins
from six.moves.urllib.parse import quote
from twisted.web.template import Tag, tags
from pydoctor.epydoc.markup import DocstringLinker, ParsedDocstring
import pydoctor.epydoc.markup.plaintext

try:
    import exceptions
except ImportError:
    exceptions = builtins


def _find_stdlib_dir():
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
STDLIB_URL = 'http://docs.python.org/library/'


def link(o):
    return quote(o.fullName()+'.html')


def get_parser(obj):
    formatname = obj.system.options.docformat
    try:
        mod = import_module('pydoctor.epydoc.markup.' + formatname)
    except ImportError as e:
        msg = 'Error trying to import %r parser:\n\n    %s: %s\n\nUsing plain text formatting only.'%(
            formatname, e.__class__.__name__, e)
        obj.system.msg('epydoc2stan', msg, thresh=-1, once=True)
        mod = pydoctor.epydoc.markup.plaintext
    return mod.parse_docstring


def get_docstring(obj):
    for source in obj.docsources():
        doc = source.docstring
        if doc:
            return doc, source
        if doc is not None:
            # Treat empty docstring as undocumented.
            return None, source
    return None, None


def stdlib_doc_link_for_name(name):
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
        if part0 in exceptions.__dict__:
            return STDLIB_URL + 'exceptions.html#exceptions.' + name
        elif isinstance(bltin, type):
            return STDLIB_URL + 'stdtypes.html#' + name
        elif callable(bltin):
            return STDLIB_URL + 'functions.html#' + name
        else:
            return STDLIB_URL + 'constants.html#' + name
    return None


class _EpydocLinker(DocstringLinker):

    def __init__(self, obj):
        self.obj = obj

    def _objLink(self, obj):
        if obj.documentation_location is model.DocLocation.PARENT_PAGE:
            p = obj.parent
            if isinstance(p, model.Module) and p.name == '__init__':
                p = p.parent
            return link(p) + '#' + quote(obj.name)
        elif obj.documentation_location is model.DocLocation.OWN_PAGE:
            return link(obj)
        else:
            raise AssertionError(
                "Unknown documentation_location: %s" % obj.documentation_location)

    def look_for_name(self, name, candidates):
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
                section='resolve_identifier_xref')
        return None

    def look_for_intersphinx(self, name):
        """
        Return link for `name` based on intersphinx inventory.

        Return None if link is not found.
        """
        return self.obj.system.intersphinx.getLink(name)

    def resolve_identifier_xref(self, fullID):

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
        target = self.look_for_intersphinx(fullerID)
        if not target:
            # FIXME: https://github.com/twisted/pydoctor/issues/125
            # expandName is unreliable so in the case fullerID fails, we
            # try our luck with fullID.
            target = self.look_for_intersphinx(fullID)
        if target:
            return target

        # Since there was no global match, go look for the name in the
        # context where it was used.

        # Check if fullID refers to an object by Python name resolution
        # in our context. Walk up the object tree and see if fullID refers
        # to an object by Python name resolution in each context.
        src = self.obj
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
        return None


class FieldDesc(object):
    def __init__(self):
        self.kind = None
        self.name = None
        self.type = None
        self.body = None
    def format(self):
        if self.body is None:
            body = ''
        else:
            body = self.body
        if self.type is not None:
            body = body, ' (type: ', self.type, ')'
        return body
    def __repr__(self):
        contents = []
        for k, v in self.__dict__.items():
            contents.append("%s=%r"%(k, v))
        return "<%s(%s)>"%(self.__class__.__name__, ', '.join(contents))


def format_desc_list(singular, descs, plural=None):
    if plural is None:
        plural = singular + 's'
    if not descs:
        return ''
    if len(descs) > 1:
        label = plural
    else:
        label = singular
    r = []
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

def format_field_list(obj, singular, fields, plural=None):
    if plural is None:
        plural = singular + 's'
    if not fields:
        return ''
    if len(fields) > 1:
        label = plural
    else:
        label = singular
    rows = []
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


class Field(object):
    """Like pydoctor.epydoc.markup.Field, but without the gross accessor
    methods and with a formatted body."""
    def __init__(self, field, obj):
        self.tag = field.tag()
        self.arg = field.arg()
        self.lineno = field.lineno
        self.body = field.body().to_stan(_EpydocLinker(obj))

    def __repr__(self):
        r = repr(self.body)
        if len(r) > 25:
            r = r[:20] + '...' + r[-2:]
        return "<%s %r %r %s %d>"%(self.__class__.__name__,
                             self.tag, self.arg, self.lineno, r)

class FieldHandler(object):
    def __init__(self, obj):
        self.obj = obj

        self.types = {}

        self.parameter_descs = []
        self.return_desc = None
        self.raise_descs = []
        self.seealsos = []
        self.notes = []
        self.authors = []
        self.sinces = []
        self.unknowns = []
        self.unattached_types = {}

    def redef(self, field):
        self.obj.system.msg(
            "epytext",
            "on %r: redefinition of @type %s"%(self.obj.fullName(), field.arg),
            thresh=-1)

    def handle_return(self, field):
        if not self.return_desc:
            self.return_desc = FieldDesc()
        if self.return_desc.body:
            self.obj.system.msg('epydoc2stan', 'XXX')
        self.return_desc.body = field.body
    handle_returns = handle_return

    def handle_returntype(self, field):
        if not self.return_desc:
            self.return_desc = FieldDesc()
        if self.return_desc.type:
            self.obj.system.msg('epydoc2stan', 'XXX')
        self.return_desc.type = field.body
    handle_rtype = handle_returntype

    def add_type_info(self, desc_list, field):
        if desc_list and desc_list[-1].name == field.arg:
            if desc_list[-1].type is not None:
                self.redef(field)
            desc_list[-1].type = field.body
        else:
            d = FieldDesc()
            d.kind = field.tag
            d.name = field.arg
            d.type = field.body
            desc_list.append(d)

    def add_info(self, desc_list, field):
        d = FieldDesc()
        d.kind = field.tag
        d.name = field.arg
        d.body = field.body
        desc_list.append(d)

    def handle_type(self, field):
        self.types[field.arg] = field.body

    def handle_param(self, field):
        self.add_info(self.parameter_descs, field)
    handle_arg = handle_param
    handle_keyword = handle_param


    def handled_elsewhere(self, field):
        # Some fields are handled by extract_fields below.
        pass

    handle_ivar = handled_elsewhere
    handle_cvar = handled_elsewhere
    handle_var = handled_elsewhere

    def handle_raises(self, field):
        self.add_info(self.raise_descs, field)
    handle_raise = handle_raises

    def handle_seealso(self, field):
        self.seealsos.append(field)
    handle_see = handle_seealso

    def handle_note(self, field):
        self.notes.append(field)

    def handle_author(self, field):
        self.authors.append(field)

    def handle_since(self, field):
        self.sinces.append(field)

    def handleUnknownField(self, field):
        self.obj.system.msg(
            'epydoc2stan',
            'found unknown field on %r: %r'%(self.obj.fullName(), field),
            thresh=-1)
        self.add_info(self.unknowns, field)

    def handle(self, field):
        m = getattr(self, 'handle_' + field.tag, self.handleUnknownField)
        m(field)

    def resolve_types(self):
        for pd in self.parameter_descs:
            if pd.name in self.types:
                pd.type = self.types[pd.name]

    def format(self):
        r = []

        r.append(format_desc_list('Parameters', self.parameter_descs, 'Parameters'))
        if self.return_desc:
            r.append(tags.tr(class_="fieldStart")(tags.td(class_="fieldName")('Returns'),
                               tags.td(colspan="2")(self.return_desc.format())))
        r.append(format_desc_list("Raises", self.raise_descs, "Raises"))
        for s, p, l in (('Author', 'Authors', self.authors),
                        ('See Also', 'See Also', self.seealsos),
                        ('Present Since', 'Present Since', self.sinces),
                        ('Note', 'Notes', self.notes)):
            r.append(format_field_list(self.obj, s, l, p))
        unknowns = {}
        unknownsinorder = []
        for fieldinfo in self.unknowns:
            tag = fieldinfo.kind
            if tag in unknowns:
                unknowns[tag].append(fieldinfo)
            else:
                unknowns[tag] = [fieldinfo]
                unknownsinorder.append(unknowns[tag])
        for fieldlist in unknownsinorder:
            label = "Unknown Field: " + fieldlist[0].kind
            r.append(format_desc_list(label, fieldlist, label))

        return tags.table(class_='fieldTable')(r)


def reportErrors(obj, errs):
    if errs and obj.fullName() not in obj.system.docstring_syntax_errors:
        obj.system.docstring_syntax_errors.add(obj.fullName())

        for err in errs:
            lineno_offset = 0
            if isinstance(err, string_types):
                descr = err
            elif isinstance(err, ParseError):
                descr = err.descr()
                lineno_offset = err.linenum() - 1
            else:
                raise TypeError(type(err).__name__)

            obj.report(
                'bad docstring: ' + descr,
                lineno_offset=lineno_offset,
                section='docstring'
                )


def parse_docstring(obj, doc, source):
    """Parse a docstring.
    @rtype: L{ParsedDocstring}
    """

    parser = get_parser(obj)
    errs = []
    try:
        pdoc = parser(doc, errs)
    except Exception as e:
        errs.append('%s: %s' % (e.__class__.__name__, e))
        pdoc = None
    if pdoc is None:
        pdoc = pydoctor.epydoc.markup.plaintext.parse_docstring(doc, errs)
    if errs:
        reportErrors(source, errs)
    return pdoc


def format_docstring(obj):
    """Generate an HTML representation of a docstring"""

    doc, source = get_docstring(obj)

    # Use cached or split version if possible.
    pdoc = getattr(obj, 'parsed_docstring', None)

    if pdoc is None:
        if doc is None:
            return tags.div(class_='undocumented')("Undocumented")
        pdoc = parse_docstring(obj, doc, source)
        obj.parsed_docstring = pdoc
    elif source is None:
        # A split field is documented by its parent.
        source = obj.parent

    try:
        stan = pdoc.to_stan(_EpydocLinker(source))
    except Exception as e:
        errs = ['%s: %s' % (e.__class__.__name__, e)]
        if doc is None:
            stan = tags.p(class_="undocumented")('Broken description')
        else:
            pdoc_plain = pydoctor.epydoc.markup.plaintext.parse_docstring(doc, errs)
            stan = pdoc_plain.to_stan(_EpydocLinker(source))
        reportErrors(source, errs)

    content = [stan] if stan.tagName else stan.children
    fields = pdoc.fields
    s = tags.div(*content)
    if fields:
        fh = FieldHandler(obj)
        for field in fields:
            fh.handle(Field(field, obj))
        fh.resolve_types()
        s(fh.format())
    return s


def format_summary(obj):
    """Generate an shortened HTML representation of a docstring."""

    doc, source = get_docstring(obj)
    if doc is None:
        # Attributes can be documented as fields in their parent's docstring.
        if isinstance(obj, model.Attribute):
            pdoc = getattr(obj, 'parsed_docstring', None)
        else:
            pdoc = None
        if pdoc is None:
            return format_undocumented(obj)
        source = obj.parent
    else:
        # Use up to three first non-empty lines of doc string as summary.
        lines = itertools.dropwhile(lambda line: not line.strip(),
                                    doc.split('\n'))
        lines = itertools.takewhile(lambda line: line.strip(), lines)
        lines = [ line.strip() for line in lines ]
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


def format_undocumented(obj):
    """Generate an HTML representation for an object lacking a docstring."""
    subdocstrings = {}
    subcounts = {}
    for subob in obj.contents.values():
        k = subob.kind.lower()
        subcounts[k] = subcounts.get(k, 0) + 1
        if subob.docstring is not None:
            subdocstrings[k] = subdocstrings.get(k, 0) + 1
    if isinstance(obj, model.Package):
        subcounts['module'] -= 1
    if subdocstrings:
        plurals = {'class': 'classes'}
        text = "No %s docstring; %s documented" % (
            obj.kind.lower(),
            ', '.join(
                "%s/%s %s" % (subdocstrings.get(k, 0), subcounts[k],
                              plurals.get(k, k + 's'))
                for k in sorted(subcounts)
                )
            )
    else:
        text = "Undocumented"
    return tags.span(class_='undocumented')(text)


def type2stan(obj):
    parsed_type = get_parsed_type(obj)
    if parsed_type is None:
        return None
    else:
        return parsed_type.to_stan(_EpydocLinker(obj))

def get_parsed_type(obj):
    parsed_type = getattr(obj, 'parsed_type', None)
    if parsed_type is not None:
        return parsed_type

    annotation = getattr(obj, 'annotation', None)
    if annotation is not None:
        return AnnotationDocstring(annotation)

    return None


class AnnotationDocstring(ParsedDocstring):

    def __init__(self, annotation):
        ParsedDocstring.__init__(self, ())
        self.annotation = annotation

    def to_stan(self, docstring_linker):
        src = astor.to_source(self.annotation).strip()
        return tags.code(src)


field_name_to_human_name = {
    'ivar': 'Instance Variable',
    'cvar': 'Class Variable',
    'var': 'Variable',
    }


def extract_fields(obj):
    doc, source = get_docstring(obj)
    if doc is None:
        return

    pdoc = parse_docstring(obj, doc, source)
    obj.parsed_docstring = pdoc

    for field in pdoc.fields:
        tag = field.tag()
        if tag in ['ivar', 'cvar', 'var', 'type']:
            arg = field.arg()
            if arg is None:
                obj.report("Missing field name in @%s" % (tag,),
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
