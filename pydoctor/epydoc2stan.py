"""
Convert epydoc markup into renderable content.
"""

from __future__ import print_function

import astor

from importlib import import_module
import inspect
import itertools
import os
import sys

from pydoctor import model
from six.moves import builtins
from six.moves.urllib.parse import quote
from twisted.web.template import tags
from pydoctor.epydoc.markup import DocstringLinker
from pydoctor.epydoc.markup.epytext import Element, ParsedEpytextDocstring
import pydoctor.epydoc.markup.plaintext

try:
    import exceptions
except ImportError:
    exceptions = builtins


STDLIB_DIR = os.path.dirname(os.__file__)
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
        if doc is not None:
            if doc.strip():
                doc = inspect.cleandoc(doc)
            else:
                # Treat empty docstring as undocumented.
                doc = None
            return doc, source
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

    def _objLink(self, obj, prettyID):
        if obj.documentation_location is model.DocLocation.PARENT_PAGE:
            p = obj.parent
            if isinstance(p, model.Module) and p.name == '__init__':
                p = p.parent
            linktext = link(p) + '#' + quote(obj.name)
        elif obj.documentation_location is model.DocLocation.OWN_PAGE:
            linktext = link(obj)
        else:
            raise AssertionError(
                "Unknown documentation_location: %s" % obj.documentation_location)
        return tags.a(tags.code(prettyID), href=linktext)

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
            self.obj.system.msg(
                "translate_identifier_xref", "%s:%s ambiguous ref to %s, could be %s" % (
                    self.obj.fullName(), self.obj.linenumber, name,
            ', '.join([ob.fullName() for ob in potential_targets])),
                thresh=-1)
        return None

    def look_for_intersphinx(self, name):
        """
        Return link for `name` based on intersphinx inventory.

        Return None if link is not found.
        """
        return self.obj.system.intersphinx.getLink(name)

    def translate_identifier_xref(self, fullID, prettyID):
        """Figure out what ``L{fullID}`` should link to.

        There is a lot of DWIM here.  The order goes:

          1. Check if fullID refers to an object by Python name resolution in
             our context.

          2. Walk up the object tree and see if fullID refers to an object by
             Python name resolution in each context.

          3. Check if fullID is the fullName of an object.

          4. Check to see if fullID names a builtin or standard library
             module.

          4. Walk up the object tree again and see if fullID refers to an
             object in an "uncle" object.  (So if p.m1 has a class C, the
             docstring for p.m2 can say L{C} to refer to the class in m1).  If
             at any level fullID refers to more than one object, complain.

          5. Examine every module and package in the system and see if fullID
             names an object in each one.  Again, if more than one object is
             found, complain.

        """
        src = self.obj
        while src is not None:
            target = src.resolveName(fullID)
            if target is not None:
                return self._objLink(target, prettyID)
            src = src.parent
        target = self.obj.system.objForFullName(fullID)
        if target is not None:
            return self._objLink(target, prettyID)
        fullerID = self.obj.expandName(fullID)
        linktext = stdlib_doc_link_for_name(fullerID)
        if linktext is not None:
            return tags.a(tags.code(prettyID), href=linktext)
        src = self.obj
        while src is not None:
            target = self.look_for_name(fullID, src.contents.values())
            if target is not None:
                return self._objLink(target, prettyID)
            src = src.parent
        target = self.look_for_name(fullID, itertools.chain(
            self.obj.system.objectsOfType(model.Module),
            self.obj.system.objectsOfType(model.Package)))
        if target is not None:
            return self._objLink(target, prettyID)

        target = self.look_for_intersphinx(fullerID)
        if not target:
            # FIXME: https://github.com/twisted/pydoctor/issues/125
            # expandName is unreliable so in the case fullerID fails, we
            # try our luck with fullID.
            target = self.look_for_intersphinx(fullID)
        if target:
            return tags.a(tags.code(prettyID), href=target)
        if fullID != fullerID:
            self.obj.system.msg(
                "translate_identifier_xref", "%s:%s invalid ref to '%s' "
                "resolved as '%s'" % (
                    self.obj.fullName(), self.obj.linenumber, fullID, fullerID),
                thresh=-1)
        return tags.code(prettyID)


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
        self.body = field.body().to_stan(_EpydocLinker(obj))

    def __repr__(self):
        r = repr(self.body)
        if len(r) > 25:
            r = r[:20] + '...' + r[-2:]
        return "<%s %r %r %s>"%(self.__class__.__name__,
                             self.tag, self.arg, r)

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
    for err in errs:
        if isinstance(err, str):
            linenumber = '??'
            descr = err
        else:
            linenumber = obj.linenumber + err.linenum()
            descr = err._descr
        obj.system.msg(
            'epydoc2stan2',
            '%s:%s epytext error %r' % (obj.fullName(), linenumber, descr))
    if errs and obj.fullName() not in obj.system.epytextproblems:
        obj.system.epytextproblems.append(obj.fullName())
        obj.system.msg('epydoc2stan',
                       'epytext error in %s'%(obj,), thresh=1)
        p = lambda m:obj.system.msg('epydoc2stan', m, thresh=2)
        for i, l in enumerate(obj.docstring.splitlines()):
            p("%4s"%(i+1)+' '+l)
        for err in errs:
            p(err)


