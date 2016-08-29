import click
import requests
import os
from collections import OrderedDict
from os.path import isfile
from bs4 import BeautifulSoup
from random import randint
from time import sleep
from humanfriendly.tables import format_pretty_table

# have to handle wrong symbol
# have to handle no connetion

ROOT_FOLDER = os.path.abspath(os.path.dirname(__file__))
BONDS = ROOT_FOLDER + '/bonds.csv'
STOCKS = ROOT_FOLDER + '/stocks.csv'


def formatted(raw):
    return [el.strip('\n').split(';') for el in raw]


def get_assets(fileloc):

    with open(fileloc, 'r') as f:
        f.readline()
        temp = f.readlines()

    if temp:
        assets = OrderedDict()
        for line in formatted(temp):
            assets[line[0]] = [line[1], line[2]]
    else:
        return None  # da cambiare
    return assets


def get_bond_price(isin):
    url = 'http://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/'
    url_end = '.html?lang=it'
    html = requests.get(''.join([url, isin.upper(), url_end]))
    soup = BeautifulSoup(html.text, 'html.parser')
    try:
        return float(soup.find_all('td', limit=8)[7].text.replace(',', '.'))
    except IndexError:
        print('isin sbagliato!: {}'.format(isin))
        return False


def get_stock_price(stocks):

    symbol_str = ''
    for stock in stocks:
        symbol_str += '{}+'.format(stocks[stock][0])
    url = 'http://finance.yahoo.com/d/quotes.csv?s=#&f=l1p2'
    prices = requests.get(url.replace('#', symbol_str)).text.split('\n')[:-1]
    raw = [x.split(',') for x in prices]
    polished = list(map((lambda y: [float(y[0]), y[1].replace('"', '')]), raw))
    cont = 0
    for stock in stocks:
        stocks[stock].extend(polished[cont])
        cont += 1
    return stocks


def compute_progress(price, limit):  # da finire

    if max(price, limit) == limit:  # price<limit
        gap = limit - price
        progress = gap / price
    else:  # limit<price
        gap = price - limit
        progress = gap / price
    return '{}%'.format(str(progress * 100)[:4])


def check_stocks(stocks):

    msg = ''

    msg_txt_up = '{} è salita sopra la soglia di {}, ultimo prezzo {}\n'
    msg_txt_down = '{} è scesa sotto la soglia di {}, ultimo prezzo {}\n'
    log_columns_names = [' ', 'nome', 'progresso', 'prezzo', 'variazione']
    log = []

    if stocks:
        stocks = get_stock_price(stocks)
        for stock in stocks:
            limit = stocks[stock][1]
            stock_price = stocks[stock][2]
            var = stocks[stock][3]
            stock_prefix = limit[:1]
            if stock_prefix == '+':
                stock_limit = float(limit[1:])
                progress = compute_progress(stock_price, stock_limit)
                log.append(['+', stock, progress, stock_price, var])
                if stock_price > stock_limit:
                    msg += msg_txt_up.format(stock, stock_limit, stock_price)
            else:
                stock_limit = float(limit)
                if stock_prefix == '-':
                    stock_limit = float(limit[1:])
                progress = compute_progress(stock_price, stock_limit)
                log.append(['-', stock, progress, stock_price, var])
                if stock_price < stock_limit:
                    msg += msg_txt_down.format(stock, stock_limit, stock_price)

    else:
        return'nessuna azione inserita!\n\n'

    if not msg:
        no_msg = '\nnessuna azione è scesa sotto la soglia\n\n'
        return format_pretty_table(log, log_columns_names) + no_msg

    return msg + '\n' + format_pretty_table(log, log_columns_names) + '\n\n'


