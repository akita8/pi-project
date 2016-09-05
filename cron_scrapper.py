import datetime
import imaplib
import smtplib
import data_processing as scr
from socket import gaierror
from subprocess import Popen, PIPE
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import message_from_bytes

CREDENTIALS = scr.ROOT_FOLDER + '/credentials.txt'

with open(CREDENTIALS, 'r') as f:
    cred = f.readline().strip('\n').split(',')
    sender = cred[0]
    rec = cred[1]
    psw = f.readline().strip('\n')

today = datetime.date.today()


def green_or_red(num):

    if float(num) > 0:
        return 'ForestGreen'
    return 'Crimson'


def send_email(message):

    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login(sender, psw)
    mail.sendmail(sender, rec, message.as_string())
    mail.quit()


def text_email(cmd, opt, text):
    msg = MIMEText(text)
    msg['Subject'] = "scrapper {} {} {}".format(cmd, opt, today)
    msg['From'] = sender
    msg['To'] = rec
    send_email(msg)


def html_email(cmd, html):

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "scrapper {} {}".format(cmd, today)
    msg['From'] = sender
    msg['To'] = rec

    text = ""

    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    msg.attach(part1)
    msg.attach(part2)
    send_email(msg)


def html_content(content, a_type):

    table, msg = content

    style = '''"font-family:Rockwell, serif;font-size:14px;font-weight:normal;
               padding:10px 5px;border-style:solid;border-width:{}px;
               overflow:hidden;word-break:normal;vertical-align:top;
               color:black;background-color:{}"
            '''

    prefix = '<html><head></head><body>'

    suffix = '</body></html>'

    html_table = '<table style="border-collapse:collapse;border-spacing:0">'
    header = True
    for row in table:
        html_table += '<tr>'
        for i, cell in enumerate(row):
            color = 'LemonChiffon'
            border = 2
            if not header:
                # variazione
                if i == 4 and a_type == 'stock':
                    if cell != 'N/A':
                        var = cell[:-1]  # removing the % symbol
                        color = green_or_red(var)
                # yield and yield_y
                elif (i == 6 or i == 7) and a_type == 'bond':
                    color = green_or_red(cell)
            else:
                border = 3
                color = 'PeachPuff'
            s = style.format(border, color)
            html_table += '<th style={}>{}</th>'.format(s, str(cell))
        if header:
            header = False
        html_table += '</tr>'

    html_table += '</table>'

    paragraph = '''<p style="font-family:Rockwell, serif;
                   font-size:14px;color:black">{}</p>'''
    html_msg = ''

    if msg:
        for m in msg.split('\n'):
            html_msg += paragraph.format(m)

    return ''.join([prefix, html_msg, html_table, suffix])


def parse_command(command):
    end_of_cmd = '|'
    if end_of_cmd not in command:
        text_email('ERRORE: ultimo comando', '', ' | non presente')
        return
    words = command.split(end_of_cmd)[0].split(' ')
    stmt = words[0].lower()
    options = words[1:]
    s = 'stock'
    b = 'bond'
    i = 'ip'
    success_msg = 'COMANDO ESEGUITO: {}'.format(' '.join(words))
    failure_msg = 'COMAND FALLITO: {}'.format(' '.join(words))

    if stmt == 'get':
        first_option = options[0].lower()
        if s in first_option:      # stock
            html_email(' '.join([stmt, s]), html_content(scr.cron_get(s), s))
        elif b in first_option:    # bond
            html_email(' '.join([stmt, b]), html_content(scr.cron_get(b), b))
        elif i in first_option:    # ip
            cmd = ['hostname', '-I']
            p = Popen(cmd, stdout=PIPE)
            out = p.communicate()
            raw = str(out[0])
            ip = raw.strip('\n').split(' ')[0][2:]
            text_email(stmt, i, ip)

    elif stmt == 'add':
        first_option = options[0].lower()
        try:
            if s in first_option:      # stock
                with open(scr.STOCKS, 'a') as f:
                    stock = options[1:]
                    f.write('{0};{1};{2}\n'.format(*stock))
                    text_email(stmt, s, success_msg)
            elif b in first_option:    # bond
                with open(scr.BONDS, 'a') as f:
                    bond = options[1:]
                    f.write('{0};{1};{2}\n'.format(*bond))
                    text_email(stmt, b, success_msg)
        except IndexError:
            text_email(stmt, first_option, failure_msg)

    elif stmt == 'remove':
        first_option = options[0].lower()
        removed = options[1].lower()
        if s in first_option:      # stock
            selected = scr.STOCKS
            with open(selected, 'r') as f:
                header = f.readline()
                temp = f.readlines()
        elif b in first_option:    # bond
            selected = scr.BONDS
            with open(selected, 'r') as f:
                header = f.readline()
                temp = f.readlines()
        new = [el for el in scr.formatted(temp) if el[0].lower() != removed]
        with open(selected, 'w') as f:
            f.write(header)
            for line in new:
                f.write('{0};{1};{2}\n'.format(*line))
        text_email(stmt, selected, success_msg)

    elif stmt == 'show':
        with open(scr.BONDS, 'r') as f, open(scr.STOCKS, 'r') as d:
            f.readline()
            d.readline()
            table = [['nome', 'isin/simbolo', 'soglia']]
            table.extend([el.split(';') for el in f.readlines()])
            table.extend([el.split(';') for el in d.readlines()])
            html_email('show', html_content((table, None), None))


def check_email():
    try:
        conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    except gaierror:
        raise SystemExit
    conn.login(sender, psw)
    conn.select()  # select a mailbox, default INBOX

    typ, data = conn.search(None, 'UNSEEN')

    for num in data[0].split():
        typ, msg_data = conn.fetch(num, '(RFC822)')
        for response_part in msg_data:

            if isinstance(response_part, tuple):
                msg = message_from_bytes(response_part[1])
                subject = msg['subject']
                payload = msg.get_payload()
                cmd = payload[0].get_payload(decode=True).decode('utf-8')
                if 'scrapper' in subject.lower():
                    parse_command(cmd)
    conn.logout()


if __name__ == '__main__':
    try:
        check_email()
    except SystemExit:
        pass
