try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'name': 'factors',
    'description': 'Generates actuarial factors for premium calculations.',
    'author': 'Pieter Marres',
    'author_email': 'pmarres@oxylo.com'
}

setup(**config)