def check_bonds(bonds):

    msg = ''
    log = ''
    log_columns_names = [' ', 'nome', 'progresso', 'prezzo']
    log = []
    text_up = '{0} è salita sopra la soglia di {1}, ultimo prezzo {2}\n'
    text_down = '{0} è sceso sotto la soglia di {1}, ultimo prezzo {2}\n'

    if bonds:
        for bond in bonds:
            bond_price = get_bond_price(bonds[bond][0])
            if not bond_price:
                continue
            bond_prefix = bonds[bond][1][:1]
            if bond_prefix == '+':
                bond_limit = float(bonds[bond][1][1:])
                progress = compute_progress(bond_price, bond_limit)
                log.append(['+', bond, progress, bond_price])
                if bond_price > bond_limit:
                    msg += text_up.format(bond, bonds[bond][1], bond_price)
            else:
                bond_limit = float(bonds[bond][1])
                if bond_prefix == '-':
                    bond_limit = float(bonds[bond][1][1:])
                progress = compute_progress(bond_price, bond_limit)
                log.append(['-', bond, progress, bond_price])
                if bond_price < bond_limit:
                    msg += text_down.format(bond, bonds[bond][1], bond_price)
            sleep(randint(5, 10))
    else:
        return'nessuna obbligazione inserita!\n\n'

    if not msg:
        no_msg = '\nnessuna obbgligazione è scesa sotto la soglia\n\n'
        return format_pretty_table(log, log_columns_names) + no_msg

    return msg + '\n' + format_pretty_table(log, log_columns_names)


@click.group()
def cli():

    if not isfile(BONDS):
        with open(BONDS, 'w') as f:
            f.write('nome;isin;soglia\n')
    if not isfile(STOCKS):
        with open(STOCKS, 'w') as f:
            f.write('nome;simbolo;soglia\n')


@cli.command()
@click.option('--stock', 'only_one', flag_value='stock',
              help='controlla solo le azioni')
@click.option('--bond', 'only_one', flag_value='bond',
              help='controlla solo le obbligazioni')
def get(only_one):
    '''attiva il programma'''

    if only_one == 'stock':
        click.echo('aggiorno i prezzi delle azioni\n')
        click.echo(check_stocks(get_assets(STOCKS)))

    elif only_one == 'bond':
        click.echo('aggiorno i prezzi delle obbligazioni\n')
        click.echo(check_bonds(get_assets(BONDS)))
    else:
        click.echo('aggiorno i prezzi di azioni e obbligazioni\n')
        msg = check_stocks(get_assets(STOCKS))
        msg += check_bonds(get_assets(BONDS))
        click.echo(msg)


@cli.command()
@click.option('--bond', nargs=3, type=str, default=(),
              help='obbligazione : NOME ISIN SOGLIA')
@click.option('--stock', nargs=3, type=str, default=(),
              help='azione : NOME SIMBOLO SOGLIA')
def add(bond, stock):
    ''' aggiungi un azione o obbligazione'''

    if bond:
        with open(BONDS, 'a') as f:
            f.write('{0};{1};{2}\n'.format(*bond))
    if stock:
        with open(STOCKS, 'a') as f:
            f.write('{0};{1};{2}\n'.format(*stock))


@cli.command()
@click.option('--mod', default='', help='modifica la soglia di notifica')
@click.option('--bond', default='',
              help='NOME obbligazione da rimuovere o modificare')
@click.option('--stock', default='',
              help='NOME azione da rimuovere o modificare')
def remove(mod, bond, stock):
    '''rimuovi un azione o obbligazione'''

    if bond:
        selected = BONDS
        removed = bond
        with open(BONDS, 'r') as f:
            header = f.readline()
            temp = f.readlines()

    if stock:
        selected = STOCKS
        removed = stock
        with open(STOCKS, 'r') as f:
            header = f.readline()
            temp = f.readlines()

    if mod:
        new = [el for el in formatted(temp)]
        with open(selected, 'w') as f:
            f.write(header)
            for line in new:
                if line[0] == removed:
                    f.write('{0};{1};{2}\n'.format(line[0], line[1], mod))
                else:
                    f.write('{0};{1};{2}\n'.format(*line))
    else:
        prompt = 'Vuoi davvero cancellare {}'
        if click.confirm(prompt.format(removed), default=False):

            new = [el for el in formatted(temp) if el[0] != removed]

            with open(selected, 'w') as f:
                f.write(header)
                for line in new:
                    f.write('{0};{1};{2}\n'.format(*line))


@cli.command()
def show():
    '''mostra le azioni e obbligazioni inserite'''

    with open(BONDS, 'r') as f, open(STOCKS, 'r') as d:
        text = f.read().replace(';', ' ') + '\n' + d.read().replace(';', ' ')
        click.echo_via_pager(text)


if __name__ == '__main__':
    cli()
