import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='ok8deploy',
    version='1.0.4',
    author='davidgiga1993',
    author_email='david@dev-core.org',
    description='Simple Openshift / K8 template engine with state tracking',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/davidgiga1993/OpenK8Deploy',
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': ['ok8deploy=ok8deploy.ok8deploy:main'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries'
    ],
)
