#!/usr/bin/python
import sys

if sys.version_info > (3, 0):
    raise Exception(("PyDoctor does not yet work on Python 3. Please see "
                     "https://github.com/twisted/pydoctor/issues/96 for "
                     "the tracking ticket for work on this."))

from setuptools import setup

setup(
    name='pydoctor',
    version='16.3.0',
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
    classifiers=[
        'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Documentation',
        'Topic :: Software Development :: Documentation',
    ],
    install_requires=["Twisted", "epydoc"],
)
