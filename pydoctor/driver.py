"""The command-line parsing and entry point."""

from pydoctor import model, zopeinterface
import sys, os

def error(msg, *args):
    if args:
        msg = msg%args
    print >> sys.stderr, msg
    sys.exit(1)

def findClassFromDottedName(dottedname, optionname):
    # watch out, prints a message and SystemExits on error!
    if '.' not in dottedname:
        error("%stakes a dotted name", optionname)
    parts = dottedname.rsplit('.', 1)
    try:
        mod = __import__(parts[0], globals(), locals(), parts[1])
    except ImportError:
        error("could not import module %s", parts[0])
    try:
        return getattr(mod, parts[1])
    except AttributeError:
        error("did not find %s in module %s", parts[1], parts[0])

def getparser():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option(
        '-c', '--config', dest='configfile',
        help=("Use config from this file (any command line"
              "options override settings from the file)."))
    parser.add_option(
        '-p', '--input-pickle', dest='inputpickle',
        help=("Load the system from this pickle file (default: "
              "none, a blank system is created)."))
    parser.add_option(
        '-o', '--output-pickle', dest='outputpickle',
        help=("Save the system to this pickle file (default: "
              "none, the system is not saved by default)."))
    parser.add_option(
        '--extra-system', action='append', dest='moresystems',
        metavar='SYS:URLPREFIX', default=[],
        help=("Look for objects in this system to.  Links to these "
              "objects will have URLPREFIX prepended to them."))
    parser.add_option(
        '--system-class', dest='systemclass',
        help=("A dotted name of the class to use to make a system."))
    parser.add_option(
        '--project-name', dest='projectname',
        help=("The project name, appears in the html."))
    parser.add_option(
        '--project-url', dest='projecturl',
        help=("The project url, appears in the html if given."))
    parser.add_option(
        '--project-base-dir', dest='projectbasedirectory',
        help=("Absolute path to the base directory of the "
              "project.  Source links will be computed based "
              "on this value."))
    parser.add_option(
        '--testing', dest='testing', action='store_true',
        help=("Don't complain if the run doesn't have any effects."))
    parser.add_option(
        '--pdb', dest='pdb', action='store_true',
        help=("Like py.test's --pdb."))
    parser.add_option(
        '--make-html', action='store_true', dest='makehtml',
        default=True, help=("Produce html output."))
    parser.add_option(
        '--server', action='store_true', dest='server',
        help=("Serve HTML on a local server."))
    parser.add_option(
        '--server-port', action='store', dest='server_port',
        type=int, default=8080,
        help=("The port for --server to use."))
    parser.add_option(
        '--local-only', action='store_true', dest='local_only',
        help=("Bind the server to localhost only."))
    parser.add_option(
        '--facing-path', action='store', dest='facing_path',
        help=("Set up a VHostMonster, with all the confusion that implies."))
    parser.add_option(
        '--edit', action='store_true', dest='edit',
        help=("When serving HTML, allow editing."))
    parser.add_option(
        '--no-check', action='store_true', dest='nocheck',
        help=("When serving HTML and allow editing, don't check all "
              "docstrings first."))
    parser.add_option(
        '--add-package', action='append', dest='packages',
        metavar='PACKAGEDIR', default=[],
        help=("Add a package to the system.  Can be repeated "
              "to add more than one package."))
    parser.add_option(
        '--add-module', action='append', dest='modules',
        metavar='MODULE', default=[],
        help=("Add a module to the system.  Can be repeated."))
    parser.add_option(
        '--prepend-package', action='store', dest='prependedpackage',
        help=("Pretend that all packages are within this one.  "
              "Can be used to document part of a package."))
    parser.add_option(
        '--resolve-aliases', action='store_true',
        dest='resolvealiases', default=False,
        help=("This updates references to classes imported from a module "
              "into which they were imported to references to where they "
              "are defined."))
    parser.add_option(
        '--abbreviate-specialcase', action='store',
        dest='abbrevmapping', default='',
        help=("This is a comma seperated list of key=value pairs.  "
              "Where any key corresponds to a module name and value is "
              "the desired abbreviation.  This can be used to resolve "
              "conflicts with abbreviation where you have two or more "
              "modules that start with the same letter.  Example: "
              "twistedcaldav=tcd."))
    parser.add_option(
        '--docformat', dest='docformat', action='store', default='epytext',
        help=("Which epydoc-supported format docstrings are assumed "
              "to be in."))
    parser.add_option(
        '--html-subject', dest='htmlsubjects', action='append',
        help=("The fullName of object to generate API docs for"
              " (default: everything)."))
    parser.add_option(
        '--html-summary-pages', dest='htmlsummarypages',
        action='store_true', default=False,
        help=("Only generate the summary pages."))
    parser.add_option(
        '--html-write-function-pages', dest='htmlfunctionpages',
        default=False, action='store_true',
        help=("Make individual HTML files for every function and "
              "method. They're not linked to in any pydoctor-"
              "generated HTML, but they can be useful for third-party "
              "linking."))
    parser.add_option(
        '--html-output', dest='htmloutput', default='apidocs',
        help=("Directory to save HTML files to (default 'apidocs')"))
    parser.add_option(
        '--html-writer', dest='htmlwriter',
        help=("Dotted name of html writer class to use (default "
              "'pydoctor.nevowhtml.NevowWriter', requires Divmod Nevow "
              "to be installed)."))
    parser.add_option(
        '--html-viewsource-base', dest='htmlsourcebase',
        help=("This should be the path to the trac browser for the top "
              "of the svn checkout we are documenting part of."))
    parser.add_option(
        '--html-use-sorttable', dest='htmlusesorttable',
        default=False, action="store_true",
        help=("Use the sorttable JS library to make tables of package, "
              "module and class contents sortable"))
    parser.add_option(
        '--html-use-splitlinks', dest='htmlusesplitlinks',
        default=False, action="store_true",
        help=("Generate (unobstrusive) JavaScript to allow class methods to "
              "be shown either in one table per base class or in one big "
              "table."))
    parser.add_option(
        '--html-shorten-lists', dest='htmlshortenlists',
        default=False, action="store_true",
        help=("Generate (unobstrusive) JavaScript to hide some of the "
              "entries in long lists of e.g. subclasses."))
    parser.add_option(
        '--livecheck', action='store_true', dest='livecheck',
        default=False,
        help=("Import and examine the modules too.  XXX not working "
              "right now"))
    parser.add_option(
        '-v', '--verbose', action='count', dest='verbosity',
        default=0,
        help=("Be noisier.  Can be repeated for more noise."))
    parser.add_option(
        '-q', '--quiet', action='count', dest='quietness',
        default=0,
        help=("Be quieter."))
    parser.add_option(
        '--auto', action="store_true", dest="auto",
        help=("Automagic mode: analyze all modules and packages in the "
              "current working directory and run a local server that allows "
              "examination and editing of the docstrings."))
    def verbose_about_callback(option, opt_str, value, parser):
        d = parser.values.verbosity_details
        d[value] = d.get(value, 0) + 1
    parser.add_option(
        '--verbose-about', metavar="stage", action="callback",
        type=str, default={}, dest='verbosity_details',
        callback=verbose_about_callback,
        help=("Be noiser during a particular stage of generation."))
    return parser

