from requests import get
from bs4 import BeautifulSoup
from random import randint
from time import sleep
import smtplib
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
        sleep(randint(15, 30))
        if price < float(diz[bond][0]):
            notification=True
            msg='{0} è sceso sotto la soglia di {1}, ultim prezzo {2}\n'.format(bond, diz[bond][0], diz[bond][1])
    if notification:
        send_email(msg)

def mainloop():
#    try:
    while True:
        call(['git', 'pull'])

        with open('bonds.csv') as f:
            temp=f.read().split('\n')
            bonds={x.split(',')[0]:[x.split(',')[1],x.split(',')[2]] for x in temp }
        check(bonds)
        sleep(1200)
#    except:
        send_email('errore programma pi')




if __name__ == '__main__':
    mainloop()
