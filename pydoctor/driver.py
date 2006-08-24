from pydoctor import model, html, astbuilder, liveobjectchecker
import sys, os

def error(msg, *args):
    if args:
        msg = msg%args
    print >> sys.stderr, msg
    sys.exit(1)

def findClassFromDottedName(dottedname, optionname):
    # watch out, print a message and SystemExits on error!
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
    parser.add_option('-c', '--config', dest='configfile',
                      help="Use config from this file (any command line"
                           "options override settings from the file).")
    parser.add_option('-p', '--input-pickle', dest='inputpickle',
                      help="Load the system from this pickle file (default: "
                      "none, a blank system is created).")
    parser.add_option('-o', '--output-pickle', dest='outputpickle',
                      help="Save the system to this pickle file (default: "
                      "none, the system is not saved by default).")
    parser.add_option('--extra-system',
                      action='append', dest='moresystems', metavar='SYS:URLPREFIX',
                      default=[],
                      help='Experimental.')
    parser.add_option('--system-class', dest='systemclass',
                      help="a dotted name of the class to use to make a system")
    parser.add_option('--builder-class', dest='builderclass',
                      help="a dotted name of the class to use")
    parser.add_option('--project-name', dest='projectname',
                      help="the project name (appears on index.html)")
    parser.add_option('--testing', dest='testing', action='store_true',
                      help="don't complain if the run doesn't have any effects")
    parser.add_option('--target-state', dest='targetstate',
                      default='finalized',
                      choices=model.states,
                      help="the state to move the system to (default: %default).")
    parser.add_option('--make-html',
                      action='store_true', dest='makehtml',
                      help="")
    parser.add_option('--add-package',
                      action='append', dest='packages', metavar='PACKAGEDIR',
                      default=[],
                      help='Add a package to the system.  Can be repeated '
                           'to add more than one package.')
    parser.add_option('--prepend-package',
                      action='store', dest='prependedpackage',
                      help='')
    parser.add_option('--no-find-import-star',
                      action='store_false', dest='findimportstar',
                      default=True,
                      help="Don't preprocess the modules to resolve import *s."
                           " It's a significant speed saving if you don't need"
                           " it.")
    parser.add_option('--resolve-aliases',
                      action='store_true', dest='resolvealiases',
                      default=False,
                      help="experimental")
    parser.add_option('--abbreviate-specialcase',
                      action='store', dest='abbrevmapping',
                      default='',
                      help="This is a comma seperated list of key=value pairs.  "
                          "Where any key corresponds to a module name and value "
                          "is the desired abbreviation.  This can be used to "
                          "resolve conflicts with abbreviation where you have two or more "
                          "modules that start with the same letter.  Ex: twistedcaldav=tcd")
    parser.add_option('--html-subject', dest='htmlsubjects',
                      action='append',
                      help="fullName of object to generate API docs for"
                      " (default: everything).")
    parser.add_option('--html-summary-pages', dest='htmlsummarypages',
                      action='store_true',
                      default=False,
                      help="Only generate the summary pages.")
    parser.add_option('--html-write-function-pages', dest='htmlfunctionpages',
                      default=False,
                      action='store_true',
                      help="Make individual HTML files for every function and "
                      "method. They're not linked to in any pydoctor-"
                      "generated HTML, but they can be useful for third-party "
                      "linking.")
    parser.add_option('--html-output', dest='htmloutput',
                      default='apidocs',
                      help="Directory to save HTML files to "
                           "(default 'apidocs')")
    parser.add_option('--html-writer', dest='htmlwriter',
                      help="dotted name of html writer class to use"
                           "(default 'XXX')")
    parser.add_option('--html-viewsource-base', dest='htmlsourcebase',
                      help="")
    parser.add_option('--html-use-sorttable', dest='htmlusesorttable',
                      default=False,
                      action="store_true",
                      help="")
    parser.add_option('-v', '--verbose', action='count', dest='verbosity',
                      help="Be noisier.  Can be repeated for more noise.")
    return parser

