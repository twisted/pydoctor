from pydoctor.test.epydoc.test_epytext2html import epytext2node

def test_nested_markup() -> None:
    """
    The Epytext nested inline markup are correctly transformed to L{docutils} nodes. 
    """
    doc = '''
        I{B{Inline markup} may be nested; and
        it may span} multiple lines.
        '''
    expected = '''<document source="epytext">
    <paragraph>
        <emphasis>
            <strong>
                Inline markup
             may be nested; and it may span
         multiple lines.
'''
    
    assert epytext2node(doc).pformat() == expected

    doc = '''
        It becomes a little bit complicated with U{B{custom} links <https://google.ca>}
        '''
    expected = '''<document source="epytext">
    <paragraph>
        It becomes a little bit complicated with 
        <reference internal="False" refuri="https://google.ca">
            <strong>
                custom
             links
'''
    
    assert epytext2node(doc).pformat() == expected

    doc = '''
        It becomes a little bit complicated with L{B{custom} links <twisted.web()>}
        '''
    expected = '''<document source="epytext">
    <paragraph>
        It becomes a little bit complicated with 
        <title_reference refuri="twisted.web">
            <strong>
                custom
             links
'''
    
    assert epytext2node(doc).pformat() == expected
