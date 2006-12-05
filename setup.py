from distutils.core import setup

setup(
    name='pydoctor',
    version='0.2',
    author='Michael Hudson',
    author_email='mwh@python.net',
    url='http://codespeak.net/svn/user/mwh/pydoctor/trunk',
    description='API doc generator.',
    packages=[
        'pydoctor',
        'pydoctor.nevowhtml',
        ],
    package_data={
        'pydoctor': [
            'templates/*',
            ],
        },
    scripts=[
        'bin/pydoctor',
        ],
    )
