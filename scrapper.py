import click
import requests
import os
import datetime
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
INVESTED = 10000
REPAYMENT = 100
TAX = 0.125


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


def get_bond_data(isin):
    '''
        data keys:
        Prezzo ufficiale, Numero Contratti, Lotto Minimo, Min Oggi,
        Valuta di negoziazione, Max Oggi, Valuta di liquidazione,
        Min Anno, Data Ultima Cedola Pagata, Max Anno, Tasso Prossima Cedola,
        Tipo Bond, Scadenza, Codice Isin, Apertura, Mercato, Volume Ultimo:,
        Tipologia, Volume totale
    '''
    url = 'http://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/'
    url_end = '.html?lang=it'
    try:
        html = requests.get(''.join([url, isin.upper(), url_end]))
    except requests.exceptions.ConnectionError:
        raise SystemExit
    soup = BeautifulSoup(html.text, 'html.parser')

    raw_data = soup.find_all('td')
    keys = [el.text for i, el in enumerate(raw_data)
            if i > 5 and i < 44 and i % 2 == 0]
    values = [el.text for i, el in enumerate(raw_data)
              if i > 5 and i < 44 and i % 2 != 0]
    data = dict(zip(keys, values))
    try:
        price = float(data['Prezzo ufficiale'].replace(',', '.'))
        unpolished_date = data['Scadenza'].split('/')
        year = int('20'+unpolished_date[2])
        month = int(unpolished_date[1])
        day = int(unpolished_date[0])
        date = datetime.date(year, month, day)
        max_year = data['Max Anno']
        min_year = data['Min Anno']
        return (price, date, max_year, min_year)
    except KeyError:
        print('ATTENZIONE isin sbagliato: {}\n'.format(isin))
        return (None, None, None, None)


def get_stock_data(stocks):

    symbol_str = ''
    for stock in stocks:
        symbol_str += '{}+'.format(stocks[stock][0])
    url = 'http://finance.yahoo.com/d/quotes.csv?s=#&f=l1p2'
    try:
        prices = requests.get(url.replace('#', symbol_str)).text.split('\n')
    except requests.exceptions.ConnectionError:
        raise SystemExit
    raw = [x.split(',') for x in prices[:-1]]
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
        stocks = get_stock_data(stocks)
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
        return'nessuna azione inserita!\n'

    table = format_pretty_table(log, log_columns_names)

    if not msg:
        no_msg = 'nessuna azione è scesa sotto la soglia'
        return '{}\n{}\n'.format(table, no_msg)

    return '{}\n{}\n'.format(table, msg)


def check_bonds(bonds):

    msg = ''
    log = ''
    log_columns_names = [' ', 'nome', 'progresso', 'prezzo', 'max_y', 'min_y',
                         'yield_y', 'yield']
    log = []
    text_up = '{0} è salita sopra la soglia di {1}, ultimo prezzo {2}\n'
    text_down = '{0} è sceso sotto la soglia di {1}, ultimo prezzo {2}\n'

    if bonds:
        for bond in bonds:

            isin = bonds[bond][0]
            bond_price, repayment_date, max_y, min_y = get_bond_data(isin)

            if not bond_price:
                continue

            gross_coupon = float(bond.split('-')[1].replace(',', '.'))/100
            net_coupon = gross_coupon - gross_coupon*TAX
            today = datetime.date.today()
            day_to_repayment = (repayment_date-today).days
            cumulative_coupon = (net_coupon/365.0)*day_to_repayment
            cumulative_coupon *= INVESTED
            repayment_diff = INVESTED - (INVESTED*(bond_price/100))
            bond_yield = int(cumulative_coupon + repayment_diff)
            annual_yield = round(bond_yield/(day_to_repayment/365.0), 2)

            bond_prefix = bonds[bond][1][:1]

            if bond_prefix == '+':
                bond_limit = float(bonds[bond][1][1:])
                progress = compute_progress(bond_price, bond_limit)
                log_data = ['+', bond, progress, bond_price, max_y, min_y,
                            annual_yield, bond_yield]
                log.append(log_data)
                if bond_price > bond_limit:
                    msg += text_up.format(bond, bonds[bond][1], bond_price)
            else:
                bond_limit = float(bonds[bond][1])
                if bond_prefix == '-':
                    bond_limit = float(bonds[bond][1][1:])
                progress = compute_progress(bond_price, bond_limit)
                log_data = ['-', bond, progress, bond_price, max_y, min_y,
                            annual_yield, bond_yield]
                log.append(log_data)
                if bond_price < bond_limit:
                    msg += text_down.format(bond, bonds[bond][1], bond_price)

            sleep(randint(5, 7))
    else:
        return'nessuna obbligazione inserita!\n'

    table = format_pretty_table(log, log_columns_names)

    if not msg:
        no_msg = 'nessuna obbgligazione è scesa sotto la soglia'
        return '{}\n{}\n'.format(table, no_msg)

    return '{}\n{}\n'.format(table, msg)


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
    try:
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
    except SystemExit:
        click.echo('ATTENZIONE nessuna connessione internet')


@cli.command()
@click.option('--bond', nargs=3, type=str, default=(),
              help='obbligazione : NOME-CEDOLA ISIN SOGLIA')
@click.option('--stock', nargs=3, type=str, default=(),
              help='azione : NOME SIMBOLO SOGLIA')
def add(bond, stock):
    ''' aggiungi un azione o obbligazione'''
    # devo validare l input
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
