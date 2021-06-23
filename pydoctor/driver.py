"""The command-line parsing and entry point."""

from argparse import SUPPRESS, ArgumentParser, Namespace
from pathlib import Path
from typing import Iterator, TYPE_CHECKING, Sequence, Type, TypeVar, cast
import functools
import datetime
import os
import sys
import warnings
from inspect import getmodulename

from pydoctor import model, zopeinterface, __version__
from pydoctor.templatewriter import IWriter, TemplateLookup, UnsupportedTemplateVersion
from pydoctor.sphinx import (MAX_AGE_HELP, USER_INTERSPHINX_CACHE,
                             SphinxInventoryWriter, prepareCache)

if TYPE_CHECKING:
    from typing_extensions import NoReturn
else:
    NoReturn = None

# On Python 3.7+, use importlib.resources from the standard library.
# On older versions, a compatibility package must be installed from PyPI.
try:
    import importlib.resources as importlib_resources
except ImportError:
    if not TYPE_CHECKING:
        import importlib_resources

BUILDTIME_FORMAT = '%Y-%m-%d %H:%M:%S'
BUILDTIME_FORMAT_HELP = 'YYYY-mm-dd HH:MM:SS'

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

def parse_path(value: str, opt: str) -> Path:
    """Parse a str path to a L{Path} object
    using L{resolve_path()}.
    """
    try:
        return resolve_path(value)
    except Exception as ex:
        raise error(f"invalid path: {ex} in option {opt}.")

def get_supported_docformats() -> Iterator[str]:
    """
    Get the list of currently supported docformat.
    """
    for fileName in importlib_resources.contents('pydoctor.epydoc.markup'):
        moduleName = getmodulename(fileName)
        if moduleName is None or moduleName == '__init__':
            continue
        else:
            yield moduleName


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog='pydoctor',
        description="API doc generator.",
        usage="usage: pydoctor [options] SOURCEPATH...")
    # parser.add_argument(
    #     '-c', '--config', dest='configfile',
    #     help=("Use config from this file (any command line"
    #           "options override settings from the file)."))
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument(
        '--system-class', dest='systemclass',
        help=("A dotted name of the class to use to make a system."))
    parser.add_argument(
        '--project-name', dest='projectname',
        help=("The project name, shown at the top of each HTML page."))
    parser.add_argument(
        '--project-version',
        dest='projectversion',
        default='',
        metavar='VERSION',
        help=(
            "The version of the project for which the API docs are generated. "
            "Defaults to empty string."
            ))
    parser.add_argument(
        '--project-url', dest='projecturl',
        help=("The project url, appears in the html if given."))
    parser.add_argument(
        '--project-base-dir', dest='projectbasedirectory',  
        type=functools.partial(parse_path, opt="--project-base-dir"),
        help=("Path to the base directory of the project.  Source links "
              "will be computed based on this value."))
    parser.add_argument(
        '--testing', dest='testing', action='store_true',
        help=("Don't complain if the run doesn't have any effects."))
    parser.add_argument(
        '--pdb', dest='pdb', action='store_true',
        help=("Like py.test's --pdb."))
    parser.add_argument(
        '--make-html', action='store_true', dest='makehtml',
        default=MAKE_HTML_DEFAULT, help=("Produce html output."))
    parser.add_argument(
        '--make-intersphinx', action='store_true', dest='makeintersphinx',
        default=False, help=("Produce (only) the objects.inv intersphinx file."))
    parser.add_argument(
        '--add-package', action='append', dest='packages',
        metavar='PACKAGEDIR', default=[], help=SUPPRESS)
    parser.add_argument(
        '--add-module', action='append', dest='modules',
        metavar='MODULE', default=[], help=SUPPRESS)
    parser.add_argument(
        '--prepend-package', action='store', dest='prependedpackage',
        help=("Pretend that all packages are within this one.  "
              "Can be used to document part of a package."))
    _docformat_choices = get_supported_docformats()
    parser.add_argument(
        '--docformat', dest='docformat', action='store', default='epytext',
        choices=list(_docformat_choices),
        help=("Format used for parsing docstrings. "
             f"Supported values: {', '.join(_docformat_choices)}"))
    parser.add_argument(
        '--template-dir',
        dest='templatedir',
        help=("Directory containing custom HTML templates."),
    )
    parser.add_argument(
        '--html-subject', dest='htmlsubjects', action='append',
        help=("The fullName of objects to generate API docs for"
              " (generates everything by default)."))
    parser.add_argument(
        '--html-summary-pages', dest='htmlsummarypages',
        action='store_true', default=False,
        help=("Only generate the summary pages."))
    parser.add_argument(
        '--html-output', dest='htmloutput', default='apidocs',
        help=("Directory to save HTML files to (default 'apidocs')"))
    parser.add_argument(
        '--html-writer', dest='htmlwriter',
        help=("Dotted name of HTML writer class to use (default "
              "'pydoctor.templatewriter.TemplateWriter')."))
    parser.add_argument(
        '--html-viewsource-base', dest='htmlsourcebase',
        help=("This should be the path to the trac browser for the top "
              "of the svn checkout we are documenting part of."))
    parser.add_argument(
        '--buildtime', dest='buildtime',
        help=("Use the specified build time over the current time. "
              f"Format: {BUILDTIME_FORMAT_HELP}"))
    parser.add_argument(
        '-W', '--warnings-as-errors', action='store_true',
        dest='warnings_as_errors', default=False,
        help=("Return exit code 3 on warnings."))
    parser.add_argument(
        '-v', '--verbose', action='count', dest='verbosity',
        default=0,
        help=("Be noisier.  Can be repeated for more noise."))
    parser.add_argument(
        '-q', '--quiet', action='count', dest='quietness',
        default=0,
        help=("Be quieter."))
    parser.add_argument(
        '--introspect-c-modules', default=False, action='store_true',
        help=("Import and introspect any C modules found."))

    parser.add_argument(
        '--intersphinx', action='append', dest='intersphinx',
        metavar='URL_TO_OBJECTS.INV', default=[],
        help=(
            "Use Sphinx objects inventory to generate links to external "
            "documentation. Can be repeated."))

    parser.add_argument(
        '--enable-intersphinx-cache',
        dest='enable_intersphinx_cache_deprecated',
        action='store_true',
        default=False,
        help=SUPPRESS
    )
    parser.add_argument(
        '--disable-intersphinx-cache',
        dest='enable_intersphinx_cache',
        action='store_false',
        default=True,
        help="Disable Intersphinx cache."
    )
    parser.add_argument(
        '--intersphinx-cache-path',
        dest='intersphinx_cache_path',
        default=USER_INTERSPHINX_CACHE,
        help="Where to cache intersphinx objects.inv files."
    )
    parser.add_argument(
        '--clear-intersphinx-cache',
        dest='clear_intersphinx_cache',
        action='store_true',
        default=False,
        help=("Clear the Intersphinx cache "
              "specified by --intersphinx-cache-path."),
    )
    parser.add_argument(
        '--intersphinx-cache-max-age',
        dest='intersphinx_cache_max_age',
        default='1d',
        help=MAX_AGE_HELP,
    )

    parser.add_argument(
        'sourcepath', metavar='SOURCEPATH', 
        help=("Path to python modules/packages to document."),
        nargs="*", default=[], 
    )

    return parser

