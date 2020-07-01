from itertools import takewhile
from os.path import abspath, dirname, join as joinpath
from setuptools import find_packages, setup


top_dir = abspath(dirname(__file__))
with open(joinpath(top_dir, 'README.rst'), encoding='utf-8') as f:
    long_description = ''.join(
        takewhile(lambda line: not line.startswith('.. description-end'), f)
        )

setup(
    name='pydoctor',
    author='Michael Hudson-Doyle',
    author_email='micahel@gmail.com',
    maintainer='Maarten ter Huurne',
    maintainer_email='maarten@boxingbeetle.com',
    url='http://github.com/twisted/pydoctor',
    description='API doc generator.',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='MIT/X11',
    packages=find_packages(),
    package_data={
        'pydoctor': [
            'templates/*',
        ],
    },
    entry_points={
        'console_scripts': [
            'pydoctor = pydoctor.driver:main'
        ]
    },
    classifiers=[
        'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
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
        "enum34;python_version<'3.4'",
    ],
)
