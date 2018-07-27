import os
import re

from setuptools import find_packages, setup


def get_version_from_src():
    with open(os.path.join("factors", "__init__.py"), mode="r") as fh:
        return re.search("__version__\s*=\s*['\"](.*?)['\"]", fh.read()).group(1)


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='factors',
    version=get_version_from_src(),
    packages=find_packages(),
    # package_data={
    #     "factors.data": ["*.xls", "*.xlsx"]
    # },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'factors=factors.__main__:main'
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    description='Generates actuarial factors for premium calculations.',
    long_description=readme(),
    author='Pieter Marres',
    author_email='pmarres@oxylo.com',
    maintainer='Pieter Marres',
    maintainer_email='pmarres@oxylo.com',
    license='MIT',
    url='https://github.com/Oxylo/factors',
    download_url='https://github.com/Oxylo/factors/archive/0.1.tar.gz',
    zip_safe=False,
    install_requires=[
        'pandas>=0.23.3',
        'xlrd>=1.1.0',
        'openpyxl>=2.5.4',
    ],
    test_suite='pytest',
    tests_require=['pytest'],
)