def parse_args(args: Sequence[str]) -> Namespace:
    parser = get_parser()
    options = parser.parse_args(args)
    options.verbosity -= options.quietness

    _warn_deprecated_options(options)

    return options


def _warn_deprecated_options(options: Namespace) -> None:
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
    options = parse_args(args)

    exitcode = 0

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
        modules = options.sourcepath + options.modules + options.packages

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

        if modules:
            prependedpackage = None
            if options.prependedpackage:
                for m in options.prependedpackage.split('.'):
                    prependedpackage = system.Package(
                        system, m, prependedpackage)
                    system.addObject(prependedpackage)
                    initmodule = system.Module(system, '__init__', prependedpackage)
                    system.addObject(initmodule)
            added_paths = set()
            for mod_path in modules:
                path = resolve_path(mod_path)
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

        if options.makehtml:
            options.makeintersphinx = True
            from pydoctor import templatewriter
            if options.htmlwriter:
                writerclass = findClassFromDottedName(
                    options.htmlwriter, '--html-writer', IWriter)
            else:
                writerclass = templatewriter.TemplateWriter

            system.msg('html', 'writing html to %s using %s.%s'%(
                options.htmloutput, writerclass.__module__,
                writerclass.__name__))

            writer: IWriter
            # Handle custom HTML templates
            if system.options.templatedir:
                custom_lookup = TemplateLookup()
                try:
                    custom_lookup.add_templatedir(
                        Path(system.options.templatedir))
                except UnsupportedTemplateVersion as e:
                    error(str(e))

                try:
                    # mypy error: Cannot instantiate abstract class 'IWriter'
                    writer = writerclass(options.htmloutput, # type: ignore[abstract]
                        template_lookup=custom_lookup)
                except TypeError:
                    # Custom class does not accept 'template_lookup' argument.
                    writer = writerclass(options.htmloutput) # type: ignore[abstract]
                    warnings.warn(f"Writer '{writerclass.__name__}' does not support "
                        "HTML template customization with --template-dir.")
            else:
                writer = writerclass(options.htmloutput) # type: ignore[abstract]

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
