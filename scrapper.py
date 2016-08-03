
import click
import sys
import smtplib
import requests
from bs4 import BeautifulSoup
from random import randint
from time import sleep
from email.mime.text import MIMEText
from subprocess import call
import datetime
import os

ROOT_FOLDER = os.path.abspath(os.path.dirname(__file__))
BONDS=ROOT_FOLDER+'/bonds.csv'
CREDENTIALS=ROOT_FOLDER+'/credentials.txt'

def formatted(raw):
    return [el.strip('\n').split(';') for el in raw]

def get_last_price(isin):

    url_it = "http://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/#.html?lang=it"
    seg_url = url_it.split('#')
    url = seg_url[0] + isin.upper() + seg_url[1]
    html = requests.get(url)
    soup = BeautifulSoup(html.text, 'html.parser')
    return float(soup.find_all('td', limit=8)[7].text.replace(',', '.'))

def send_email(text):

    with open(CREDENTIALS, 'r') as f:
        cred=f.readline().strip('\n').split(',')
    msg = MIMEText(text)
    msg['Subject'] = 'notifica bond {}'.format(datetime.datetime.today())
    msg['From'] = cred[0]
    msg['To'] = cred[1]
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()

def check(diz, auto):

    notification=False
    msg=''

    for bond in diz:
        price=get_last_price(diz[bond][0])
        if price < float(diz[bond][1]):
            notification=True
            text='{0} è sceso sotto la soglia di {1}, ultimo prezzo {2}'.format(bond, diz[bond][1], price)
            msg+=text+'\n'
        if not auto:
            click.echo('Aggiorno {}'.format(bond))
        sleep(randint(5, 15))
    if notification and auto:
        send_email(msg)
    elif notification and not auto:
        click.echo(msg)
    elif auto:
        send_email('messaggio di testing')
    else:
        click.echo('nessuna obbgligazione è scesa sotto la soglia')

def get_bonds():

    with open(BONDS, 'r') as f:
        f.readline()
        temp=f.readlines()
    if temp:
        bonds={x[0]:(x[1], x[2]) for x in formatted(temp)}
    else:
        sys.exit(0)
    return bonds




@click.group()
def cli():
    pass



@cli.command()
@click.option('--auto', default=False)
def get(auto):
    '''attiva il programma'''

    if auto:
        sleep(60) #waiting for connection
    check(get_bonds(), auto)

@cli.command()
@click.argument('bond')
def add(bond):
    ''' aggiungi obbgligazioni NOME-ISIN-SOGLIA'''
    with open(BONDS, 'a') as f:
        f.write('{0};{1};{2}\n'.format(*bond.split('-')))

@cli.command()
@click.option('--mod', default='', help='modifica la soglia di notifica')
@click.argument('bond_name')
def remove(mod, bond_name):
    '''rimuovi un obbligazione NOME'''

    with open(BONDS, 'r') as f:
        header=f.readline()
        temp=f.readlines()


    if mod:
        new=[el for el in formatted(temp)]
        with open(BONDS, 'w') as f:
            f.write(header)
            for line in new:
                if line[0]==bond_name:
                    f.write('{0};{1};{2}\n'.format(line[0], line[1], mod))
                else:
                    f.write('{0};{1};{2}\n'.format(*line))
    else:
        if click.confirm('Vuoi davvero cancellare {}'.format(bond_name), default=False):

            new=[el for el in formatted(temp) if el[0]!=bond_name]

            with open(BONDS, 'w') as f:
                f.write(header)
                for line in new:
                    f.write('{0};{1};{2}\n'.format(*line))

@cli.command()
def show():
    '''mostra le bonds inserite'''
    with open(BONDS, 'r') as f:
        bonds=f.read()
        click.echo_via_pager(bonds.replace(';', ' '))


if __name__ == '__main__':
    cli()
