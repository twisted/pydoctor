"""The command-line parsing and entry point."""

from optparse import SUPPRESS_HELP, Option, OptionParser, OptionValueError, Values
from pathlib import Path
from typing import TYPE_CHECKING, List, Sequence, Tuple, Type, TypeVar, cast
import datetime
import os
import sys

from pydoctor.themes import get_themes
from pydoctor import model, zopeinterface, __version__
from pydoctor.templatewriter import IWriter, TemplateError, TemplateLookup
from pydoctor.sphinx import (MAX_AGE_HELP, USER_INTERSPHINX_CACHE,
                             SphinxInventoryWriter, prepareCache)
from pydoctor.epydoc.markup import get_supported_docformats

if TYPE_CHECKING:
    from typing_extensions import NoReturn
else:
    NoReturn = None

# In newer Python versions, use importlib.resources from the standard library.
# On older versions, a compatibility package must be installed from PyPI.
if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

BUILDTIME_FORMAT = '%Y-%m-%d %H:%M:%S'

def error(msg: str, *args: object) -> NoReturn:
    if args:
        msg = msg%args
    print(msg, file=sys.stderr)
    sys.exit(1)

T = TypeVar('T')

def findClassFromDottedName(
        dottedname: str,
        optionname: str,
        base_class: Type[T]
        ) -> Type[T]:
    """
    Looks up a class by full name.
    Watch out, prints a message and SystemExits on error!
    """
    if '.' not in dottedname:
        error("%stakes a dotted name", optionname)
    parts = dottedname.rsplit('.', 1)
    try:
        mod = __import__(parts[0], globals(), locals(), parts[1])
    except ImportError:
        error("could not import module %s", parts[0])
    try:
        cls = getattr(mod, parts[1])
    except AttributeError:
        error("did not find %s in module %s", parts[1], parts[0])
    if not issubclass(cls, base_class):
        error("%s is not a subclass of %s", cls, base_class)
    return cast(Type[T], cls)

MAKE_HTML_DEFAULT = object()

def resolve_path(path: str) -> Path:
    """Parse a given path string to a L{Path} object.

    The path is converted to an absolute path, as required by
    L{System.setSourceHref()}.
    The path does not need to exist.
    """

    # We explicitly make the path relative to the current working dir
    # because on Windows resolve() does not produce an absolute path
    # when operating on a non-existing path.
    return Path(Path.cwd(), path).resolve()

def parse_path(option: Option, opt: str, value: str) -> Path:
    """Parse a path value given to an option to a L{Path} object
    using L{resolve_path()}.
    """
    try:
        return resolve_path(value)
    except Exception as ex:
        raise OptionValueError(f"{opt}: invalid path: {ex}")

class CustomOption(Option):
    TYPES = Option.TYPES + ("path",)
    TYPE_CHECKER = dict(Option.TYPE_CHECKER, path=parse_path)

