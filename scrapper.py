from requests import get
from bs4 import BeautifulSoup
from random import randint
from time import sleep
import smtplib
from email.mime.text import MIMEText
from subprocess import call


bonds = {'BTP-1FB19 4,25%': 'IT0003493258'}

def get_last_price(isin):
    url_it = "http://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/#.html?lang=it"
    seg_url = url_it.split('#')
    url = seg_url[0] + isin + seg_url[1]
    html = get(url)
    soup = BeautifulSoup(html.text, 'html.parser')
    return soup.find_all('td', limit=2)[1].text.replace(',', '.')


def make_email():
    print('crezione report obbligazioni')
    msg = ''
    for bond in bonds:
        price= get_last_price(bonds[bond])
        msg+=bond+': '+price+'\n'
        print('aggiorno {}'.format(bond))
        sleep(randint(15, 30))
    return msg


def send_email(text):

    msg = MIMEText(text)
    msg['Subject'] = 'prova'
    msg['From'] = 'cavolo9876@gmail.com'
    msg['To'] = 'cavolo9876@gmail.com'
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    print('messagio inviato')
    s.quit()


def mainloop():

    while True:
        email=make_email()
        send_email(email)
        sleep(1200)




if __name__ == '__main__':
    mainloop()
