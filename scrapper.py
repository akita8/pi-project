import click
import sys
import smtplib
import requests
import datetime
import os
from collections import OrderedDict
from os.path import isfile
from bs4 import BeautifulSoup
from random import randint
from time import sleep
from email.mime.text import MIMEText
from subprocess import call


ROOT_FOLDER = os.path.abspath(os.path.dirname(__file__))
BONDS = ROOT_FOLDER + '/bonds.csv'
STOCKS = ROOT_FOLDER + '/stocks.csv'
CREDENTIALS = ROOT_FOLDER + '/credentials.txt'

def send_email(text):

    with open(CREDENTIALS, 'r') as f:
        cred = f.readline().strip('\n').split(',')
    msg = MIMEText(text)
    msg['Subject'] = 'notifica asset {}'.format(datetime.date.today())
    msg['From'] = cred[0]
    msg['To'] = cred[1]
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()

def formatted(raw):
    return [el.strip('\n').split(';') for el in raw]


def get_asset_type(path):
    return path.split('/')[-1].split('.')[0]


def url_completion(url, inclusion):
    seg= url.split('#')
    return '{0}{1}{2}'.format(seg[0], inclusion, seg[1])

def get_assets(fileloc):

    with open(fileloc, 'r') as f:
        f.readline()
        temp = f.readlines()

    if temp:
        assets=OrderedDict()
        for line in formatted(temp):
            assets[line[0]]=[line[1], line[2]]
    else:
        return None #da cambiare
    return assets

def get_bond_price(isin):

    url = url_completion(
        '''http://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/#.html?lang=it''', isin.upper())
    html = requests.get(url)
    soup = BeautifulSoup(html.text, 'html.parser')
    return float(soup.find_all('td', limit=8)[7].text.replace(',', '.'))


def get_stock_price(stocks):

    symbol_str=''
    for stock in stocks:
        symbol_str+='{}+'.format(stocks[stock][0])
    symbol_str=symbol_str[:-1]
    url = url_completion('http://finance.yahoo.com/d/quotes.csv?s=#&f=l1', symbol_str)
    prices=requests.get(url).text.split('\n')[:-1]
    polished=list(map(lambda x:float(x), prices))
    cont=0
    for stock in stocks:
        stocks[stock].append(polished[cont])
        cont+=1
    return stocks

def check(bonds, stocks, auto):

    notification = False
    msg = ''

    if stocks:
        stocks=get_stock_price(stocks)
        for stock in stocks:
            temp=stocks[stock]
            if temp[2]<float(temp[1]):
                notification=True
                text = '{0} è sceso sotto la soglia di {1}, ultimo prezzo {2}'.format(stock, temp[1], temp[2])
                msg += text + '\n'

    else:
        click.echo('nessuna azione inserita!')

    if bonds:
        for bond in bonds:
            bond_price = get_bond_price(bonds[bond][0])
            if bond_price < float(bonds[bond][1]):
                notification = True
                text = '{0} è sceso sotto la soglia di {1}, ultimo prezzo {2}'.format(bond, bonds[
                                                                                      bond][1], bond_price)
                msg += text + '\n'
            if not auto:
                click.echo('Aggiorno {}'.format(bond))
            sleep(randint(5, 10))

    else:
        click.echo('nessuna obbligazione inserita!')

    if notification and auto:
        send_email(msg)
    elif notification and not auto:
        click.echo(msg)
    elif auto:
        send_email('messaggio di testing')
    else:
        click.echo('nessuna obbgligazione o azione è scesa sotto la soglia')


@click.group()
def cli():

    if not isfile(BONDS):
        with open(BONDS, 'w') as f:
            f.write('nome;isin;soglia\n')
    if not isfile(STOCKS):
        with open(STOCKS, 'w') as f:
            f.write('nome;simbolo;soglia\n')


@cli.command()
@click.option('--auto', default=False)
def get(auto):
    '''attiva il programma'''

    if auto:
        sleep(60)  # waiting for connection at startup
    check(get_assets(BONDS), get_assets(STOCKS), auto)


@cli.command()
@click.option('--bond', nargs=3, type=str, default=(), help='obbligazione : NOME ISIN SOGLIA')
@click.option('--stock', nargs=3, type=str, default=(), help='azione : NOME SIMBOLO SOGLIA')
def add(bond, stock):
    ''' Aggiungi asset'''

    if bond:
        with open(BONDS, 'a') as f:
            f.write('{0};{1};{2}\n'.format(*bond))
    if stock:
        with open(STOCKS, 'a') as f:
            f.write('{0};{1};{2}\n'.format(*stock))


@cli.command()
@click.option('--mod', default='', help='modifica la soglia di notifica')
@click.option('--bond', default='', help='NOME obbligazione da rimuovere o modificare')
@click.option('--stock', default='', help='NOME azione da rimuovere o modificare')
def remove(mod, bond, stock):
    '''rimuovi un asset NOME'''

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
        if click.confirm('Vuoi davvero cancellare {}'.format(removed), default=False):

            new = [el for el in formatted(temp) if el[0] != removed]

            with open(selected, 'w') as f:
                f.write(header)
                for line in new:
                    f.write('{0};{1};{2}\n'.format(*line))


@cli.command()
def show():
    '''mostra le azioni e obbligazioni inserite'''
    with open(BONDS, 'r') as f, open(STOCKS, 'r') as d:
        text=f.read().replace(';', ' ')+'\n'+d.read().replace(';', ' ')
        click.echo_via_pager(text)


if __name__ == '__main__':
    cli()
