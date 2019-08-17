import os
import sys

from setuptools import setup, find_packages

CURRENT_PYTHON = sys.version_info[:2]
REQUIRED_PYTHON = (3, 6)

# This check and everything above must remain compatible with Python 2.7.
if CURRENT_PYTHON < REQUIRED_PYTHON:
    sys.stderr.write("""
==========================
Unsupported Python version
==========================
The module requires Python {}.{}, but you're trying to
install it on Python {}.{}.

""".format(*(REQUIRED_PYTHON + CURRENT_PYTHON)))
    sys.exit(1)


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


EXCLUDE_FROM_PACKAGES = []
REQUIREMENTS = [i.strip() for i in open(os.path.join(os.path.dirname(__file__), "requirements.txt")).readlines()]

setup(
    name='mapping_distrinet',
    version='0.1',
    python_requires='>={}.{}'.format(*REQUIRED_PYTHON),
    packages=find_packages(exclude=[]),
    url='https://github.com/atomassi/mapping_distrinet',
    download_url='https://github.com/atomassi/mapping_distrinet',
    license='MIT',
    author='atomassi',
    author_email='andrea.tomassilli@inria.fr',
    description='Various algorithms for the problem of mapping a virtual network onto the substrate network or onto a cloud network.',
    long_description=read('README.md'),
    classifiers=[
        "Programming Language :: Python",
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    dependency_links=['http://github.com/mininet/mininet/tarball/master#egg=mininet'],
    install_requires=[
        'PuLP',
        'networkx',
        'mininet',
        'numpy'
    ],
    package_data={
        'distriopt.embedding.instances': ['*.json'],
        'distriopt.packing.instances': ['*.json']
    },
    include_package_data=True,
    zip_safe=True
)
