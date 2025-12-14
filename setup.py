from setuptools import setup, find_packages

setup(
    name='flake8-multiline-equals',
    version='1.0.0',
    packages=find_packages(),
    install_requires=['flake8>=3.0.0'],
    entry_points={
        'flake8.extension': [
            'MNA001 = flake8_multiline_equals:MultilineNamedArgsCheckerPlugin',
        ],
    },
)