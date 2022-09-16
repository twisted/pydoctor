"""
The command-line parsing.
"""

import re
from typing import Sequence, List, Optional, Type, Tuple, TYPE_CHECKING
import sys
import functools
from pathlib import Path
from argparse import SUPPRESS, Namespace

from configargparse import ArgumentParser
import attr

from pydoctor import __version__
from pydoctor.themes import get_themes
from pydoctor.epydoc.markup import get_supported_docformats
from pydoctor.sphinx import MAX_AGE_HELP, USER_INTERSPHINX_CACHE
from pydoctor.utils import parse_path, findClassFromDottedName, parse_privacy_tuple, error
from pydoctor._configparser import CompositeConfigParser, IniConfigParser, TomlConfigParser, ValidatorParser

if TYPE_CHECKING:
    from typing import Literal
    from pydoctor import model
    from pydoctor.templatewriter import IWriter

BUILDTIME_FORMAT = '%Y-%m-%d %H:%M:%S'
BUILDTIME_FORMAT_HELP = 'YYYY-mm-dd HH:MM:SS'

DEFAULT_CONFIG_FILES = ['./pyproject.toml', './setup.cfg', './pydoctor.ini']
CONFIG_SECTIONS = ['tool.pydoctor', 'tool:pydoctor', 'pydoctor']

DEFAULT_SYSTEM = 'pydoctor.model.System'

__all__ = ("Options", )

# CONFIGURATION PARSING

PydoctorConfigParser = CompositeConfigParser(
                [TomlConfigParser(CONFIG_SECTIONS),
                 IniConfigParser(CONFIG_SECTIONS, split_ml_text_to_list=True)])

# ARGUMENTS PARSING

def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog='pydoctor',
        description="API doc generator.",
        usage="pydoctor [options] SOURCEPATH...", 
        default_config_files=DEFAULT_CONFIG_FILES,
        config_file_parser_class=PydoctorConfigParser)
    
    # Add the validator to the config file parser, this is arguably a hack.
    parser._config_file_parser = ValidatorParser(parser._config_file_parser, parser)
    
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
              "will be computed based on this value."), metavar="PATH", default='.')
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
    # Used to pass sourcepath from config file
    parser.add_argument(
        '--add-package', '--add-module', action='append', dest='packages',
        metavar='MODPATH', default=[], help=SUPPRESS)
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
        '--html-viewsource-template', dest='htmlsourcetemplate', 
        help=("A format string used to generate the source link of documented objects. "
            "The default behaviour auto detects most common providers like Github, Bitbucket, GitLab or SourceForge. "
            "But in some cases you might have to override the template string, for instance to make it work with git-web, use: "
            '--html-viewsource-template="{mod_source_href}#n{lineno}"'), metavar='SOURCETEMPLATE', default=Options.HTML_SOURCE_TEMPLATE_DEFAULT)
    parser.add_argument(
        '--buildtime', dest='buildtime',
        help=("Use the specified build time over the current time. "
              f"Format: {BUILDTIME_FORMAT_HELP}"), metavar='TIME')
    parser.add_argument(
        '--process-types', dest='processtypes', action='store_true', 
        help="Process the 'type' and 'rtype' fields, add links and inline markup automatically. "
            "This settings should not be enabled when using google or numpy docformat because the types are always processed by default.",)
    parser.add_argument(
        '--warnings-as-errors', '-W', action='store_true',
        dest='warnings_as_errors', default=False,
        help=("Return exit code 3 on warnings."))
    parser.add_argument(
        '--verbose', '-v', action='count', dest='verbosity',
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
        '--sidebar-expand-depth', metavar="INT", type=int, default=1, dest='sidebarexpanddepth',
        help=("How many nested modules and classes should be expandable, "
              "first level is always expanded, nested levels can expand/collapse. Value should be 1 or greater. (default: 1)"))
    parser.add_argument(
        '--sidebar-toc-depth', metavar="INT", type=int, default=6, dest='sidebartocdepth',
        help=("How many nested titles should be listed in the docstring TOC "
              "(default: 6)"))
    parser.add_argument(
        '--no-sidebar', default=False, action='store_true', dest='nosidebar',
        help=("Do not generate the sidebar at all."))
    
    parser.add_argument(
        '--system-class', dest='systemclass', default=DEFAULT_SYSTEM,
        help=("A dotted name of the class to use to make a system."))

    parser.add_argument(
        '--cls-member-order', dest='cls_member_order', default="alphabetical", choices=["alphabetical", "source"],
        help=("Presentation order of class members. (default: alphabetical)"))
    parser.add_argument(
        '--mod-member-order', dest='mod_member_order', default="alphabetical", choices=["alphabetical", "source"],
        help=("Presentation order of module/package members. (default: alphabetical)"))
    
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