def getparser() -> OptionParser:
    parser = OptionParser(
        option_class=CustomOption, version=__version__,
        usage="usage: %prog [options] SOURCEPATH...")
    parser.add_option(
        '-c', '--config', dest='configfile',
        help=("Use config from this file (any command line"
              "options override settings from the file)."))
    parser.add_option(
        '--system-class', dest='systemclass',
        help=("A dotted name of the class to use to make a system."))
    parser.add_option(
        '--project-name', dest='projectname',
        help=("The project name, shown at the top of each HTML page."))
    parser.add_option(
        '--project-version',
        dest='projectversion',
        default='',
        metavar='VERSION',
        help=(
            "The version of the project for which the API docs are generated. "
            "Defaults to empty string."
            ))
    parser.add_option(
        '--project-url', dest='projecturl',
        help=("The project url, appears in the html if given."))
    parser.add_option(
        '--project-base-dir', dest='projectbasedirectory', type='path',
        help=("Path to the base directory of the project.  Source links "
              "will be computed based on this value."), metavar="PATH",)
    parser.add_option(
        '--testing', dest='testing', action='store_true',
        help=("Don't complain if the run doesn't have any effects."))
    parser.add_option(
        '--pdb', dest='pdb', action='store_true',
        help=("Like py.test's --pdb."))
    parser.add_option(
        '--make-html', action='store_true', dest='makehtml',
        default=MAKE_HTML_DEFAULT, help=("Produce html output."
            " Enabled by default if options '--testing' or '--make-intersphinx' are not specified. "))
    parser.add_option(
        '--make-intersphinx', action='store_true', dest='makeintersphinx',
        default=False, help=("Produce (only) the objects.inv intersphinx file."))
    parser.add_option(
        '--add-package', action='append', dest='packages',
        metavar='PACKAGEDIR', default=[], help=SUPPRESS_HELP)
    parser.add_option(
        '--add-module', action='append', dest='modules',
        metavar='MODULE', default=[], help=SUPPRESS_HELP)
    parser.add_option(
        '--prepend-package', action='store', dest='prependedpackage',
        help=("Pretend that all packages are within this one.  "
              "Can be used to document part of a package."))
    _docformat_choices = get_supported_docformats()
    parser.add_option(
        '--docformat', dest='docformat', action='store', default='epytext',
        type="choice", choices=list(_docformat_choices),
        help=("Format used for parsing docstrings. "
             f"Supported values: {', '.join(_docformat_choices)}"),
             metavar='FORMAT')
    parser.add_option(
        '--template-dir', action='append',
        dest='templatedir', default=[],
        help=("Directory containing custom HTML templates. Can repeat."),
        metavar='PATH',
    )
    parser.add_option('--theme', dest='theme', default='classic', 
        choices=list(get_themes()) ,
        help=("The theme to use when building your API documentation. "),
    )
    parser.add_option(
        '--html-subject', dest='htmlsubjects', action='append',
        help=("The fullName of objects to generate API docs for"
              " (generates everything by default)."),
              metavar='PACKAGE/MOD/CLASS')
    parser.add_option(
        '--html-summary-pages', dest='htmlsummarypages',
        action='store_true', default=False,
        help=("Only generate the summary pages."))
    parser.add_option(
        '--html-output', dest='htmloutput', default='apidocs',
        help=("Directory to save HTML files to (default 'apidocs')"), metavar='PATH',)
    parser.add_option(
        '--html-writer', dest='htmlwriter',
        help=("Dotted name of writer class to use (default "
              "'pydoctor.templatewriter.TemplateWriter')."), metavar='CLASS',)
    parser.add_option(
        '--html-viewsource-base', dest='htmlsourcebase',
        help=("This should be the path to the trac browser for the top "
              "of the svn checkout we are documenting part of."), metavar='URL',)
    parser.add_option(
        '--process-types', dest='processtypes', action='store_true', 
        help="Process the 'type' and 'rtype' fields, add links and inline markup automatically. "
            "This settings should not be enabled when using google or numpy docformat because the types are always processed by default.",)
    parser.add_option(
        '--buildtime', dest='buildtime',
        help=("Use the specified build time over the current time. "
              "Format: %s" % BUILDTIME_FORMAT), metavar='TIME')
    parser.add_option(
        '-W', '--warnings-as-errors', action='store_true',
        dest='warnings_as_errors', default=False,
        help=("Return exit code 3 on warnings."))
    parser.add_option(
        '-v', '--verbose', action='count', dest='verbosity',
        default=0,
        help=("Be noisier.  Can be repeated for more noise."))
    parser.add_option(
        '-q', '--quiet', action='count', dest='quietness',
        default=0,
        help=("Be quieter."))
    def verbose_about_callback(option: Option, opt_str: str, value: str, parser: OptionParser) -> None:
        assert parser.values is not None
        d = parser.values.verbosity_details
        d[value] = d.get(value, 0) + 1
    parser.add_option(
        '--verbose-about', metavar="stage", action="callback",
        type=str, default={}, dest='verbosity_details',
        callback=verbose_about_callback,
        help=("Be noiser during a particular stage of generation."))
    parser.add_option(
        '--introspect-c-modules', default=False, action='store_true',
        help=("Import and introspect any C modules found."))

    parser.add_option(
        '--intersphinx', action='append', dest='intersphinx',
        metavar='URL_TO_OBJECTS.INV', default=[],
        help=(
            "Use Sphinx objects inventory to generate links to external "
            "documentation. Can be repeated."))

    parser.add_option(
        '--enable-intersphinx-cache',
        dest='enable_intersphinx_cache_deprecated',
        action='store_true',
        default=False,
        help=SUPPRESS_HELP
    )
    parser.add_option(
        '--disable-intersphinx-cache',
        dest='enable_intersphinx_cache',
        action='store_false',
        default=True,
        help="Disable Intersphinx cache."
    )
    parser.add_option(
        '--intersphinx-cache-path',
        dest='intersphinx_cache_path',
        default=USER_INTERSPHINX_CACHE,
        help="Where to cache intersphinx objects.inv files.",
        metavar='PATH',
    )
    parser.add_option(
        '--clear-intersphinx-cache',
        dest='clear_intersphinx_cache',
        action='store_true',
        default=False,
        help=("Clear the Intersphinx cache "
              "specified by --intersphinx-cache-path."),
    )
    parser.add_option(
        '--intersphinx-cache-max-age',
        dest='intersphinx_cache_max_age',
        default='1d',
        help=MAX_AGE_HELP,
        metavar='DURATION',
    )
    parser.add_option(
        '--pyval-repr-maxlines', dest='pyvalreprmaxlines', default=7, type=int,
        help='Maxinum number of lines for a constant value representation. Use 0 for unlimited.')
    parser.add_option(
        '--pyval-repr-linelen', dest='pyvalreprlinelen', default=80, type=int,
        help='Maxinum number of caracters for a constant value representation line. Use 0 for unlimited.')

    parser.add_option(
        '--sidebar-expand-depth', metavar="INTEGER", action="store",
        type=int, default=2, dest='sidebarexpanddepth',
        help=("How many nested modules and classes should be expandable, "
              "first level is always expanded. (default: 2)"))

    parser.add_option(
        '--sidebar-toc-depth', metavar="INTEGER", action="store",
        type=int, default=6, dest='sidebartocdepth',
        help=("How many nested titles should be listed in the docstring TOC "
              "(default: 6)"))
    
    parser.add_option(
        '--no-sidebar', default=False, action='store_true', dest='nosidebar',
        help=("Do not generate the sidebar at all."))

    return parser

