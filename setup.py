import setuptools
import codecs
import os

with open('README.md', 'r') as fh:
    long_description = fh.read()


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setuptools.setup(
    name='octoploy',
    version=get_version('octoploy/__init__.py'),
    author='davidgiga1993',
    author_email='david@dev-core.org',
    description='Simple kubernetes / openshift templating engine with templating, libraries, state tracking',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/davidgiga1993/octoploy',
    packages=setuptools.find_packages(),
    python_requires='>=3.8',
    install_requires=['pyyaml', 'pycryptodome'],
    entry_points={
        'console_scripts': ['octoploy=octoploy.octoploy:main'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries'
    ],
)
