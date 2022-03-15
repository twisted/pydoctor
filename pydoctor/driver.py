"""The command-line parsing and entry point."""

from argparse import SUPPRESS, Namespace
from configargparse import ArgumentParser, ConfigparserConfigFileParser
from typing import Any, Sequence, TypeVar
import datetime
import os
import sys
from pathlib import Path

from pydoctor.themes import get_themes
from pydoctor.utils import error
from pydoctor import model, __version__
from pydoctor.templatewriter import IWriter, TemplateLookup, TemplateError
from pydoctor.epydoc.markup import get_supported_docformats
from pydoctor.sphinx import (MAX_AGE_HELP, USER_INTERSPHINX_CACHE,
                             SphinxInventoryWriter, prepareCache)

# In newer Python versions, use importlib.resources from the standard library.
# On older versions, a compatibility package must be installed from PyPI.
if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

BUILDTIME_FORMAT = '%Y-%m-%d %H:%M:%S'
BUILDTIME_FORMAT_HELP = 'YYYY-mm-dd HH:MM:SS'

T = TypeVar('T')

def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog='pydoctor',
        description="API doc generator.",
        usage="pydoctor [options] SOURCEPATH...", 
        default_config_files=['./pydoctor.ini'],
        config_file_parser_class=ConfigparserConfigFileParser)
    parser.add_argument(
        '-c', '--config', is_config_file=True,
        help=("Load config from this file (any command line"
              "options override settings from the file)."), metavar="PATH",)
    parser.add_argument(
        '--project-name', dest='projectname', metavar="PROJECTNAME",
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
        '--project-url', dest='projecturl', metavar="URL", 
        help=("The project url, appears in the html if given."))
    parser.add_argument(
        '--project-base-dir', dest='projectbasedirectory',  
        help=("Path to the base directory of the project.  Source links "
              "will be computed based on this value."), metavar="PATH")
    parser.add_argument(
        '--testing', dest='testing', action='store_true',
        help=("Don't complain if the run doesn't have any effects."))
    parser.add_argument(
        '--pdb', dest='pdb', action='store_true',
        help=("Like py.test's --pdb."))
    parser.add_argument(
        '--make-html', action='store_true', dest='makehtml',
        default=model.Options.MAKE_HTML_DEFAULT, help=("Produce html output."
            " Enabled by default if options '--testing' or '--make-intersphinx' are not specified. "))
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
              "Can be used to document part of a package."), metavar='PACKAGE')
    _docformat_choices = list(get_supported_docformats())
    parser.add_argument(
        '--docformat', dest='docformat', action='store', default='epytext',
        choices=_docformat_choices,
        help=("Format used for parsing docstrings. "
             f"Supported values: {', '.join(_docformat_choices)}"), metavar='FORMAT')
    parser.add_argument('--theme', dest='theme', default='classic', 
        choices=list(get_themes()) ,
        help=("The theme to use when building your API documentation. "),
        metavar='THEME', 
    )
    parser.add_argument(
        '--template-dir', action='append',
        dest='templatedir', default=[],
        help=("Directory containing custom HTML templates. Can be repeated."),
        metavar='PATH',
    )
    parser.add_argument(
        '--privacy', action='append', dest='privacy',
        metavar='<PRIVACY>:<PATTERN>', default=[], 
        help=("Set the privacy of specific objects when default rules doesn't fit the use case. "
              "Format: '<PRIVACY>:<PATTERN>', where <PRIVACY> can be one of 'PUBLIC', 'PRIVATE' or "
              "'HIDDEN' (case insensitive), and <PATTERN> is fnmatch-like pattern matching objects fullName. "
              "Pattern added last have priority over a pattern added before, but an exact match wins over a fnmatch. Can be repeated."))
    parser.add_argument(
        '--html-subject', dest='htmlsubjects', action='append',
        help=("The fullName of objects to generate API docs for"
              " (generates everything by default)."), metavar='PACKAGE/MOD/CLASS')
    parser.add_argument(
        '--html-summary-pages', dest='htmlsummarypages',
        action='store_true', default=False,
        help=("Only generate the summary pages."))
    parser.add_argument(
        '--html-output', dest='htmloutput', default='apidocs',
        help=("Directory to save HTML files to (default 'apidocs')"), metavar='PATH')
    parser.add_argument(
        '--html-writer', dest='htmlwriter',
        default='pydoctor.templatewriter.TemplateWriter', 
        help=("Dotted name of HTML writer class to use (default 'pydoctor.templatewriter.TemplateWriter')."), 
        metavar='CLASS', )
    parser.add_argument(
        '--html-viewsource-base', dest='htmlsourcebase', 
        help=("This should be the path to the trac browser for the top "
              "of the svn checkout we are documenting part of."), metavar='URL',)
    parser.add_argument(
        '--buildtime', dest='buildtime',
        help=("Use the specified build time over the current time. "
              f"Format: {BUILDTIME_FORMAT_HELP}"), metavar='TIME')
    parser.add_argument(
        '--process-types', dest='processtypes', action='store_true', 
        help="Process the 'type' and 'rtype' fields, add links and inline markup automatically. "
            "This settings should not be enabled when using google or numpy docformat because the types are always processed by default.",)
    parser.add_argument(
        '-W', '--warnings-as-errors', action='store_true',
        dest='warnings_as_errors', default=False,
        help=("Return exit code 3 on warnings."))
    parser.add_argument(
        '--verbose', '-v',action='count', dest='verbosity',
        default=0,
        help=("Be noisier.  Can be repeated for more noise."))
    parser.add_argument(
        '--quiet', '-q', action='count', dest='quietness',
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
        help="Where to cache intersphinx objects.inv files.",
        metavar='PATH',
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
        metavar='DURATION',
    )
    parser.add_argument(
        '--pyval-repr-maxlines', dest='pyvalreprmaxlines', default=7, type=int, metavar='INT',
        help='Maxinum number of lines for a constant value representation. Use 0 for unlimited.')
    parser.add_argument(
        '--pyval-repr-linelen', dest='pyvalreprlinelen', default=80, type=int, metavar='INT',
        help='Maxinum number of caracters for a constant value representation line. Use 0 for unlimited.')
    parser.add_argument(
        '--system-class', dest='systemclass', default='pydoctor.zopeinterface.ZopeInterfaceSystem',
        help=("A dotted name of the class to use to make a system."))
    
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
    
    parser.add_argument(
        'sourcepath', metavar='SOURCEPATH', 
        help=("Path to python modules/packages to document."),
        nargs="*", default=[], 
    )
    return parser

