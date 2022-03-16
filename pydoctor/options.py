"""
Provides L{Options} container with high level factory methods.
"""

from typing import Sequence, List, Optional, Type, Tuple, TYPE_CHECKING
import sys
import functools
from pathlib import Path

from argparse import SUPPRESS, Namespace
from configargparse import ArgumentParser, ConfigparserConfigFileParser
import attr

from pydoctor import __version__
from pydoctor.themes import get_themes
from pydoctor.epydoc.markup import get_supported_docformats
from pydoctor.sphinx import MAX_AGE_HELP, USER_INTERSPHINX_CACHE
from pydoctor.utils import parse_path, findClassFromDottedName, error, parse_privacy_tuple

if TYPE_CHECKING:
    from pydoctor import model
    from pydoctor.templatewriter import IWriter

BUILDTIME_FORMAT = '%Y-%m-%d %H:%M:%S'
BUILDTIME_FORMAT_HELP = 'YYYY-mm-dd HH:MM:SS'

# DEFAULT_CONFIG_FILES = ['./setup.cfg', './pyproject.toml', './pydoctor.ini']
DEFAULT_CONFIG_FILES = ['./pydoctor.ini']

__all__ = ("Options", )

# ARGUMENTS PARSING

def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog='pydoctor',
        description="API doc generator.",
        usage="pydoctor [options] SOURCEPATH...", 
        default_config_files=DEFAULT_CONFIG_FILES,
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
        default=Options.MAKE_HTML_DEFAULT, help=("Produce html output."
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

# CONVERTERS

def _convert_sourcepath(l: List[str]) -> List[Path]:
    return list(map(functools.partial(parse_path, opt='SOURCEPATH'), l))
def _convert_templatedir(l: List[str]) -> List[Path]:
    return list(map(functools.partial(parse_path, opt='--template-dir'), l))
def _convert_projectbasedirectory(s: Optional[str]) -> Optional[Path]:
    if s: return parse_path(s, opt='--project-base-dir')
    else: return None
def _convert_systemclass(s: str) -> Type['model.System']:
    return findClassFromDottedName(s, '--system-class', base_class='pydoctor.model.System')
def _convert_htmlwriter(s: str) -> Type['IWriter']:
    return findClassFromDottedName(s, '--html-writer', base_class='pydoctor.templatewriter.IWriter')
def _convert_privacy(l: List[str]) -> List[Tuple['model.PrivacyClass', str]]:
    return list(map(functools.partial(parse_privacy_tuple, opt='--privacy'), l))

# TYPED OPTIONS CONTAINER

@attr.s
class Options:
    """
    Container for all possible pydoctor options. 

    See C{pydoctor --help} for more informations. 
    """
    MAKE_HTML_DEFAULT = object()
    # Avoid to define default values for config options here because it's taken care of by argparse.

    sourcepath:             List[Path]                              = attr.ib(converter=_convert_sourcepath)
    systemclass:            Type['model.System']                    = attr.ib(converter=_convert_systemclass)
    projectname:            Optional[str]                           = attr.ib()
    projectversion:         str                                     = attr.ib()
    projecturl:             Optional[str]                           = attr.ib()
    projectbasedirectory:   Optional[Path]                          = attr.ib(converter=_convert_projectbasedirectory)
    testing:                bool                                    = attr.ib()
    pdb:                    bool                                    = attr.ib() # only working via driver.main()
    makehtml:               bool                                    = attr.ib()
    makeintersphinx:        bool                                    = attr.ib()
    prependedpackage:       Optional[str]                           = attr.ib()
    docformat:              str                                     = attr.ib()
    theme:                  str                                     = attr.ib()
    processtypes:           bool                                    = attr.ib()
    templatedir:            List[Path]                              = attr.ib(converter=_convert_templatedir)
    privacy:                List[Tuple['model.PrivacyClass', str]]  = attr.ib(converter=_convert_privacy)
    htmlsubjects:           Optional[List[str]]                     = attr.ib()
    htmlsummarypages:       bool                                    = attr.ib()
    htmloutput:             str                                     = attr.ib() # TODO: make this a Path object once https://github.com/twisted/pydoctor/pull/389/files is merged
    htmlwriter:             Type['IWriter']                         = attr.ib(converter=_convert_htmlwriter)
    htmlsourcebase:         Optional[str]                           = attr.ib()
    buildtime:              Optional[str]                           = attr.ib()
    warnings_as_errors:     bool                                    = attr.ib()
    verbosity:              int                                     = attr.ib()
    quietness:              int                                     = attr.ib()
    introspect_c_modules:   bool                                    = attr.ib()
    intersphinx:            List[str]                               = attr.ib()
    enable_intersphinx_cache:   bool                                = attr.ib()
    intersphinx_cache_path:     str                                 = attr.ib()
    clear_intersphinx_cache:    bool                                = attr.ib()
    intersphinx_cache_max_age:  str                                 = attr.ib()
    pyvalreprlinelen:       int                                     = attr.ib()
    pyvalreprmaxlines:      int                                     = attr.ib()

    def __attrs_post_init__(self) -> None:
        # FIXME: https://github.com/twisted/pydoctor/issues/441
        # do some validations
        if self.htmlsourcebase:
            if self.projectbasedirectory is None:
                error("you must specify --project-base-dir "
                        "when using --html-viewsource-base")

    # HIGH LEVEL FACTORY METHODS

    @classmethod
    def defaults(cls,) -> 'Options':
        return cls.from_args([])
    
    @classmethod
    def from_args(cls, args: Sequence[str]) -> 'Options':
        return cls.from_namespace(parse_args(args))
    
    @classmethod
    def from_namespace(cls, args: Namespace) -> 'Options':
        argsdict = vars(args)

        # set correct default for --make-html
        if args.makehtml == cls.MAKE_HTML_DEFAULT:
            if not args.testing and not args.makeintersphinx:
                argsdict['makehtml'] = True
            else:
                argsdict['makehtml'] = False

        # handle deprecated arguments
        argsdict['sourcepath'].extend(list(map(functools.partial(parse_path, opt='--add-package'), argsdict.pop('packages'))))
        argsdict['sourcepath'].extend(list(map(functools.partial(parse_path, opt='--add-module'), argsdict.pop('modules'))))

        # remove deprecated arguments
        argsdict.pop('enable_intersphinx_cache_deprecated')

        # remove the config argument
        argsdict.pop('config')
        
        return cls(**argsdict)