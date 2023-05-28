import argparse
import configparser
import shutil
import sys
import contextlib
import io
import os
import tarfile
import tempfile
import time
import datetime
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, cast
import tempfile

import pydoctor.driver
import requests
import appdirs

from pydoctor.utils import temporary_filename

def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
                            description="Build python documentation from pypi repositories", 
                            formatter_class=argparse.ArgumentDefaultsHelpFormatter, 
                            prog='python3 -m pydocor.pypi')
    parser.add_argument('--package', metavar="PACKAGE", 
                        help="Builds the selected package from PyPI, can repeat to build multiple packages. ",
                        action='extend', dest='packages', required=True, nargs='+')
    parser.add_argument('--options', dest='pydoctor_options',
                        action='extend', default=[], nargs='+',
                        help="Use the given pydoctor option, can repeat to to add more options. "
                             "Format should be the same as in the pydoctor config file.", )
    parser.add_argument('--html-output', metavar="PATH", dest='build_dir',
                        type=Path, default='apidocs', help="Output directory.", )
    parser.add_argument('--build-timeout', metavar="MINUTES", dest='build_timeout',
                        type=int, default=120, help="Build timeout, in minutes.",)
    parser.add_argument('--verbose', action='store_true', dest='verbose', default=False,
                        help="Print pydoctor output",)
    parser.add_argument('--cache-max-age', metavar='HOURS', help="TTL of downloaded sources.", 
                        type=int, default=480, dest='cache_max_age')
    return parser

class Options(argparse.Namespace):
    build_dir: Path
    build_timeout: int
    packages: List[str]
    options: List[str]
    verbose: bool
    cache_max_age: int

def fetch_package_info(package_name: str) -> Dict[str, Any]:
    return cast('Dict[str, Any]', requests.get(f'https://pypi.org/pypi/{package_name}/json',
            headers={'User-Agent': 'pydoctor'}).json())

def fetch_source(package_name:str, 
                 version: Optional[str], 
                 sources: Path) -> Dict[str, Any]:
    """
    Download a package sources if we don't already have them on disk.

    Returns the package infos as returned by fetch_package_info.
    """
    package_info = fetch_package_info(package_name)
    version = version or package_info['info']['version']
    sourceid = f'{package_name}-{version}'

    if (not (sources / sourceid).exists()):

        print(f'[-] downloading {package_name}=={version}')

        source_packages = [
            p for p in package_info['releases'][version] if p['packagetype'] == 'sdist'
        ]
        assert len(source_packages) > 0

        if len(source_packages) > 1:
            print(
                f"[!] {package_name} returned multiple source distributions, we're just using the first one"
            )

        source_package = source_packages[0]

        filename = source_package['filename']
        assert '/' not in filename  # for security

        download_dir = Path(tempfile.mkdtemp(prefix='pydoctor.pypi'))
        try:
            archive_path = download_dir / filename

            with requests.get(source_package['url'], stream=True) as r: 
                with open(archive_path, 'wb') as f: #type:ignore[assignment]
                    shutil.copyfileobj(r.raw, f)

            if filename.endswith('.tar.gz'):
                tf = tarfile.open(archive_path)
                for member in tf.getmembers():
                    # TODO: check that path is secure (doesn't start with /, doesn't contain ..)
                    if '/' in member.name:
                        member.name = member.name.split('/', maxsplit=1)[1]
                    else:
                        member.name = '.'
                tf.extractall(sources / sourceid)
            
            elif filename.endswith('.zip'):
                with zipfile.ZipFile(archive_path) as zf:
                    for info in zf.infolist():
                        # TODO: check that path is secure (doesn't start with /, doesn't contain ..)
                        if '/' in info.filename.rstrip('/'):
                            info.filename = info.filename.split('/', maxsplit=1)[1]
                        else:
                            info.filename = './'
                        zf.extract(info, sources / sourceid)
            else:
                raise RuntimeError(f'unknown python source dist archive format: {filename}')
        
        finally:
            shutil.rmtree(download_dir.as_posix())
    
    return package_info

