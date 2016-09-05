from os.path import abspath, dirname


def path(name):
    return '/'.join([abspath(dirname(__package__)), name])


class Const:
    DB = path('scrapper.db')
    CONFIGS = path('scrapper_config.txt')
    INVESTED = 10000
    REPAYMENT = 100
    TAX = 0.125
