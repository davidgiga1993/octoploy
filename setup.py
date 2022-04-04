import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='octoploy',
    version='1.0.8',
    author='davidgiga1993',
    author_email='david@dev-core.org',
    description='Simple kubernetes / openshift templating engine with state tracking, backups and more',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/davidgiga1993/octoploy',
    packages=setuptools.find_packages(),
    install_requires=['pyyaml'],
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