def readConfigFile(options):
    # this is all a bit horrible.  rethink, then rewrite!
    for i, line in enumerate(open(options.configfile, 'rU')):
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

def parse_args(args):
    parser = getparser()
    options, args = parser.parse_args(args)
    options.verbosity -= options.quietness
    return options, args

def main(args):
    import cPickle
    options, args = parse_args(args)

    args = list(args) + options.modules + options.packages

    exitcode = 0

    if options.configfile:
        readConfigFile(options)

    try:
        # step 1: make/find the system
        if options.systemclass:
            systemclass = findClassFromDottedName(options.systemclass,
                                                  '--system-class')
            if not issubclass(systemclass, model.System):
                msg = "%s is not a subclass of model.System"
                error(msg, systemclass)
        else:
            systemclass = zopeinterface.ZopeInterfaceSystem

        if options.inputpickle:
            system = cPickle.load(open(options.inputpickle, 'rb'))
            if options.systemclass:
                if type(system) is not systemclass:
                    cls = type(system)
                    msg = ("loaded pickle has class %s.%s, differing "
                           "from explicitly requested %s")
                    error(msg, cls.__module__, cls.__name__,
                          options.systemclass)
        else:
            system = systemclass()

        system.options = options

        system.urlprefix = ''
        if options.moresystems:
            moresystems = []
            for fnamepref in options.moresystems:
                fname, prefix = fnamepref.split(':', 1)
                moresystems.append(cPickle.load(open(fname, 'rb')))
                moresystems[-1].urlprefix = prefix
                moresystems[-1].options = system.options
                moresystems[-1].subsystems.append(system)
            system.moresystems = moresystems
        system.sourcebase = options.htmlsourcebase

        if options.abbrevmapping:
            for thing in options.abbrevmapping.split(','):
                k, v = thing.split('=')
                system.abbrevmapping[k] = v

        # step 1.5: check that we're actually going to accomplish something here

        if options.auto:
            options.server = True
            options.edit = True
            for fn in os.listdir('.'):
                if os.path.isdir(fn) and \
                   os.path.exists(os.path.join(fn, '__init__.py')):
                    options.packages.append(fn)
                elif fn.endswith('.py') and fn != 'setup.py':
                    options.modules.append(fn)

        if not options.outputpickle and not options.makehtml \
               and not options.testing and not options.server:
            msg = ("this invocation isn't going to do anything\n"
                   "maybe supply --make-html and/or --output-pickle?")
            error(msg)

        # step 2: add any packages and modules

        if args:
            prependedpackage = None
            if options.prependedpackage:
                for m in options.prependedpackage.split('.'):
                    prependedpackage = system.Package(
                        system, m, None, prependedpackage)
                    system.addObject(prependedpackage)
                    initmodule = system.Module(system, '__init__', None, prependedpackage)
                    system.addObject(initmodule)
            for path in args:
                path = os.path.abspath(path)
                if path in system.packages:
                    continue
                if os.path.isdir(path):
                    system.msg('addPackage', 'adding directory ' + path)
                    system.addPackage(path, prependedpackage)
                else:
                    system.msg('addModule', 'adding module ' + path)
                    system.addModule(path, prependedpackage)
                system.packages.append(path)

        # step 3: move the system to the desired state

        if not system.packages:
            error("The system does not contain any code, did you "
                  "forget an --add-package?")

        system.process()

        if system.options.livecheck:
            error("write this")

        if system.options.projectname is None:
            name = '/'.join([ro.name for ro in system.rootobjects])
            system.msg(
                'warning',
                'WARNING: guessing '+name+' for project name', thresh=-1)
            system.guessedprojectname = name

        # step 4: save the system, if desired

        if options.outputpickle:
            system.msg('', 'saving output pickle to ' + options.outputpickle)
            del system.options # don't persist the options
            f = open(options.outputpickle, 'wb')
            cPickle.dump(system, f, cPickle.HIGHEST_PROTOCOL)
            f.close()
            system.options = options

        # step 5: make html, if desired

        if options.makehtml:
            if options.htmlwriter:
                writerclass = findClassFromDottedName(
                    options.htmlwriter, '--html-writer')
            else:
                from pydoctor import nevowhtml
                writerclass = nevowhtml.NevowWriter

            system.msg('html', 'writing html to %s using %s.%s'%(
                options.htmloutput, writerclass.__module__,
                writerclass.__name__))

            writer = writerclass(options.htmloutput)
            writer.system = system
            writer.prepOutputDirectory()

            system.epytextproblems = []

            if options.htmlsubjects:
                subjects = []
                for fn in options.htmlsubjects:
                    subjects.append(system.allobjects[fn])
            elif options.htmlsummarypages:
                writer.writeModuleIndex(system)
                subjects = []
            else:
                writer.writeModuleIndex(system)
                subjects = system.rootobjects
            writer.writeIndividualFiles(subjects, options.htmlfunctionpages)
            if system.epytextproblems:
                def p(msg):
                    system.msg(('epytext', 'epytext-summary'), msg, thresh=-1, topthresh=1)
                p("these %s objects' docstrings are not proper epytext:"
                  %(len(system.epytextproblems),))
                exitcode = 2
                for fn in system.epytextproblems:
                    p('    '+fn)
            if options.outputpickle:
                system.msg(
                    '', 'saving output pickle to ' + options.outputpickle)
                # save again, with epytextproblems
                del system.options # don't persist the options
                f = open(options.outputpickle, 'wb')
                cPickle.dump(system, f, cPickle.HIGHEST_PROTOCOL)
                f.close()
                system.options = options

        # Finally, if we should serve html, lets serve some html.
        if options.server:
            from pydoctor.server import (
                EditingPyDoctorResource, PyDoctorResource)
            from pydoctor.epydoc2stan import doc2html
            from nevow import appserver
            from twisted.internet import reactor
            if options.edit:
                if not options.nocheck:
                    system.msg(
                        "server", "Checking formatting of docstrings.")
                    included_obs = [
                        ob for ob in system.orderedallobjects
                        if ob.isVisible]
                    for i, ob in enumerate(included_obs):
                        system.progress(
                            "server", i+1, len(included_obs),
                            "docstrings checked, found %s problems" % (
                            len(system.epytextproblems)))
                        doc2html(ob, docstring=ob.docstring)
                root = EditingPyDoctorResource(system)
            else:
                root = PyDoctorResource(system)
            if options.facing_path:
                options.local_only = True
                from nevow import rend, vhost
                realroot = rend.Page()
                cur = realroot
                realroot.putChild('vhost', vhost.VHostMonsterResource())
                segments = options.facing_path.split('/')
                for segment in segments[:-1]:
                    next = rend.Page()
                    cur.putChild(segment, next)
                    cur = next
                cur.putChild(segments[-1], root)
                root = realroot
            system.msg(
                "server",
                "Setting up server at http://localhost:%d/" %
                options.server_port)
            if options.auto:
                def wb_open():
                    import webbrowser
                    webbrowser.open(
                        'http://localhost:%d/' % options.server_port)
                reactor.callWhenRunning(wb_open)
            from twisted.python import log
            log.startLogging(sys.stdout)
            site = appserver.NevowSite(root)
            if options.local_only:
                interface = 'localhost'
            else:
                interface = ''
            reactor.listenTCP(options.server_port, site, interface=interface)
            reactor.run()
    except:
        if options.pdb:
            import pdb
            pdb.post_mortem(sys.exc_traceback)
        raise
    return exitcode

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
