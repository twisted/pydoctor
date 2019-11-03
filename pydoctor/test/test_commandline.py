from __future__ import print_function

import sys

from pydoctor import driver
from twisted.python.compat import NativeStringIO

from . import py2only, py3only

def geterrtext(*options):
    options = list(options)
    se = sys.stderr
    f = NativeStringIO()
    print(options)
    sys.stderr = f
    try:
        try:
            driver.main(options)
        except SystemExit:
            pass
        else:
            assert False, "did not fail"
    finally:
        sys.stderr = se
    return f.getvalue()

def test_invalid_option():
    err = geterrtext('--no-such-option')
    assert 'no such option' in err

def test_cannot_advance_blank_system():
    err = geterrtext('--make-html')
    assert 'forget an --add-package?' in err

@py2only
def test_no_systemclasses_py2():
    err = geterrtext('--system-class')
    assert 'requires an argument' in err

@py3only
def test_no_systemclasses_py3():
    err = geterrtext('--system-class')
    assert 'requires 1 argument' in err

def test_invalid_systemclasses():
    err = geterrtext('--system-class=notdotted')
    assert 'dotted name' in err
    err = geterrtext('--system-class=no-such-module.System')
    assert 'could not import module' in err
    err = geterrtext('--system-class=pydoctor.model.Class')
    assert 'is not a subclass' in err


def test_projectbasedir():
    """
    The --project-base-dir option should set the projectbasedirectory attribute
    on the options object.
    """
    value = "projbasedirvalue"
    options, args = driver.parse_args([
            "--project-base-dir", value])
    assert options.projectbasedirectory == value


def test_cache_disabled_by_default():
    """
    Intersphinx object caching is disabled by default.
    """
    parser = driver.getparser()
    (options, _) = parser.parse_args([])
    assert not options.enable_intersphinx_cache
