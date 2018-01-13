import os
import re

from setuptools import setup


def get_version_from_src():
    with open(os.path.join("factors", "__init__.py"), mode="r") as fh:
        return re.search("__version__\s*=\s*['\"](.*?)['\"]", fh.read()).group(1)


def readme():
    with open('README.rst') as f:
        return f.read()


setup(
    name='factors',
    version=get_version_from_src(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
    description='Generates actuarial factors for premium calculations.',
    long_description=readme(),
    author='Pieter Marres',
    author_email='pmarres@oxylo.com',
    maintainer='Pieter Marres',
    maintainer_email='pmarres@oxylo.com',
    license='MIT',
    packages=['factors'],
    package_data={
        'factors': ['factors/**/*']
    },
    entry_points={
        'console_scripts': [
            'factors=factors.__main__:main'
        ]
    },
    url='https://github.com/Oxylo/factors',
    download_url='https://github.com/Oxylo/factors/archive/0.1.tar.gz',
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'numpy',  # TODO pin versions
        'pandas',
        'xlrd',
        'openpyxl',
    ],
    test_suite='pytest',
    tests_require=['pytest'],
)
