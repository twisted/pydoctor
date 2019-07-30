# epydoc -- Utility functions
#
# Copyright (C) 2005 Edward Loper
# Author: Edward Loper <edloper@loper.org>
# URL: <http://epydoc.sf.net>
#

"""
Miscellaneous utility functions that are used by multiple modules.

@group Python source types: py_src_filename
@group Text processing: wordwrap, decode_with_backslashreplace,
    plaintext_to_html
"""
__docformat__ = 'epytext en'

import os, os.path, re, sys

######################################################################
## Python Source Types
######################################################################

PY_SRC_EXTENSIONS = ['.py', '.pyw']

def py_src_filename(filename):
    basefile, extension = os.path.splitext(filename)
    if extension in PY_SRC_EXTENSIONS:
        return filename
    else:
        for ext in PY_SRC_EXTENSIONS:
            if os.path.isfile('%s%s' % (basefile, ext)):
                return '%s%s' % (basefile, ext)
        else:
            raise ValueError('Could not find a corresponding '
                             'Python source file for %r.' % filename)

######################################################################
## Text Processing
######################################################################

def decode_with_backslashreplace(s):
    r"""
    Convert the given 8-bit string into unicode, treating any
    character c such that ord(c)<128 as an ascii character, and
    converting any c such that ord(c)>128 into a backslashed escape
    sequence.

        >>> decode_with_backslashreplace('abc\xff\xe8')
        u'abc\\xff\\xe8'
    """
    # s.encode('string-escape') is not appropriate here, since it
    # also adds backslashes to some ascii chars (eg \ and ').
    assert isinstance(s, str)
    return (s
            .decode('latin1')
            .encode('ascii', 'backslashreplace')
            .decode('ascii'))

def wordwrap(str, indent=0, right=75, startindex=0, splitchars=''):
    """
    Word-wrap the given string.  I.e., add newlines to the string such
    that any lines that are longer than C{right} are broken into
    shorter lines (at the first whitespace sequence that occurs before
    index C{right}).  If the given string contains newlines, they will
    I{not} be removed.  Any lines that begin with whitespace will not
    be wordwrapped.

    @param indent: If specified, then indent each line by this number
        of spaces.
    @type indent: C{int}
    @param right: The right margin for word wrapping.  Lines that are
        longer than C{right} will be broken at the first whitespace
        sequence before the right margin.
    @type right: C{int}
    @param startindex: If specified, then assume that the first line
        is already preceeded by C{startindex} characters.
    @type startindex: C{int}
    @param splitchars: A list of non-whitespace characters which can
        be used to split a line.  (E.g., use '/\\' to allow path names
        to be split over multiple lines.)
    @rtype: C{str}
    """
    if splitchars:
        chunks = re.split(r'( +|\n|[^ \n%s]*[%s])' %
                          (re.escape(splitchars), re.escape(splitchars)),
                          str.expandtabs())
    else:
        chunks = re.split(r'( +|\n)', str.expandtabs())
    result = [' '*(indent-startindex)]
    charindex = max(indent, startindex)
    for chunknum, chunk in enumerate(chunks):
        if (charindex+len(chunk) > right and charindex > 0) or chunk == '\n':
            result.append('\n' + ' '*indent)
            charindex = indent
            if chunk[:1] not in ('\n', ' '):
                result.append(chunk)
                charindex += len(chunk)
        else:
            result.append(chunk)
            charindex += len(chunk)
    return ''.join(result).rstrip()+'\n'

def plaintext_to_html(s):
    """
    @return: An HTML string that encodes the given plaintext string.
    In particular, special characters (such as C{'<'} and C{'&'})
    are escaped.
    @rtype: C{string}
    """
    s = s.replace('&', '&amp;').replace('"', '&quot;')
    s = s.replace('<', '&lt;').replace('>', '&gt;')
    return s

class RunSubprocessError(OSError):
    def __init__(self, cmd, out, err):
        OSError.__init__(self, '%s failed' % cmd[0])
        self.out = out
        self.err = err