# TODO: Make it compatible with this older version of the config file.
def readConfigFile(options: Any) -> None:
    # Deprecated
    # this is all a bit horrible.  rethink, then rewrite!
    for i, line in enumerate(open(options.configfile, encoding='utf-8')):
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

def parse_args(args: Sequence[str]) -> Namespace:
    parser = get_parser()
    options = parser.parse_args(args)
    assert isinstance(options, Namespace)
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

def get_system(options: model.Options) -> model.System:
    """
    Get a system with the defined options. Load packages and modules.
    """
    cache = prepareCache(clearCache=options.clear_intersphinx_cache,
                         enableCache=options.enable_intersphinx_cache,
                         cachePath=options.intersphinx_cache_path,
                         maxAge=options.intersphinx_cache_max_age)

    # step 1: make/find the system
    system = options.systemclass(options)
    system.fetchIntersphinxInventories(cache)
    cache.close() # Fixes ResourceWarning: unclosed <ssl.SSLSocket>

    # TODO: load buildtime with default factory and converter in model.Options
    # Support source date epoch:
    # https://reproducible-builds.org/specs/source-date-epoch/
    try:
        system.buildtime = datetime.datetime.utcfromtimestamp(
            int(os.environ['SOURCE_DATE_EPOCH']))
    except ValueError as e:
        error(str(e))
    except KeyError:
        pass
    # Load custom buildtime
    if options.buildtime:
        try:
            system.buildtime = datetime.datetime.strptime(
                options.buildtime, BUILDTIME_FORMAT)
        except ValueError as e:
            error(str(e))
    
    # step 2: add any packages and modules

    prependedpackage = None
    if options.prependedpackage:
        for m in options.prependedpackage.split('.'):
            prependedpackage = system.Package(
                system, m, prependedpackage)
            system.addObject(prependedpackage)
            initmodule = system.Module(system, '__init__', prependedpackage)
            system.addObject(initmodule)
    
    added_paths = set()
    for path in options.sourcepath:
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

    # step 3: move the system to the desired state

    if system.options.projectname is None:
        name = '/'.join(system.root_names)
        system.msg('warning', f"Guessing '{name}' for project name.", thresh=0)
        system.projectname = name
    else:
        system.projectname = system.options.projectname

    system.process()

    return system

def make(system: model.System) -> None:
    """
    Produce the html/intersphinx output, as configured in the system's options. 
    """
    options = system.options
    # step 4: make html, if desired

    if options.makehtml:
        options.makeintersphinx = True
        
        system.msg('html', 'writing html to %s using %s.%s'%(
            options.htmloutput, options.htmlwriter.__module__,
            options.htmlwriter.__name__))

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

        writer = options.htmlwriter(build_directory, template_lookup=template_lookup)

        writer.prepOutputDirectory()

        subjects: Sequence[model.Documentable] = ()
        if options.htmlsubjects:
            subjects = [system.allobjects[fn] for fn in options.htmlsubjects]
        else:
            writer.writeSummaryPages(system)
            if not options.htmlsummarypages:
                subjects = system.rootobjects
        writer.writeIndividualFiles(subjects)
        
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

def main(args: Sequence[str] = sys.argv[1:]) -> int:
    """
    This is the console_scripts entry point for pydoctor CLI.

    @param args: Command line arguments to run the CLI.
    """
    options = model.Options.from_namespace(parse_args(args))

    exitcode = 0

    try:

        # Check that we're actually going to accomplish something here
        if not options.sourcepath:
            error("No source paths given.")

        # Build model
        system = get_system(options)
        
        # Produce output (HMTL, json, ect)
        make(system)

        # Print summary of docstring syntax errors
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
        
    except:
        if options.pdb:
            import pdb
            pdb.post_mortem(sys.exc_info()[2])
        raise
    
    return exitcode
