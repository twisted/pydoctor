mkdir -p build/manman
argparse-manpage --module pydoctor.options --function get_parser \
    --author 'Michael Hudson and other contributors' \
    --project-name pydoctor --prog pydoctor \
    --url https://pypi.org/project/pydoctor \
    --version $(python3 -c 'from pydoctor import __version__; print(__version__)') \
    --description 'API documentation generator for Python' \
    --output build/man/pydoctor.1
