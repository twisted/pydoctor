
import re
from pydoctor import deprecate
from pydoctor.stanutils import flatten_text, html2stan
from pydoctor.test import CapSys, test_templatewriter
from pydoctor.test.test_astbuilder import fromText


def test_twisted_python_deprecate(capsys: CapSys) -> None:
    """
    It recognizes Twisted deprecation decorators and add the
    deprecation info as part of the documentation.
    """

    # Adjusted from Twisted's tests at
    # https://github.com/twisted/twisted/blob/3bbe558df65181ed455b0c5cc609c0131d68d265/src/twisted/python/test/test_release.py#L516
    system = deprecate.System()
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
        @deprecated(Version('Twisted', 14, 2, 3), replacement='stuff')
        class Baz:
            @deprecatedProperty(Version('Twisted', 'NEXT', 0, 0), replacement='faam')
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

    assert not capsys.readouterr().out
    assert not capsys.readouterr().err

    _html_template_with_replacement = r'(.*){name} was deprecated in {package} {version}; please use {replacement} instead\.(.*)'
    _html_template_without_replacement = r'(.*){name} was deprecated in {package} {version}\.(.*)'
    
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
    ), flatten_text(_class.extra_info[0].to_stan(mod.docstring_linker, False)).strip(), re.DOTALL)

    assert re.match(_html_template_with_replacement.format(
        name='Baz', package='Twisted', version=r'14\.2\.3', replacement='stuff'
    ), class_html_text, re.DOTALL), class_html_text

    assert re.match(_html_template_with_replacement.format(
        name='foom', package='Twisted', version=r'NEXT', replacement='faam'
    ), class_html_text, re.DOTALL), class_html_text
