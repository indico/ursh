import ast
import re
import sys

from pip.req import parse_requirements
from setuptools import find_packages, setup


_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('ursh/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode('utf-8')).group(1)))

requirements = [str(x.req) for x in parse_requirements('requirements.txt', session=False)]
needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(
    name='ursh',
    version=version,
    description='A URL shortening microservice',
    url='https://github.com/nurav/ursh',
    download_url='https://github.com/nurav/ursh',
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(),
    install_requires=requirements,
    setup_requires=[] + pytest_runner,
    tests_require=[
        'pytest',
    ],
)
