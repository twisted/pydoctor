#!/usr/bin/python
import sys

from setuptools import find_packages, setup

setup(
    name='pydoctor',
    author='Michael Hudson-Doyle',
    author_email='micahel@gmail.com',
    url='http://github.com/twisted/pydoctor',
    description='API doc generator.',
    license='MIT/X11',
    packages=find_packages(),
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
    use_incremental=True,
    setup_requires=["incremental"],
    install_requires=[
        "incremental",
        "appdirs",
        "CacheControl[filecache]",
        "Twisted",
        "requests",
        "six",
        "astor",
    ],
)
