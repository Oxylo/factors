try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages


def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='factors',
    version='0.1',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
    description='Generates actuarial factors for premium calculations.',
    long_description=readme(),
    author='Pieter Marres',
    author_email='pmarres@oxylo.com',
    license='MIT',
    packages=find_packages(),
    url='https://github.com/Oxylo/factors',
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'numpy',
        'pandas',
        'xlrd',
        'openpyxl',
    ],
    test_suite='nose.collector',
    tests_require=['nose'],
)
