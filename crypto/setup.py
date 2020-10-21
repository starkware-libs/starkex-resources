from os import path

from setuptools import find_packages, setup

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
    package_data={
        '': ['signature/pedersen_params.json']
    },
)
