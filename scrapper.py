import sys
import smtplib
from requests import get
from bs4 import BeautifulSoup
from random import randint
from time import sleep
from email.mime.text import MIMEText
from subprocess import call
import datetime




def get_last_price(isin):
    url_it = "http://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/#.html?lang=it"
    seg_url = url_it.split('#')
    url = seg_url[0] + isin + seg_url[1]
    html = get(url)
    soup = BeautifulSoup(html.text, 'html.parser')
    return float(soup.find_all('td', limit=2)[1].text.replace(',', '.'))



def send_email(text):

    msg = MIMEText(text)
    msg['Subject'] = 'notifica bond {}'.format(datetime.datetime.today())
    msg['From'] = ''
    msg['To'] = ''
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()

def check(diz):

    notification=False
    msg=''

    for bond in diz:
        price=get_last_price(diz[bond][0])
        if price < float(diz[bond][1]):
            notification=True
            text='{0} è sceso sotto la soglia di {1}, ultimo prezzo {2}'.format(bond, diz[bond][1], price)
            msg+=text+'\n'
        sleep(randint(15, 30))
    if notification:
        send_email(msg)

def get_bonds(filename):
    with open(filename, 'r') as f:
        f.readline()
        temp=f.readlines()
        if temp:
            formatted=[el.strip('\n').split(';') for el in temp]
            bonds={x[0]:(x[1], x[2]) for x in formatted}
	    else:
            sys.exit(0)
    return bonds

def main():
    try:
        check(get_bonds('/home/marco/Scrivania/pi-project/bonds.csv'))


    except:
        err =  sys.exc_info()[0]
        msg='errore programma: {}'.format(err)
        send_email(msg)




if __name__ == '__main__':
    main()
