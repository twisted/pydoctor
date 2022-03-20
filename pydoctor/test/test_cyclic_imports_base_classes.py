"""
This test case is in its own file because it requires the
PYTHONHASHSEED=0 environment variable. See issue #482.
"""

import os
import subprocess
import sys

def test_cyclic_imports_base_classes() -> None:
    if sys.platform == 'win32':
        # Running this script with the following subprocess call fails on Windows
        # with an ImportError that isn't actually related to what we want to test.
        # So we just skip for Windows.
        return

    process = subprocess.Popen(
        [sys.executable, os.path.basename(__file__)],
        env={'PYTHONHASHSEED': '0'},
        cwd=os.path.dirname(__file__),
    )
    assert process.wait() == 0


if __name__ == '__main__':
    from test_packages import processPackage, model # type: ignore

    assert os.environ['PYTHONHASHSEED'] == '0'

    def consistent_hash(self: model.Module) -> int:
        return hash(self.name)

    if model.Module.__hash__ == object.__hash__:
        model.Module.__hash__ = consistent_hash

    system = processPackage('cyclic_imports_base_classes')
    b_cls = system.allobjects['cyclic_imports_base_classes.b.B']
    assert isinstance(b_cls, model.Class)
    assert b_cls.baseobjects == [system.allobjects['cyclic_imports_base_classes.a.A']]
