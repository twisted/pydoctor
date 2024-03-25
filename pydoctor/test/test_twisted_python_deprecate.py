
import re
from typing import Type

from pydoctor import model
from pydoctor.stanutils import flatten_text, html2stan
from pydoctor.test import CapSys, test_templatewriter
from pydoctor.test.test_astbuilder import fromText, DeprecateSystem

import pytest

_html_template_with_replacement = r'(.*){name} was deprecated in {package} {version}; please use {replacement} instead\.(.*)'
_html_template_without_replacement = r'(.*){name} was deprecated in {package} {version}\.(.*)'

twisted_deprecated_systemcls_param = pytest.mark.parametrize(
    'systemcls', (model.System, # system with all extensions enabled
                  DeprecateSystem, # system with deprecated extension only
                 )
    )
@twisted_deprecated_systemcls_param
def test_twisted_python_deprecate(capsys: CapSys, systemcls: Type[model.System]) -> None:
    """
    It recognizes Twisted deprecation decorators and add the
    deprecation info as part of the documentation.
    """

    # Adjusted from Twisted's tests at
    # https://github.com/twisted/twisted/blob/3bbe558df65181ed455b0c5cc609c0131d68d265/src/twisted/python/test/test_release.py#L516
    system = systemcls()
    system.options.verbosity = -1
    
    mod = fromText(
        """
        from twisted.python.deprecate import deprecated, deprecatedProperty
        from incremental import Version
        @deprecated(Version('Twisted', 15, 0, 0), 'Baz')
        def foo():
            'docstring'
        from twisted.python import deprecate
        import incremental
        @deprecate.deprecated(incremental.Version('Twisted', 16, 0, 0))
        def _bar():
            'should appear'
        from twisted.python.versions import Version as AliasVersion
        @deprecated(AliasVersion('Twisted', 14, 2, 3), replacement='stuff')
        class Baz:
            @deprecatedProperty(AliasVersion('Twisted', 'NEXT', 0, 0), replacement='faam')
            @property
            def foom(self):
                ...
            @property
            def faam(self):
                ...
        class stuff: ...
        """, system=system, modname='mod')

    mod_html_text = flatten_text(html2stan(test_templatewriter.getHTMLOf(mod)))
    class_html_text = flatten_text(html2stan(test_templatewriter.getHTMLOf(mod.contents['Baz'])))

    assert capsys.readouterr().out == ''

    assert 'docstring' in mod_html_text
    assert 'should appear' in mod_html_text

    assert re.match(_html_template_with_replacement.format(
        name='foo', package='Twisted', version=r'15\.0\.0', replacement='Baz'
    ), mod_html_text, re.DOTALL), mod_html_text
    assert re.match(_html_template_without_replacement.format(
        name='_bar', package='Twisted', version=r'16\.0\.0'
    ), mod_html_text, re.DOTALL), mod_html_text

    _class = mod.contents['Baz']
    assert len(_class.extra_info)==1
    assert re.match(_html_template_with_replacement.format(
        name='Baz', package='Twisted', version=r'14\.2\.3', replacement='stuff'
    ), flatten_text(_class.extra_info[0].to_stan(mod.docstring_linker)).strip(), re.DOTALL)

    assert re.match(_html_template_with_replacement.format(
        name='Baz', package='Twisted', version=r'14\.2\.3', replacement='stuff'
    ), class_html_text, re.DOTALL), class_html_text

    assert re.match(_html_template_with_replacement.format(
        name='foom', package='Twisted', version=r'NEXT', replacement='faam'
    ), class_html_text, re.DOTALL), class_html_text

@twisted_deprecated_systemcls_param
def test_twisted_python_deprecate_arbitrary_text(capsys: CapSys, systemcls: Type[model.System]) -> None:
    """
    The deprecated object replacement can be given as a free form text as well, it does not have to be an identifier or an object.
    """
    system = systemcls()
    system.options.verbosity = -1
    
    mod = fromText(
    """
    from twisted.python.deprecate import deprecated
    from incremental import Version
    @deprecated(Version('Twisted', 15, 0, 0), replacement='just use something else')
    def foo(): ...
    """, system=system, modname='mod')

    mod_html = test_templatewriter.getHTMLOf(mod)

    assert not capsys.readouterr().out
    assert 'just use something else' in mod_html

