"""Early validation of --template-dir (issue #857)."""
from pydoctor.test.test_commandline import geterrtext


def test_invalid_template_dir_fails_early() -> None:
    """
    An invalid --template-dir should fail before semantic analysis.
    """
    err = geterrtext(
        '--template-dir=/definitely/not/a/real/template/dir',
        'pydoctor/test/testpackages/basic/',
    )
    assert 'Template folder do not exist or is not a directory' in err