def main(args):
    import cPickle
    parser = getparser()
    options, args = parser.parse_args(args)

    if options.configfile:
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
                setattr(options, k, v)

    # step 1: make/find the system
    if options.systemclass:
        systemclass = findClassFromDottedName(options.systemclass, '--system-class')
        if not issubclass(systemclass, model.System):
            msg = "%s is not a subclass of model.System"
            error(msg, systemclass)
    else:
        systemclass = model.System

    if options.inputpickle:
        system = cPickle.load(open(options.inputpickle, 'rb'))
        if options.systemclass:
            if type(system) is not systemclass:
                msg = ("loaded pickle has class %s.%s, differing "
                       "from explicitly requested %s")
                error(msg, cls.__module__, cls.__name__, options.systemclass)
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
        system.moresystems = moresystems
    system.sourcebase = options.htmlsourcebase

    for thing in options.abbrevmapping.split(','):
        k, v = thing.split('=')
        system.abbrevmapping[k] = v

    # step 1.25: make a builder

    if options.builderclass:
        builderclass = findClassFromDottedName(options.builderclass, '--builder-class')
        if not issubclass(builderclass, astbuilder.ASTBuilder):
            msg = "%s is not a subclass of astbuilder.ASTBuilder"
            error(msg, builderclass)
    elif hasattr(system, 'defaultBuilder'):
        builderclass = system.defaultBuilder
    else:
        builderclass = astbuilder.ASTBuilder

    builder = builderclass(system)

    # step 1.5: check that we're actually going to accomplish something here

    if not options.outputpickle and not options.makehtml \
           and not options.testing:
        msg = ("this invocation isn't going to do anything\n"
               "maybe supply --make-html and/or --output-pickle?")
        error(msg)

    # step 2: add any packages

    if options.packages:
        if options.prependedpackage:
            for m in options.prependedpackage.split('.'):
                builder.pushPackage(m, None)
        for path in options.packages:
            path = os.path.normpath(path)
            if path in system.packages:
                continue
            if system.state not in ['blank', 'preparse']:
                msg = 'system is in state %r, which is too late to add new code'
                error(msg, system.state)
            print 'adding directory', path
            builder.preprocessDirectory(path)
            system.packages.append(path)
        if options.prependedpackage:
            for m in options.prependedpackage.split('.'):
                builder.popPackage()

    # step 3: move the system to the desired state

    curstateindex = model.states.index(system.state)
    finalstateindex = model.states.index(options.targetstate)

    if finalstateindex < curstateindex and (options.targetstate, system.state) != ('finalized', 'livechecked'):
        msg = 'cannot reverse system from %r to %r'
        error(msg, system.state, options.targetstate)

    if finalstateindex > 0 and curstateindex == 0:
        msg = 'cannot advance totally blank system to %r'
        error(msg, options.targetstate)

    funcs = [None,
             builder.findImportStars,
             builder.extractDocstrings,
             builder.finalStateComputations,
             lambda : liveobjectchecker.liveCheck(system, builder)]

    for i in range(curstateindex, finalstateindex):
        f = funcs[i]
        if f == builder.findImportStars and not options.findimportstar:
            continue
        print f.__name__
        f()

    if system.state != options.targetstate:
        msg = "failed to advance state to %r (this is a bug)"
        error(msg, options.targetstate)

    # step 4: save the system, if desired

    if options.outputpickle:
        del system.options # don't persist the options
        f = open(options.outputpickle, 'wb')
        cPickle.dump(system, f, cPickle.HIGHEST_PROTOCOL)
        f.close()
        system.options = options

    # step 5: make html, if desired

    if options.makehtml:
        if options.htmlwriter:
            writerclass = findClassFromDottedName(options.htmlwriter, '--html-writer')
        else:
            writerclass = html.SystemWriter

        print 'writing html to', options.htmloutput,
        print 'using %s.%s'%(writerclass.__module__, writerclass.__name__)

        writer = writerclass(options.htmloutput)
        writer.system = system
        writer.prepOutputDirectory()

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

if __name__ == '__main__':
    main(sys.argv[1:])
