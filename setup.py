import operast
from setuptools import find_packages, setup


setup(
    name='operast',
    version=operast.__version__,
    packages=find_packages(),
    install_requires=[
        'astpretty',
        'typing-extensions'
    ],
    extras_require={
        'dev': ['mypy',
                'pytest',
                'pytest-cov',
                'sphinx',
                'coverage',
                'mypy-extensions',
                'hypothesis']
    }
)
