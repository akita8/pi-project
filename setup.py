from setuptools import setup

setup(
    name='scrapper',
    version='0.1',
    py_modules=['scrapper'],
    install_requires=[
        'Click',
        'Bs4',
        'requests'
    ],
    entry_points='''
        [console_scripts]
        scrapper=scrapper:cli
    ''',
)
