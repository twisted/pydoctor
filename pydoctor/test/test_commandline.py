from pydoctor import driver
import sys, cStringIO

def geterrtext(*options):
    options = list(options)
    se = sys.stderr
    f = cStringIO.StringIO()
    print options
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

def test_no_do_nothing():
    err = geterrtext()
    assert "this invocation isn't going to do anything" in err

def test_cannot_advance_blank_system():
    err = geterrtext('--make-html')
    assert 'forget an --add-package?' in err

def test_invalid_systemclasses():
    err = geterrtext('--system-class')
    assert 'requires an argument' in err
    err = geterrtext('--system-class=notdotted')
    assert 'dotted name' in err
    err = geterrtext('--system-class=no-such-module.System')
    assert 'could not import module' in err
    err = geterrtext('--system-class=pydoctor.model.Class')
    assert 'is not a subclass' in err
