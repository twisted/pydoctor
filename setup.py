#!/usr/bin/python
from distutils.core import setup

setup(
    name='pydoctor',
    version='0.6b2',
    author='Michael Hudson-Doyle',
    author_email='micahel@gmail.com',
    url='http://github.com/twisted/pydoctor',
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
    install_requires=["Twisted", "epydoc"],
    )
