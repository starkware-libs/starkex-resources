from os import path

from setuptools import find_packages, setup

# Reads the contents of your README file.
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='starkware_crypto',
    version='0.1',
    author='StarkWare Industries',
    author_email='info@starkware.co',
    url='https://starkware.co',
    packages=find_packages(),
    namespace_packages=['starkware'],
    install_requires=[
        'mpmath==1.0.0',
        'sympy==1.6',
        'ecdsa==0.16.0',
    ],
    long_description=long_description,
    package_data={
        '': ['signature/pedersen_params.json']
    },
)
