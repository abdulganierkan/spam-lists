# -*- coding: utf-8 -*-
from codecs import open
import re
import sys

from setuptools import setup


def read_attributes(string, *names):
    regex_tpl = r'^__{}__\s*=\s*[\'"]([^\'"]*)[\'"]'

    def read(name):
        regex = regex_tpl.format(name)
        return re.search(regex, string, re.MULTILINE).group(1)

    return [read(n) for n in names]


with open('spam_lists/__init__.py', 'r') as fd:
    content = fd.read()
    name, version, author, _license = read_attributes(
        content,
        'title',
        'version',
        'author',
        'license'
    )

with open('README.rst', 'r', 'utf-8') as f:
    readme = f.read()


install_requires = [
    'future',
    'requests',
    'tldextract',
    'validators',
    'dnspython'
]

tests_require = ['nose-parameterized']

version = sys.version_info

if version < (3, 3):
    install_requires += ['ipaddress']
    tests_require += ['mock']

if version < (3, 2):
    install_requires += ['cachetools']

if version < (2, 7, 9):
    # request[security] extras
    install_requires += ['ndg-httpsclient']

setup(
    name=name,
    version=version,
    description='Web address blacklist/whitelist library for Python',
    long_description=readme,
    author=author,
    author_email='piotr.rusin88@gmail.com',
    url='https://github.com/piotr-rusin/spam-lists',
    packages=['spam_lists', 'test', 'test.integration', 'test.unit'],
    install_requires=install_requires,
    license=_license,
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
    ),
    keywords=('spam dnsbl surbl google-safe-browsing-api '
              'spamhaus whitelist blacklist'),
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
    },
)
