#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['Click>=7.0', ]

test_requirements = ['pytest>=3', ]

setup(
    author="Pieter Marres",
    author_email='pmarres@quantsense.io',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Making pension pring DNB scenarios.",
    entry_points={
        'console_scripts': [
            'factors=factors.cli:main',
        ],
    },
    install_requires=requirements,
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='factors',
    name='factors',
    packages=find_packages(include=['factors', 'factors.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/pmarres/factors',
    version='0.1.0',
    zip_safe=False,
)