def find_packages(path: Path, package_name: str) -> List[Path]:
    package_name = package_name.lower()

    # we don't want to execute setup.py, so we firstly check setup.cfg

    setup_cfg = path / 'setup.cfg'
    if setup_cfg.exists():
        parser = configparser.ConfigParser()
        parser.read(setup_cfg)
        package_dir = parser.get('options', 'package_dir', fallback=None)
        if package_dir is not None:
            package_dir = package_dir.strip()
            if package_dir.startswith('='):
                package_dir = package_dir.lstrip('= ')
                # TODO: ensure path is safe
                if (path / package_dir / package_name / '__init__.py').exists():
                    return [path / package_dir / package_name]
            else:
                print(f"[!] options.package_dir in {package_name}'s setup.cfg doesn't start with =")

    # TODO: Parse the AST of setup.py and extract packages list

    # we couldn't find the package via setup.cfg so we fallback to educated guesses
    # TODO: ensure this behaves likes find_packages()

    if (path / package_name / '__init__.py').exists():
        return [path / package_name]

    if (path / 'src' / package_name / '__init__.py').exists():
        return [path / 'src' / package_name]

    if (path / (package_name + '.py')).exists():
        # single-file package (e.g. Bottle)
        return [path / (package_name + '.py')]

    packages = []

    for subpath in path.iterdir():
        if subpath.is_dir():
            if (subpath / '__init__.py').exists():
                packages.append(subpath)
    
    # Filter 'test' and 'tests' packages
    packages = [p for p in packages if p.name not in ['test', 'tests']]
    
    return packages

def run_pydoctor(package_names:Sequence[str], 
                    versions: Dict[str, str], 
                    sources: Path, 
                    dist: Path, 
                    args: List[str],
                    verbose: bool=False) -> int:
    to_be_documented = []
    
    for package_name in package_names:
        version = versions[package_name]
        sourceid = f'{package_name}-{version}'
        
        if not (sources / sourceid).exists():
            print(f'[!] missing source code for {sourceid}')
            return -1
        
        package_paths = list(find_packages(sources / sourceid, package_name))

        if len(package_paths) == 0:
            print(
                '[!] failed to determine package directory for', sources / sourceid
            )
            return -1

        if len(package_paths) > 1:
            print(
                f"[!] found multiple packages for {package_name} ({package_paths}), we're just using the first one"
            )

        to_be_documented.append(str(package_paths[0]))
            
    # generating args
    _args = args + [
                f'--html-output={dist}',
                f'--project-base-dir={sources}',
                '--quiet', 
            ] + to_be_documented
        
    _f = io.StringIO()

    code:int = -1

    with contextlib.redirect_stdout(_f):
        code = pydoctor.driver.main(_args)
    
    _pydoctor_output = _f.getvalue()
    nb_messages = len(_pydoctor_output.splitlines())
    print(f'[-] got {nb_messages} messages')
    if verbose and nb_messages>0:
        print(_pydoctor_output)
    return code

def cleanup_cache_dir(sources:Path, cache_ttl:int):
    # cache_ttl in hours
    now = datetime.datetime.now()
    for entry in sources.iterdir():
        try:
            then = datetime.datetime.fromtimestamp((entry/'index.html').stat().st_mtime)
            if (now-then) > datetime.timedelta(hours=cache_ttl):
                shutil.rmtree(entry, ignore_errors=True)
        except Exception:
            pass

def main(args: Sequence[str] = sys.argv[1:]) -> int:
    options = cast(Options, get_parser().parse_args(args))
    sources = Path(appdirs.user_cache_dir('pydoctor.pypi'))
    sources.mkdir(exist_ok=True, parents=True)
    cleanup_cache_dir(sources, options.cache_max_age)

    # Figure the packages list we want to build the documentation for
    assert options.packages is not None
    package_list = []
    versions: Dict[str, str] = {}
    
    for _pack in options.packages:
        parts = _pack.split('==', 1)
        package_list.append(parts[0])
        if len(parts)>1:
            versions[parts[0]] = parts[1]

    # 1. fetch sources

    print('[+] fetching sources...')
    package_infos = {}
    
    pydoctor_options = options.pydoctor_options or []

    for package_name in package_list:
        pkg_info = fetch_source(package_name, 
                                versions.get(package_name), 
                                sources)
        package_infos[package_name] = pkg_info
        versions.setdefault(package_name, pkg_info['info']['version'])

    # 2. generate docs with pydoctor

    print('[+] generating docs...')
    dist = options.build_dir
    dist.mkdir(exist_ok=True)

    with temporary_filename('pypi.ini') as config_file:

        if pydoctor_options:
            with open(config_file, 'w') as f:
                f.write('[pydoctor]\n')
                for option in pydoctor_options:
                    f.write(option); f.write('\n')

            arguments = [f"--config={config_file}"]
        else:
            arguments = []
        
        then = time.time()
        code =  run_pydoctor(package_list, 
            versions, 
            sources=sources, 
            dist=dist, 
            args=arguments, 
            verbose=options.verbose)
        now = time.time()
        
        if code!=-1:
            delta = now-then
            if delta>120:
                print(f'[+] took {round(delta/60, 2)} minutes')
            else:
                print(f'[+] took {round(delta, 2)} seconds')
        return code

if __name__ == "__main__":
    main()