#!/usr/bin/python
from distutils.core import setup

setup(
    name='pydoctor',
    version='0.5b1',
    author='Michael Hudson-Doyle',
    author_email='micahel@gmail.com',
    url='http://codespeak.net/~mwh/pydoctor/',
    description='API doc generator.',
    license='MIT/X11',
    packages=[
        'pydoctor',
        'pydoctor.templatewriter',
        'pydoctor.templatewriter.pages',
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
