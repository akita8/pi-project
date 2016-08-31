import datetime
import imaplib
import smtplib
import scrapper as scr
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


def html_email(asset_type):

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "scrapper get {} {}".format(asset_type, today)
    msg['From'] = sender
    msg['To'] = rec

    text = ""
    html = html_content(scr.cron_get(asset_type), asset_type)

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

    for m in msg.split('\n'):
        html_msg += paragraph.format(m)

    return ''.join([prefix, html_msg, html_table, suffix])


def parse_command(command):
    words = command.split('|')[0].split(' ')
    stmt = words[0].lower()
    options = words[1:]
    if stmt == 'get':
        s = 'stock'
        b = 'bond'
        i = 'ip'
        first_option = options[0].lower()
        if s in first_option:      # stock
            html_email(s)
        elif b in first_option:    # bond
            html_email(b)
        elif i in first_option:    # ip
            cmd = ['hostname', '-I']
            p = Popen(cmd, stdout=PIPE)
            out = p.communicate()
            raw = str(out[0])
            ip = raw.strip('\n').split(' ')[0][2:]
            text_email(stmt, i, ip)


def check_email():
    conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
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
    conn.close()


if __name__ == '__main__':
    check_email()