@twisted_deprecated_systemcls_param
def test_twisted_python_deprecate_security(capsys: CapSys, systemcls: Type[model.System]) -> None:
    system = systemcls()
    system.options.verbosity = -1
    
    mod = fromText(
    """
    from twisted.python.deprecate import deprecated
    from incremental import Version
    @deprecated(Version('Twisted\\n.. raw:: html\\n\\n   <script>alert(1)</script>', 15, 0, 0), 'Baz')
    def foo(): ...
    @deprecated(Version('Twisted', 16, 0, 0), replacement='\\n.. raw:: html\\n\\n   <script>alert(1)</script>')
    def _bar(): ...
    """, system=system, modname='mod')

    mod_html = test_templatewriter.getHTMLOf(mod)

    assert capsys.readouterr().out == '''mod:4: Invalid package name: 'Twisted\\n.. raw:: html\\n\\n   <script>alert(1)</script>'
''', capsys.readouterr().out
    assert '<script>alert(1)</script>' not in mod_html

@twisted_deprecated_systemcls_param
def test_twisted_python_deprecate_corner_cases(capsys: CapSys, systemcls: Type[model.System]) -> None:
    """
    It does not crash and report appropriate warnings while handling Twisted deprecation decorators.
    """
    system = systemcls()
    system.options.verbosity = -1
    
    mod = fromText(
        """
        from twisted.python.deprecate import deprecated, deprecatedProperty
        from incremental import Version
        # wrong incremental.Version() call (missing micro)
        @deprecated(Version('Twisted', 15, 0), 'Baz')
        def foo():
            'docstring'

        # wrong incremental.Version() call (argument should be 'NEXT')
        @deprecated(Version('Twisted', 'latest', 0, 0))
        def _bar():
            'should appear'
        
        # wrong deprecated() call (argument should be incremental.Version() call)
        @deprecated('14.2.3', replacement='stuff')
        class Baz:
            
            # bad deprecation text: replacement not found
            @deprecatedProperty(Version('Twisted', 'NEXT', 0, 0), replacement='notfound')
            @property
            def foom(self):
                ...
            
            # replacement as callable works
            @deprecatedProperty(Version('Twisted', 'NEXT', 0, 0), replacement=Baz.faam)
            @property
            def foum(self):
                ...
            @property
            def faam(self):
                ...
        class stuff: ...
        """, system=system, modname='mod')

    test_templatewriter.getHTMLOf(mod)
    class_html_text = flatten_text(html2stan(test_templatewriter.getHTMLOf(mod.contents['Baz'])))

    assert capsys.readouterr().out=="""mod:5: missing a required argument: 'micro'
mod:10: Invalid call to incremental.Version(), 'major' should be an int or 'NEXT'.
mod:15: Invalid call to twisted.python.deprecate.deprecated(), first argument should be a call to incremental.Version()
mod:20: Cannot find link target for "notfound"
""", capsys.readouterr().out

    assert re.match(_html_template_with_replacement.format(
        name='foom', package='Twisted', version='NEXT', replacement='notfound'
    ), class_html_text, re.DOTALL), class_html_text

    assert re.match(_html_template_with_replacement.format(
        name='foum', package='Twisted', version='NEXT', replacement='mod.Baz.faam'
    ), class_html_text, re.DOTALL), class_html_text


@twisted_deprecated_systemcls_param
def test_twisted_python_deprecate_else_branch(capsys: CapSys, systemcls: Type[model.System]) -> None:
    """
    When @deprecated decorator is used within the else branch of a if block and the same name is defined
    in the body branch, the name is not marked as deprecated.
    """

    mod = fromText('''
    if sys.version_info>(3.8):
        def foo():
            ...
        
        class Bar:
            ...
    else:
        from incremental import Version
        @twisted.python.deprecate.deprecated(Version('python', 3, 8, 0), replacement='just use newer python version')
        def foo():
            ...
        @twisted.python.deprecate.deprecated(Version('python', 3, 8, 0), replacement='just use newer python version')
        class Bar:
            ...
    ''', systemcls=systemcls)

    assert not capsys.readouterr().out
    assert 'just use newer python version' not in test_templatewriter.getHTMLOf(mod.contents['foo'])
    assert 'just use newer python version' not in test_templatewriter.getHTMLOf(mod.contents['Bar'])