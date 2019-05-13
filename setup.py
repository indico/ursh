import ast
import os
import re
import sys

from setuptools import find_packages, setup


_version_re = re.compile(r'__version__\s+=\s+(.*)')


def read_requirements_file(fname):
    with open(fname, 'r') as f:
        return [dep.strip() for dep in f.readlines() if not (dep.startswith('-') or '://' in dep)]


def get_requirements():
    return read_requirements_file(os.path.join(os.path.dirname(__file__), 'requirements.txt'))


with open('ursh/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode('utf-8')).group(1)))

needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(
    name='ursh',
    version=version,
    description='A URL shortening microservice',
    url='https://github.com/indico/ursh',
    download_url='https://github.com/indico/ursh',
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(),
    install_requires=get_requirements(),
    setup_requires=[] + pytest_runner,
    tests_require=[
        'pytest',
    ],
    entry_points={
        'console_scripts': {'ursh = ursh.cli.core:cli'}
    }
)
