"""
AWS SNS Validator for Digital Marketplace apps.
"""
import re
import ast
from setuptools import setup, find_packages


_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('dm_validate_sns/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    name='ccs-digitalmarketplace-validate-sns',
    version=version,
    url='https://github.com/tim-s-ccs/digitalmarketplace-validate-sns',
    license='MIT',
    author='CCS Developers',
    description='AWS SNS Validator for Digital Marketplace apps.',
    long_description=__doc__,
    packages=find_packages(),
    package_data={'dm_validate_sns': ['py.typed']},
    include_package_data=True,
    install_requires=[
        'oscrypto>=1.3.0',
    ],
    python_requires="~=3.9",
)
