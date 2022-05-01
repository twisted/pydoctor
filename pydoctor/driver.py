"""The entry point."""

from typing import  Sequence
import datetime
import os
import sys
from pathlib import Path

from pydoctor.options import Options, BUILDTIME_FORMAT
from pydoctor.utils import error
from pydoctor import imodel
from pydoctor.templatewriter import IWriter, TemplateLookup, TemplateError
from pydoctor.sphinx import SphinxInventoryWriter, prepareCache

# In newer Python versions, use importlib.resources from the standard library.
# On older versions, a compatibility package must be installed from PyPI.
if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

def get_system(options: Options) -> imodel.ISystem:
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

    # TODO: load buildtime with default factory and converter in Options
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
    
    builder = system.systemBuilder(system)
    try:
        for path in options.sourcepath:
            builder.addModule(path)
    except imodel.SystemBuildingError as e:
        error(str(e))

    # step 3: move the system to the desired state

    if system.options.projectname is None:
        name = '/'.join(system.root_names)
        system.msg('warning', f"Guessing '{name}' for project name.", thresh=0)
        system.projectname = name
    else:
        system.projectname = system.options.projectname

    builder.buildModules()

    return system

def make(system: imodel.ISystem) -> None:
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

        subjects: Sequence[imodel.IDocumentable] = ()
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
    options = Options.from_args(args)

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
            exitcode = 2

            def p(msg: str) -> None:
                system.msg('docstring-summary', msg, thresh=-1, topthresh=1)
            p("these %s objects' docstrings contain syntax errors:"
                %(len(system.docstring_syntax_errors),))
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