# CONVERTERS

def _convert_sourcepath(l: List[str]) -> List[Path]:
    return list(map(functools.partial(parse_path, opt='SOURCEPATH'), l))
def _convert_templatedir(l: List[str]) -> List[Path]:
    return list(map(functools.partial(parse_path, opt='--template-dir'), l))
def _convert_projectbasedirectory(s: Optional[str]) -> Optional[Path]:
    if s: return parse_path(s, opt='--project-base-dir')
    else: return None
def _convert_systemclass(s: str) -> Type['model.System']:
    try:
        return findClassFromDottedName(s, '--system-class', base_class='pydoctor.model.System')
    except ValueError as e:
        error(str(e))
def _convert_htmlwriter(s: str) -> Type['IWriter']:
    try:
        return findClassFromDottedName(s, '--html-writer', base_class='pydoctor.templatewriter.IWriter')
    except ValueError as e:
        error(str(e))
def _convert_privacy(l: List[str]) -> List[Tuple['model.PrivacyClass', str]]:
    return list(map(functools.partial(parse_privacy_tuple, opt='--privacy'), l))

_RECOGNIZED_SOURCE_HREF = {
        # Sourceforge
        '{mod_source_href}#l{lineno}': re.compile(r'(^https?:\/\/sourceforge\.net\/)'),

        # Bitbucket 
        '{mod_source_href}#lines-{lineno}': re.compile(r'(^https?:\/\/bitbucket\.org\/)'),
        
        # Matches all other plaforms: Github, Gitlab, etc. 
        # This match should be kept last in the list.
        '{mod_source_href}#L{lineno}': re.compile(r'(.*)?') 
    }
    # Since we can't guess git-web platform form URL, 
    # we have to pass the template string wih option:
    # --html-viewsource-template="{mod_source_href}#n{lineno}"

def _get_viewsource_template(sourcebase: Optional[str]) -> str:
    """
    Recognize several version control providers based on option C{--html-viewsource-base}.
    """
    if not sourcebase:
        return '{mod_source_href}#L{lineno}'
    for template, regex in _RECOGNIZED_SOURCE_HREF.items():
        if regex.match(sourcebase):
            return template
    else:
        assert False

# TYPED OPTIONS CONTAINER

@attr.s
class Options:
    """
    Container for all possible pydoctor options. 

    See C{pydoctor --help} for more informations. 
    """
    MAKE_HTML_DEFAULT = object()
    # Avoid to define default values for config options here because it's taken care of by argparse.
    
    HTML_SOURCE_TEMPLATE_DEFAULT = object()

    sourcepath:             List[Path]                              = attr.ib(converter=_convert_sourcepath)
    systemclass:            Type['model.System']                    = attr.ib(converter=_convert_systemclass)
    projectname:            Optional[str]                           = attr.ib()
    projectversion:         str                                     = attr.ib()
    projecturl:             Optional[str]                           = attr.ib()
    projectbasedirectory:   Path                                    = attr.ib(converter=_convert_projectbasedirectory)
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
    htmlsourcetemplate:     str                                     = attr.ib()
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
    sidebarexpanddepth:     int                                     = attr.ib()
    sidebartocdepth:        int                                     = attr.ib()
    nosidebar:              int                                     = attr.ib()
    cls_member_order:       'Literal["alphabetical", "source"]'     = attr.ib()
    mod_member_order:       'Literal["alphabetical", "source"]'     = attr.ib()

    def __attrs_post_init__(self) -> None:
        # do some validations...
        # check if sidebar related arguments are valid
        if self.sidebarexpanddepth < 1:
            error("Invalid --sidebar-expand-depth value." + 'The value of --sidebar-expand-depth option should be greater or equal to 1, '
                                'to suppress sidebar generation all together: use --no-sidebar')
        if self.sidebartocdepth < 0:
            error("Invalid --sidebar-toc-depth value" + 'The value of --sidebar-toc-depth option should be greater or equal to 0, '
                                'to suppress sidebar generation all together: use --no-sidebar')
            
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
        
        # auto-detect source link template if the default value is used.
        if args.htmlsourcetemplate == cls.HTML_SOURCE_TEMPLATE_DEFAULT:
            argsdict['htmlsourcetemplate'] = _get_viewsource_template(args.htmlsourcebase)

        # handle deprecated arguments
        argsdict['sourcepath'].extend(list(map(functools.partial(parse_path, opt='--add-package'), argsdict.pop('packages'))))

        # remove deprecated arguments
        argsdict.pop('enable_intersphinx_cache_deprecated')

        # remove the config argument
        argsdict.pop('config')
        
        return cls(**argsdict)
        