def readConfigFile(options: Values) -> None:
    # this is all a bit horrible.  rethink, then rewrite!
    for i, line in enumerate(open(options.configfile)):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            error("don't understand line %d of %s",
                  i+1, options.configfile)
        k, v = line.split(':', 1)
        k = k.strip()
        v = os.path.expanduser(v.strip())

        if not hasattr(options, k):
            error("invalid option %r on line %d of %s",
                  k, i+1, options.configfile)
        pre_v = getattr(options, k)
        if not pre_v:
            if isinstance(pre_v, list):
                setattr(options, k, v.split(','))
            else:
                setattr(options, k, v)
        else:
            if not isinstance(pre_v, list):
                setattr(options, k, v)

def parse_args(args: Sequence[str]) -> Tuple[Values, List[str]]:
    parser = getparser()
    options, args = parser.parse_args(args)
    options.verbosity -= options.quietness

    _warn_deprecated_options(options)

    return options, args


def _warn_deprecated_options(options: Values) -> None:
    """
    Check the CLI options and warn on deprecated options.
    """
    if options.enable_intersphinx_cache_deprecated:
        print("The --enable-intersphinx-cache option is deprecated; "
              "the cache is now enabled by default.",
              file=sys.stderr, flush=True)
    if options.modules:
        print("The --add-module option is deprecated; "
              "pass modules as positional arguments instead.",
              file=sys.stderr, flush=True)
    if options.packages:
        print("The --add-package option is deprecated; "
              "pass packages as positional arguments instead.",
              file=sys.stderr, flush=True)




