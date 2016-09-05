from setuptools import setup

setup(
    name='scrapper',
    version='0.3',
    py_modules=['scrapper'],
    install_requires=[
        'Click',
        'Bs4',
        'requests',
        'humanfriendly',
        'sqlalchemy',
        'flask'
    ],
    entry_points='''
        [console_scripts]
        scrapper=scrapper:cli
    ''',
)
