import sys
import smtplib
from requests import get
from bs4 import BeautifulSoup
from random import randint
from time import sleep
from email.mime.text import MIMEText
from subprocess import call




def get_last_price(isin):
    url_it = "http://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/#.html?lang=it"
    seg_url = url_it.split('#')
    url = seg_url[0] + isin + seg_url[1]
    html = get(url)
    soup = BeautifulSoup(html.text, 'html.parser')
    return float(soup.find_all('td', limit=2)[1].text.replace(',', '.'))



def send_email(text):

    msg = MIMEText(text)
    msg['Subject'] = 'pi'
    msg['From'] = 'cavolo9876@gmail.com'
    msg['To'] = 'cavolo9876@gmail.com'
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    print('messagio inviato')
    s.quit()

def check(diz):

    notification=False
    msg=''

    for bond in diz:
        print('aggiorno {}'.format(bond))
        price=get_last_price(diz[bond][0])
        if price < float(diz[bond][1]):
            notification=True
            text='{0} è sceso sotto la soglia di {1}, ultimo prezzo {2}'.format(bond, diz[bond][1], price)
            msg+=text+'\n'
            print(text)
        sleep(randint(15, 30))
    if notification:
        send_email(msg)

def get_bonds(filename):
    with open(filename) as f:
        temp=f.readlines()
        formatted=[el.strip('\n').split(';') for el in temp]
        bonds={x[0]:(x[1], x[2]) for x in formatted}
    return bonds

def mainloop():

    try:
        while True:
            call(['git', 'pull'])
            check(get_bonds('bonds.csv'))
            print('standby')
            sleep(1200)

    except KeyboardInterrupt:
        pass
    except:
        err =  sys.exc_info()[1]
        msg='errore programma pi: {}'.format(err)
        print(msg)
        send_email(msg)




if __name__ == '__main__':
    mainloop()
