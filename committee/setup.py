from setuptools import find_packages, setup

setup(
    name='committee',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'aerospike==3.9.0',
        'aioredis==1.2.0',
        'fastecdsa==1.7.2',
        'marshmallow-dataclass==7.1.0',
        'marshmallow==3.2.1',
        'PyYAML==5.4',
        'requests == 2.22.0',
    ]
)