def main(args: Sequence[str] = sys.argv[1:]) -> int:
    """
    This is the console_scripts entry point for pydoctor CLI.

    @param args: Command line arguments to run the CLI.
    """
    options, args = parse_args(args)

    exitcode = 0

    if options.configfile:
        readConfigFile(options)

    cache = prepareCache(clearCache=options.clear_intersphinx_cache,
                         enableCache=options.enable_intersphinx_cache,
                         cachePath=options.intersphinx_cache_path,
                         maxAge=options.intersphinx_cache_max_age)

    try:
        # step 1: make/find the system
        if options.systemclass:
            systemclass = findClassFromDottedName(
                options.systemclass, '--system-class', model.System)
        else:
            systemclass = zopeinterface.ZopeInterfaceSystem

        system = systemclass(options)
        system.fetchIntersphinxInventories(cache)

        if options.htmlsourcebase:
            if options.projectbasedirectory is None:
                error("you must specify --project-base-dir "
                      "when using --html-viewsource-base")
            system.sourcebase = options.htmlsourcebase

        # step 1.5: check that we're actually going to accomplish something here
        args = list(args) + options.modules + options.packages

        if options.makehtml == MAKE_HTML_DEFAULT:
            if not options.testing and not options.makeintersphinx:
                options.makehtml = True
            else:
                options.makehtml = False

        # Support source date epoch:
        # https://reproducible-builds.org/specs/source-date-epoch/
        try:
            system.buildtime = datetime.datetime.utcfromtimestamp(
                int(os.environ['SOURCE_DATE_EPOCH']))
        except ValueError as e:
            error(str(e))
        except KeyError:
            pass

        if options.buildtime:
            try:
                system.buildtime = datetime.datetime.strptime(
                    options.buildtime, BUILDTIME_FORMAT)
            except ValueError as e:
                error(str(e))

        # step 2: add any packages and modules

        if args:
            prependedpackage = None
            if options.prependedpackage:
                for m in options.prependedpackage.split('.'):
                    prependedpackage = system.Package(
                        system, m, prependedpackage)
                    system.addObject(prependedpackage)
                    initmodule = system.Module(system, '__init__', prependedpackage)
                    system.addObject(initmodule)
            added_paths = set()
            for arg in args:
                path = resolve_path(arg)
                if path in added_paths:
                    continue
                if options.projectbasedirectory is not None:
                    # Note: Path.is_relative_to() was only added in Python 3.9,
                    #       so we have to use this workaround for now.
                    try:
                        path.relative_to(options.projectbasedirectory)
                    except ValueError as ex:
                        error(f"Source path lies outside base directory: {ex}")
                if path.is_dir():
                    system.msg('addPackage', f"adding directory {path}")
                    if not (path / '__init__.py').is_file():
                        error(f"Source directory lacks __init__.py: {path}")
                    system.addPackage(path, prependedpackage)
                elif path.is_file():
                    system.msg('addModuleFromPath', f"adding module {path}")
                    system.addModuleFromPath(path, prependedpackage)
                elif path.exists():
                    error(f"Source path is neither file nor directory: {path}")
                else:
                    error(f"Source path does not exist: {path}")
                added_paths.add(path)
        else:
            error("No source paths given.")

        # step 3: move the system to the desired state

        if system.options.projectname is None:
            name = '/'.join(system.root_names)
            system.msg('warning', f"Guessing '{name}' for project name.", thresh=0)
            system.projectname = name
        else:
            system.projectname = system.options.projectname

        system.process()

        # step 4: make html, if desired

        # check if sidebar related arguments are valid
        if system.options.sidebarexpanddepth < 1:
            system._warning(None, "Invalid --sidebar-expand-depth value", detail='The value of --sidebar-expand-depth option should be greater or equal to 1, '
                                'to suppress sidebar generation all together: use --no-sidebar')
            system.options.sidebarexpanddepth = 1
        if system.options.sidebartocdepth < 0:
            system._warning(None, "Invalid --sidebar-toc-depth value", detail='The value of --sidebar-toc-depth option should be greater or equal to 0, '
                                'to suppress sidebar generation all together: use --no-sidebar')
            system.options.sidebartocdepth = 0

        if options.makehtml:
            options.makeintersphinx = True
            from pydoctor import templatewriter
            if options.htmlwriter:
                writerclass = findClassFromDottedName(
                    # ignore mypy error: Only concrete class can be given where "Type[IWriter]" is expected
                    options.htmlwriter, '--html-writer', IWriter) # type: ignore[misc]
            else:
                writerclass = templatewriter.TemplateWriter

            system.msg('html', 'writing html to %s using %s.%s'%(
                options.htmloutput, writerclass.__module__,
                writerclass.__name__))

            writer: IWriter
            
            # Always init the writer with the 'base' set of templates at least.
            template_lookup = TemplateLookup(
                                importlib_resources.files('pydoctor.themes') / 'base')
            
            # Handle theme selection, 'classic' by default.
            if system.options.theme != 'base':
                template_lookup.add_templatedir(
                    importlib_resources.files('pydoctor.themes') / system.options.theme)


            # Handle custom HTML templates
            if system.options.templatedir:
                try:
                    for t in system.options.templatedir:
                        template_lookup.add_templatedir(Path(t))
                except TemplateError  as e:
                    error(str(e))

            build_directory = Path(options.htmloutput)

            writer = writerclass(build_directory, template_lookup=template_lookup)

            writer.prepOutputDirectory()

            subjects: Sequence[model.Documentable] = ()
            if options.htmlsubjects:
                subjects = [system.allobjects[fn] for fn in options.htmlsubjects]
            else:
                writer.writeSummaryPages(system)
                if not options.htmlsummarypages:
                    subjects = system.rootobjects
            writer.writeIndividualFiles(subjects)
            if system.docstring_syntax_errors:
                def p(msg: str) -> None:
                    system.msg('docstring-summary', msg, thresh=-1, topthresh=1)
                p("these %s objects' docstrings contain syntax errors:"
                  %(len(system.docstring_syntax_errors),))
                exitcode = 2
                for fn in sorted(system.docstring_syntax_errors):
                    p('    '+fn)

        if system.violations and options.warnings_as_errors:
            # Update exit code if the run has produced warnings.
            exitcode = 3

        if options.makeintersphinx:
            if not options.makehtml:
                subjects = system.rootobjects
            # Generate Sphinx inventory.
            sphinx_inventory = SphinxInventoryWriter(
                logger=system.msg,
                project_name=system.projectname,
                project_version=system.options.projectversion,
                )
            if not os.path.exists(options.htmloutput):
                os.makedirs(options.htmloutput)
            sphinx_inventory.generate(
                subjects=subjects,
                basepath=options.htmloutput,
                )
    except:
        if options.pdb:
            import pdb
            pdb.post_mortem(sys.exc_info()[2])
        raise
    return exitcode
