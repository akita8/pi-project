from scrapper import ROOT_FOLDER
import smtplib
import datetime
from email.mime.text import MIMEText
CREDENTIALS = ROOT_FOLDER + '/credentials.txt'


def send_email(text):  # da spostare

    with open(CREDENTIALS, 'r') as f:
        cred = f.readline().strip('\n').split(',')
    msg = MIMEText(text)
    msg['Subject'] = 'notifica asset {}'.format(datetime.date.today())
    msg['From'] = cred[0]
    msg['To'] = cred[1]
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()
