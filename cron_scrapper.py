import imaplib
import smtplib
import scrapper as scr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import message_from_bytes

CREDENTIALS = scr.ROOT_FOLDER + '/credentials.txt'

with open(CREDENTIALS, 'r') as f:
    cred = f.readline().strip('\n').split(',')
    sender = cred[0]
    rec = cred[1]
    psw = f.readline().strip('\n')


def green_or_red(num):

    if float(num) > 0:
        return 'ForestGreen'
    return 'Crimson '


def send_email(asset_type):

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "test"
    msg['From'] = sender
    msg['To'] = rec

    text = ""
    html = html_content(asset_type)

    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    msg.attach(part1)
    msg.attach(part2)
    mail = smtplib.SMTP('smtp.gmail.com', 587)

    mail.ehlo()

    mail.starttls()

    mail.login(sender, psw)
    mail.sendmail(sender, rec, msg.as_string())
    mail.quit()


def html_content(a_type):

    table, msg = scr.cron_get(a_type)

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
    words = command.strip('\r\n').split(' ')
    if words[0] == 'get':
        if 'stock' in words[1]:
            send_email('stock')
        elif 'bond' in words[1]:
            send_email('bond')


def check_email():
    with imaplib.IMAP4_SSL("imap.gmail.com", 993) as conn:
        conn.login(sender, psw)
        conn.select()  # select a mailbox

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
    check_email()