def run_subprocess(cmd, data=None):
    """
    Execute the command C{cmd} in a subprocess.

    @param cmd: The command to execute, specified as a list
        of string.
    @param data: A string containing data to send to the
        subprocess.
    @return: A tuple C{(out, err)}.
    @raise OSError: If there is any problem executing the
        command, or if its exitval is not 0.
    """
    if isinstance(cmd, basestring):
        cmd = cmd.split()

    # Under Python 2.4+, use subprocess
    try:
        from subprocess import Popen, PIPE
        pipe = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out, err = pipe.communicate(data)
        if hasattr(pipe, 'returncode'):
            if pipe.returncode == 0:
                return out, err
            else:
                raise RunSubprocessError(cmd, out, err)
        else:
            # Assume that there was an error iff anything was written
            # to the child's stderr.
            if err == '':
                return out, err
            else:
                raise RunSubprocessError(cmd, out, err)
    except ImportError:
        pass

    # Under Python 2.3 or earlier, on unix, use popen2.Popen3 so we
    # can access the return value.
    import popen2
    if hasattr(popen2, 'Popen3'):
        pipe = popen2.Popen3(' '.join(cmd), True)
        to_child = pipe.tochild
        from_child = pipe.fromchild
        child_err = pipe.childerr
        if data:
            to_child.write(data)
        to_child.close()
        out = err = ''
        while pipe.poll() is None:
            out += from_child.read()
            err += child_err.read()
        out += from_child.read()
        err += child_err.read()
        if pipe.wait() == 0:
            return out, err
        else:
            raise RunSubprocessError(cmd, out, err)

    # Under Python 2.3 or earlier, on non-unix, use os.popen3
    else:
        to_child, from_child, child_err = os.popen3(' '.join(cmd), 'b')
        if data:
            try:
                to_child.write(data)
            # Guard for a broken pipe error
            except IOError, e:
                raise OSError(e)
        to_child.close()
        out = from_child.read()
        err = child_err.read()
        # Assume that there was an error iff anything was written
        # to the child's stderr.
        if err == '':
            return out, err
        else:
            raise RunSubprocessError(cmd, out, err)

######################################################################
## Terminal Control
######################################################################

class TerminalController:
    """
    A class that can be used to portably generate formatted output to
    a terminal.  See
    U{http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/475116}
    for documentation.  (This is a somewhat stripped-down version.)
    """
    BOL = ''             #: Move the cursor to the beginning of the line
    UP = ''              #: Move the cursor up one line
    DOWN = ''            #: Move the cursor down one line
    LEFT = ''            #: Move the cursor left one char
    RIGHT = ''           #: Move the cursor right one char
    CLEAR_EOL = ''       #: Clear to the end of the line.
    CLEAR_LINE = ''      #: Clear the current line; cursor to BOL.
    BOLD = ''            #: Turn on bold mode
    NORMAL = ''          #: Turn off all modes
    COLS = 75            #: Width of the terminal (default to 75)
    UNDERLINE = ''       #: Underline the text
    REVERSE = ''         #: Reverse the foreground & background
    BLACK = BLUE = GREEN = CYAN = RED = MAGENTA = YELLOW = WHITE = ''

    _STRING_CAPABILITIES = """
    BOL=cr UP=cuu1 DOWN=cud1 LEFT=cub1 RIGHT=cuf1 REVERSE=rev
    CLEAR_EOL=el BOLD=bold UNDERLINE=smul NORMAL=sgr0""".split()
    _COLORS = """BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE""".split()
    _ANSICOLORS = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE".split()

    #: If this is set to true, then new TerminalControllers will
    #: assume that the terminal is not capable of doing manipulation
    #: of any kind.
    FORCE_SIMPLE_TERM = False

    def __init__(self, term_stream=sys.stdout):
        # If the stream isn't a tty, then assume it has no capabilities.
        if not term_stream.isatty(): return
        if self.FORCE_SIMPLE_TERM: return

        # Curses isn't available on all platforms
        try: import curses
        except:
            # If it's not available, then try faking enough to get a
            # simple progress bar.
            self.BOL = '\r'
            self.CLEAR_LINE = '\r' + ' '*self.COLS + '\r'

        # Check the terminal type.  If we fail, then assume that the
        # terminal has no capabilities.
        try: curses.setupterm()
        except: return

        # Look up numeric capabilities.
        self.COLS = curses.tigetnum('cols')

        # Look up string capabilities.
        for capability in self._STRING_CAPABILITIES:
            (attrib, cap_name) = capability.split('=')
            setattr(self, attrib, self._tigetstr(cap_name) or '')
        if self.BOL and self.CLEAR_EOL:
            self.CLEAR_LINE = self.BOL+self.CLEAR_EOL

        # Colors
        set_fg = self._tigetstr('setf')
        if set_fg:
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, color, curses.tparm(set_fg, i) or '')
        set_fg_ansi = self._tigetstr('setaf')
        if set_fg_ansi:
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, color, curses.tparm(set_fg_ansi, i) or '')

    def _tigetstr(self, cap_name):
        # String capabilities can include "delays" of the form "$<2>".
        # For any modern terminal, we should be able to just ignore
        # these, so strip them out.
        import curses
        cap = curses.tigetstr(cap_name) or ''
        return re.sub(r'\$<\d+>[/*]?', '', cap)

    def render(self, template):
        """
        Replace each $-substitutions in the given template string with
        the corresponding terminal control string (if it's defined) or
        '' (if it's not).
        """
        return re.sub(r'\$\$|\${\w+}', self._render_sub, template)

    def _render_sub(self, match):
        s = match.group()
        if s == '$$': return s
        else: return getattr(self, s[2:-1])

