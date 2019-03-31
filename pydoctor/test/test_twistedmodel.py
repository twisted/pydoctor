from __future__ import print_function

from pydoctor.model import Class, Module, Package
from pydoctor.twistedmodel import TwistedSystem


def test_include_private():
    system = TwistedSystem()
    c = Class(system, "_private", "some doc")
    assert c.isVisible


def test_include_private_not_in_all():
    system = TwistedSystem()
    m = Module(system, "somemodule", "module doc")
    m.all = []
    c = Class(system, "_private", "some doc", m)
    assert c.isVisible


def test_doesnt_include_test_package():
    system = TwistedSystem()
    c = Class(system, "test", "some doc")
    assert c.isVisible

    p = Package(system, "test", "package doc")
    assert not p.isVisible