def doc2stan(obj, summary=False):
    """Generate an HTML representation of a docstring"""
    if getattr(obj, 'parsed_docstring', None) is not None:
        return obj.parsed_docstring.to_stan(_EpydocLinker(obj))
    doc, source = get_docstring(obj)
    if doc is None:
        return format_undocumented(obj, summary)
    if summary:
        # Use up to three first non-empty lines of doc string as summary.
        lines = itertools.dropwhile(lambda line: not line.strip(),
                                    doc.split('\n'))
        lines = itertools.takewhile(lambda line: line.strip(), lines)
        lines = [ line.strip() for line in lines ]
        if len(lines) > 3:
            return tags.span(class_="undocumented")('No summary')
        else:
            doc = ' '.join(lines)

    parse_docstring = get_parser(obj)
    errs = []
    try:
        pdoc = parse_docstring(doc, errs)
    except Exception as e:
        errs.append('%s: %s' % (e.__class__.__name__, e))
        pdoc = None
    if pdoc is None:
        pdoc = pydoctor.epydoc.markup.plaintext.parse_docstring(doc, errs)
    fields = pdoc.fields
    try:
        stan = pdoc.to_stan(_EpydocLinker(source))
    except Exception as e:
        errs.append('%s: %s' % (e.__class__.__name__, e))
        pdoc = pydoctor.epydoc.markup.plaintext.parse_docstring(doc, errs)
        stan = pdoc.to_stan(_EpydocLinker(source))
    content = [stan] if stan.tagName else stan.children
    if errs:
        reportErrors(source, errs)

    if summary:
        if content and content[0].tagName == 'p':
            content = content[0].children
        s = tags.span(*content)
    else:
        s = tags.div(*content)
        if fields:
            fh = FieldHandler(obj)
            for field in fields:
                fh.handle(Field(field, obj))
            fh.resolve_types()
            s(fh.format())
    return s


def format_undocumented(obj, summary):
    """Generate an HTML representation for an object lacking a docstring."""
    text = "Undocumented"
    subdocstrings = {}
    subcounts = {}
    for subob in obj.contents.values():
        k = subob.kind.lower()
        subcounts[k] = subcounts.get(k, 0) + 1
        if subob.docstring is not None:
            subdocstrings[k] = subdocstrings.get(k, 0) + 1
    if isinstance(obj, model.Package):
        subcounts["module"] -= 1
    if subdocstrings:
        plurals = {'class': 'classes'}
        text = "No %s docstring" % obj.kind.lower()
        if summary:
            u = []
            for k in sorted(subcounts):
                u.append("%s/%s %s" % (subdocstrings.get(k, 0), subcounts[k],
                                       plurals.get(k, k + 's')))
            text += '; ' + ', '.join(u) + " documented"
    if summary:
        return tags.span(class_="undocumented")(text)
    else:
        return tags.div(class_="undocumented")(text)


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
        src = astor.to_source(annotation).strip()
        return ParsedEpytextDocstring(
            Element('epytext',
                Element('para',
                    Element('code', src),
                    inline=True
                    )
                ),
            ()
            )

    return None


field_name_to_human_name = {
    'ivar': 'Instance Variable',
    'cvar': 'Class Variable',
    'var': 'Variable',
    }


def extract_fields(obj):
    doc, source = get_docstring(obj)
    if doc is None:
        return
    parse_docstring = get_parser(obj)
    try:
        pdoc = parse_docstring(doc, [])
    except Exception:
        return
    for field in pdoc.fields:
        tag = field.tag()
        if tag in ['ivar', 'cvar', 'var', 'type']:
            arg = field.arg()
            if arg is None:
                obj.system.msg('epydoc2stan', '%s: Missing field name in @%s'
                               % (obj.fullName(), tag))
                continue
            attrobj = obj.contents.get(arg)
            if attrobj is None:
                attrobj = obj.system.Attribute(obj.system, arg, None, obj)
                attrobj.kind = None
                obj.system.addObject(attrobj)
            if tag == 'type':
                attrobj.parsed_type = field.body()
            else:
                attrobj.parsed_docstring = field.body()
                attrobj.kind = field_name_to_human_name[tag]
