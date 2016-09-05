from data.const import Const
from data.database import session
from data.models import Bond, Stock
from data.processing import update_db, check_thresholds
from data.processing import delete_stock, delete_bond, add_stock, add_bond
from data.processing import stock_table, bond_table, show_assets
from datetime import date
from imaplib import IMAP4_SSL
from smtplib import SMTP
from sqlalchemy.exc import IntegrityError
from socket import gaierror
from subprocess import Popen, PIPE
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import message_from_bytes


with open(Const.CONFIGS, 'r') as f:
    f.readline()
    f.readline()
    sender = f.readline().strip('\n')
    rec = f.readline().strip('\n')
    psw = f.readline().strip('\n')

today = date.today()


def green_or_red(num):

    if float(num) > 0:
        return 'ForestGreen'
    return 'Crimson'


def send_email(message):

    mail = SMTP('smtp.gmail.com', 587)
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


def html_content(table, msg, a_type=None):
    '''will be deprecated with jinja2 template'''

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
            stocks = session.query(Stock).all()
            notification_s = check_thresholds(stocks).format('azione')
            table = stock_table(stocks)
            html = html_content(table, notification_s, s)
            html_email(' '.join([stmt, s]), html)
        elif b in first_option:    # bond
            bonds = session.query(Bond).all()
            notification_b = check_thresholds(bonds).format('obbligazione')
            table = bond_table(bonds)
            html = html_content(table, notification_b, b)
            html_email(' '.join([stmt, b]), html)
        elif i in first_option:    # ip
            cmd = ['hostname', '-I']
            p = Popen(cmd, stdout=PIPE)
            out = p.communicate()
            raw = str(out[0])
            ip = raw.strip('\n').split(' ')[0][2:]
            text_email(stmt, i, ip)

    elif stmt == 'add':
        first_option = options[0].lower()
        if first_option != b and first_option != s:
            failure_msg = "COMAND FALLITO: manca l'identificatore stock/bond"
            text_email(stmt, first_option, failure_msg)
        try:
            added = options[1:4]
            if s in first_option:      # stock
                add_stock(added)
                text_email(stmt, s, success_msg)
            elif b in first_option:    # bond
                add_bond(added)
                text_email(stmt, b, success_msg)
        except IndexError:
            text_email(stmt, first_option, failure_msg)
        except IntegrityError:
            failure_msg = 'COMAND FALLITO: simbolo/isin già presente'
            text_email(stmt, first_option, failure_msg)

    elif stmt == 'remove':
        first_option = options[0].lower()
        if first_option != b and first_option != s:
            failure_msg = "COMAND FALLITO: manca l'identificatore stock/bond"
            text_email(stmt, first_option, failure_msg)
        try:
            removed = options[1].lower()
            if s in first_option:      # stock
                response = delete_stock(removed)
            elif b in first_option:    # bond
                response = delete_bond(removed)
            text_email(stmt, first_option, '\n'.join([success_msg, response]))
        except IndexError:
            text_email(stmt, first_option, '\n'.join([failure_msg, response]))

    elif stmt == 'show':
        table_s, table_b = show_assets()
        table_s.pop(0)
        table_b.pop(0)
        table_b.insert(0, ['', '', ''])
        table = [['nome', 'isin/simbolo', 'soglia']]
        table.extend(table_s)
        table.extend(table_b)
        html_email('show', html_content(table, None))

    else:
        failure_msg = "COMAND FALLITO: comando non riconusciuto"
        text_email(stmt, first_option, failure_msg)


def check_email():
    try:
        conn = IMAP4_SSL("imap.gmail.com", 993)
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
        update_db()
        check_email()
    except SystemExit:
        pass
