from .const import Const
from .database import session
from .models import Stock, Bond
from requests import get, exceptions
from datetime import datetime, date
from bs4 import BeautifulSoup
from random import randint
from time import sleep


def compute_progress(price, limit):
    '''
        args: float, Float
        description: if an asset has not reached its threshold the function
        calculates the percentage of its current value that the asset has to
        lose/gain too reach the threshold
        return type: str
    '''
    price = float(price)
    limit = float(limit)
    if not price or not limit:
        return None
    if max(price, limit) == limit:  # price<limit
        gap = limit - price
        progress = gap / price
    else:                           # limit<price
        gap = price - limit
        progress = gap / price
    return '{}%'.format(str(progress * 100)[:4])


def update_treasury_data():
    '''
        currently not used and needs sqlalchemy integration
    '''
    url = 'http://www.wsj.com/mdc/public/page/2_3020-treasury.html'
    try:
        html = get(url)
    except exceptions.ConnectionError:
        raise SystemExit
    soup = BeautifulSoup(html.text, 'html.parser')
    td_tags = soup.find_all('td')
    raw = [el.text for el in td_tags[8:]]
    raw = raw[:raw.index('Maturity')]
    sub_lists = [raw[i:i+6] for i in range(0, len(raw), 6)]
    polished_dict = {el[0]: el[1:] for el in sub_lists}
    return polished_dict


def update_IT_bond_data(bonds_list):
    '''
        arg type: list of sqlalchemy.orm models
        description: scraps data from borsaitaliana.it,
                     updates bonds prices and related values
        data keys(for future reference):
        Prezzo ufficiale, Numero Contratti, Lotto Minimo, Min Oggi,
        Valuta di negoziazione, Max Oggi, Valuta di liquidazione,
        Min Anno, Data Ultima Cedola Pagata, Max Anno, Tasso Prossima Cedola,
        Tipo Bond, Scadenza, Codice Isin, Apertura, Mercato, Volume Ultimo:,
        Tipologia, Volume totale
    '''
    url = 'http://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/'
    url_end = '.html?lang=it'

    for bond in bonds_list:
        try:
            html = get(''.join([url, bond.isin.upper(), url_end]))
        except exceptions.ConnectionError:
            raise SystemExit
        soup = BeautifulSoup(html.text, 'html.parser')
        raw_data = soup.find_all('td')
        if raw_data:
            keys = [el.text for i, el in enumerate(raw_data)
                    if i > 5 and i < 44 and i % 2 == 0]
            values = [el.text for i, el in enumerate(raw_data)
                      if i > 5 and i < 44 and i % 2 != 0]
            data = dict(zip(keys, values))
            bond.price = float(data['Prezzo ufficiale'].replace(',', '.'))
            unpolished_date = datetime.strptime(data['Scadenza'], '%d/%m/%y')
            bond.maturity = unpolished_date.date()
            bond.max_y = float(data['Max Anno'].replace(',', '.'))
            bond.min_y = float(data['Min Anno'].replace(',', '.'))

            gross_coupon = float(bond.name.split('-')[1].replace(',', '.'))/100
            net_coupon = gross_coupon - gross_coupon*Const.TAX

            day_to_repayment = (bond.maturity-date.today()).days
            cumulative_coupon = (net_coupon/365.0)*day_to_repayment
            cumulative_coupon *= Const.INVESTED
            repayment_diff = Const.INVESTED - (Const.INVESTED*(bond.price/100))
            bond.yield_tot = int(cumulative_coupon + repayment_diff)
            bond.yield_y = round(bond.yield_tot/(day_to_repayment/365.0), 2)
            bond.progress = compute_progress(bond.price, bond.threshold[1:])
        sleep(randint(1, 3))
    session.commit()


def update_stock_data(stocks_list):
    '''
        arg type: list of sqlalchemy.orm models
        description: using yahoo finance api updates stocks prices
                     and related values
    '''
    url = 'http://finance.yahoo.com/d/quotes.csv?s=#&f=l1p2'
    symbol_str = ''

    if stocks_list:
        for stock in stocks_list:
            symbol_str = ''.join([symbol_str, '{}+'.format(stock.symbol)])

        try:
            data = get(url.replace('#', symbol_str)).text.split('\n')
        except exceptions.ConnectionError:
            raise SystemExit
        raw = [x.split(',') for x in data[:-1]]
        pol = list(map((lambda y: [float(y[0]), y[1].replace('"', '')]), raw))
        for i, stock in enumerate(stocks_list):
            stock.price = pol[i][0]
            stock.variation = pol[i][1]
            stock.progress = compute_progress(stock.price, stock.threshold[1:])
        session.commit()


def update_db(forced=False):

    bonds = session.query(Bond).all()
    stocks = session.query(Stock).all()

    now = datetime.today()
    twenty_m = 20*60
    twelve_h = 12*60*60

    with open(Const.CONFIGS, 'r')as f:
        previous_s = f.readline()
        previous_b = f.readline()
        other_configs = f.readlines()

    raw_s = previous_s.strip('\n').split('.')[0]
    raw_b = previous_b.strip('\n').split('.')[0]

    last_stock_update = datetime.strptime(raw_s, '%Y-%m-%d %H:%M:%S')
    last_bond_update = datetime.strptime(raw_b, '%Y-%m-%d %H:%M:%S')
    seconds_from_last_s = (now - last_stock_update).seconds
    seconds_from_last_b = (now - last_bond_update).seconds

    if seconds_from_last_s > twenty_m or forced:
        update_stock_data(stocks)
        raw_s = '{}\n'.format(str(now))
    else:
        raw_s = previous_s

    if seconds_from_last_b > twelve_h or forced:
        update_IT_bond_data(bonds)
        raw_b = '{}\n'.format(str(now))
    else:
        raw_b = previous_b

    with open(Const.CONFIGS, 'w') as f:
        lines = [raw_s, raw_b] + other_configs
        for line in lines:
            f.write(line)


def check_thresholds(asset_list):
    '''
        description: checks against the whole db if any asset has passed
                     its user set threshold
        returns a well formatted message
        return type: str
    '''

    msg = ''
    msg_txt_up = '{} è salita sopra la soglia di {}, ultimo prezzo {}\n'
    msg_txt_down = '{} è scesa sotto la soglia di {}, ultimo prezzo {}\n'
    if asset_list:
        for asset in asset_list:
            threshold_prefix = asset.threshold[:1]
            threshold = float(asset.threshold[1:])
            if threshold_prefix == '+':
                if asset.price > threshold:
                    msg = ''.join([msg, msg_txt_up.format(asset.name,
                                   str(threshold), asset.price)])
            else:
                if asset.price < threshold:
                    msg = ''.join([msg, msg_txt_down.format(asset.name,
                                   str(threshold), asset.price)])
        if not msg:
            msg = 'Nessun {} ha superato le soglie prefissate\n'
    else:
        return None
    return msg
