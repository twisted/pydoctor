import unittest
import os

from pydoctor.qnmatch import qnmatch, translate

def test_qnmatch() -> None:

    assert(qnmatch('site.yml', 'site.yml'))

    assert(not qnmatch('site.yml', '**.site.yml'))
    assert(not qnmatch('site.yml', 'site.yml.**'))
    assert(not qnmatch('SITE.YML', 'site.yml'))
    assert(not qnmatch('SITE.YML', '**.site.yml'))

    assert(qnmatch('images.logo.png', '*.*.png'))
    assert(not qnmatch('images.images.logo.png', '*.*.png'))
    assert(not qnmatch('images.logo.png', '*.*.*.png'))
    assert(qnmatch('images.logo.png', '**.png'))
    assert(qnmatch('images.logo.png', '**.*.png'))
    assert(qnmatch('images.logo.png', '**png'))

    assert(not qnmatch('images.logo.png', 'images.**.*.png'))
    assert(not qnmatch('images.logo.png', '**.images.**.png'))
    assert(not qnmatch('images.logo.png', '**.images.**.???'))
    assert(not qnmatch('images.logo.png', '**.image?.**.???'))

    assert(qnmatch('images.logo.png', 'images.**.png'))
    assert(qnmatch('images.logo.png', 'images.**.png'))
    assert(qnmatch('images.logo.png', 'images.**.???'))
    assert(qnmatch('images.logo.png', 'image?.**.???'))

    assert(qnmatch('images.gitkeep', '**.*'))
    assert(qnmatch('output.gitkeep', '**.*'))

    assert(qnmatch('images.gitkeep', '*.**'))
    assert(qnmatch('output.gitkeep', '*.**'))

    assert(qnmatch('.hidden', '**.*'))
    assert(qnmatch('sub.hidden', '**.*'))
    assert(qnmatch('sub.sub.hidden', '**.*'))

    assert(qnmatch('.hidden', '**.hidden'))
    assert(qnmatch('sub.hidden', '**.hidden'))
    assert(qnmatch('sub.sub.hidden', '**.hidden'))

    assert(qnmatch('site.yml.Class', 'site.yml.*'))
    assert(not qnmatch('site.yml.Class.property', 'site.yml.*'))
    assert(not qnmatch('site.yml.Class.property', 'site.yml.Class'))

    assert(qnmatch('site.yml.Class.__init__', '**.__*__'))
    assert(qnmatch('site._yml.Class.property', '**._*.**'))
    assert(qnmatch('site.yml._Class.property', '**._*.**'))
    assert(not qnmatch('site.yml.Class.property', '**._*.**'))
    assert(not qnmatch('site.yml_.Class.property', '**._*.**'))
    assert(not qnmatch('site.yml.Class._property', '**._*.**'))

class TranslateTestCase(unittest.TestCase):
    def test_translate(self) -> None:
        self.assertEqual(translate('*'), r'(?s:[^\.]*?)\Z')
        self.assertEqual(translate('**'), r'(?s:.*?)\Z')
        self.assertEqual(translate('?'), r'(?s:.)\Z')
        self.assertEqual(translate('a?b*'), r'(?s:a.b[^\.]*?)\Z')
        self.assertEqual(translate('[abc]'), r'(?s:[abc])\Z')
        self.assertEqual(translate('[]]'), r'(?s:[]])\Z')
        self.assertEqual(translate('[!x]'), r'(?s:[^x])\Z')
        self.assertEqual(translate('[^x]'), r'(?s:[\^x])\Z')
        self.assertEqual(translate('[x'), r'(?s:\[x)\Z')

class FnmatchTestCase(unittest.TestCase):

    def check_match(self, filename, pattern, should_match=True, fn=qnmatch) -> None: # type: ignore
        if should_match:
            self.assertTrue(fn(filename, pattern),
                         "expected %r to match pattern %r"
                         % (filename, pattern))
        else:
            self.assertFalse(fn(filename, pattern),
                         "expected %r not to match pattern %r"
                         % (filename, pattern))

    def test_fnmatch(self) -> None:
        check = self.check_match
        check('abc', 'abc')
        check('abc', '?*?')
        check('abc', '???*')
        check('abc', '*???')
        check('abc', '???')
        check('abc', '*')
        check('abc', 'ab[cd]')
        check('abc', 'ab[!de]')
        check('abc', 'ab[de]', False)
        check('a', '??', False)
        check('a', 'b', False)

        # these test that '\' is handled correctly in character sets;
        # see SF bug #409651
        check('\\', r'[\]')
        check('a', r'[!\]')
        check('\\', r'[!\]', False)

        # test that filenames with newlines in them are handled correctly.
        # http://bugs.python.org/issue6665
        check('foo\nbar', 'foo*')
        check('foo\nbar\n', 'foo*')
        check('\nfoo', 'foo*', False)
        check('\n', '*')

    def test_mix_bytes_str(self) -> None:
        self.assertRaises(TypeError, qnmatch, 'test', b'*')
        self.assertRaises(TypeError, qnmatch, b'test', '*')
        self.assertRaises(TypeError, qnmatch, 'test', b'*')
        self.assertRaises(TypeError, qnmatch, b'test', '*')

    def test_fnmatchcase(self) -> None:
        check = self.check_match
        check('abc', 'abc', True, qnmatch)
        check('AbC', 'abc', False, qnmatch)
        check('abc', 'AbC', False, qnmatch)
        check('AbC', 'AbC', True, qnmatch)

        check('usr/bin', 'usr/bin', True, qnmatch)
        check('usr\\bin', 'usr/bin', False, qnmatch)
        check('usr/bin', 'usr\\bin', False, qnmatch)
        check('usr\\bin', 'usr\\bin', True, qnmatch)

    def test_case(self) -> None:
        check = self.check_match
        check('abc', 'abc')
        check('AbC', 'abc', False)
        check('abc', 'AbC', False)
        check('AbC', 'AbC')
