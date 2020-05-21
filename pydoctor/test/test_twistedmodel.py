from __future__ import print_function

from pydoctor.model import Class, Module, Package
from pydoctor.twistedmodel import TwistedSystem


def test_include_private():
    system = TwistedSystem()
    c = Class(system, "_private")
    assert c.isVisible


def test_include_private_not_in_all():
    system = TwistedSystem()
    m = Module(system, "somemodule")
    m.all = []
    c = Class(system, "_private", m)
    assert c.isVisible


def test_doesnt_include_test_package():
    system = TwistedSystem()
    c = Class(system, "test")
    assert c.isVisible

    p = Package(system, "test")
    assert not p.isVisible
