import locale
import logging
from .const import Const
from .database import session
from .models import Stock, Bond_IT, Bond_TR, Bond_ETLX
from sqlalchemy.exc import IntegrityError
from requests import get, exceptions
from datetime import datetime, date
from bs4 import BeautifulSoup
from time import sleep

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger(__name__)
locale.setlocale(locale.LC_NUMERIC, 'it_IT.UTF-8')


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


def compute_yield(maturity, gross_coupon, price):
    gross_coupon /= 100
    net_coupon = gross_coupon - gross_coupon*Const.TAX
    day_to_repayment = (maturity-date.today()).days
    cumulative_coupon = (net_coupon/365.0)*day_to_repayment
    cumulative_coupon *= Const.INVESTED
    repayment_diff = Const.INVESTED - (Const.INVESTED*(price/100))
    yield_tot = int(cumulative_coupon + repayment_diff)
    yield_y = round(yield_tot/(day_to_repayment/365.0), 2)
    return (yield_tot, yield_y)


def update_bond_tr(bonds_list):
    '''
        arg type: list of sqlalchemy.orm models
        description: scraps data from wall street journal,
                     updates bonds prices and related values
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
    polished_dict = {(el[0], float(el[1])): el[3] for el in sub_lists}
    for bond in bonds_list:
        mat = bond.maturity.strftime('%m/%d/%Y')
        cup = bond.coupon
        if mat[0] == '0':
            mat = mat[1:]
        bond.price = float(polished_dict[(mat, cup)])
        bond.progress = compute_progress(bond.price, bond.threshold[1:])
        yields = compute_yield(bond.maturity, bond.coupon, bond.price)
        bond.yield_tot, bond.yield_y = yields
    session.commit()


def update_bond_etlx(bonds_list):
    url = 'http://www.eurotlx.com/it/strumenti/dettaglio/'
    for bond in bonds_list:
        try:
            html = get(''.join([url, bond.isin.upper()]))
        except exceptions.ConnectionError:
            raise SystemExit
        soup = BeautifulSoup(html.text, 'html.parser')
        raw_data = soup.find_all('td')
        if raw_data:
            values = {
                raw_data[cont].text: raw_data[cont+1].text
                for cont in range(32, 102, 2)}
            price = values['Prezzo']
            dynamic_price = values['Prezzo di riferimento dinamico']
            closing_price = values['Prezzo di chiusura']
            if price != '-':
                bond.price = locale.atof(price)
            elif dynamic_price != '-':
                bond.price = locale.atof(dynamic_price)
            elif closing_price != '-':
                bond.price = locale.atof(closing_price)
            bond.coupon = locale.atof(values['Tasso cedola in corso'])
            date = values['Data di scadenza']
            unpol_date = datetime.strptime(date, '%d-%m-%Y')
            bond.maturity = unpol_date.date()
            bond.max_y = locale.atof(values["Massimo dell'anno"])
            bond.min_y = locale.atof(values["Minimo dell'anno"])
            yields = compute_yield(bond.maturity, bond.coupon, bond.price)
            bond.yield_tot, bond.yield_y = yields
            bond.progress = compute_progress(bond.price, bond.threshold[1:])
            sleep(10)
    session.commit()


def update_bond_it(bonds_list):
    '''
        arg type: list of sqlalchemy.orm models
        description: scraps data from borsaitaliana.it,
                     updates bonds prices and related values
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
            last_price = raw_data[1].text
            if last_price:
                bond.price = locale.atof(last_price)
            else:
                bond.price = locale.atof(data['Prezzo ufficiale'])
            unpol_date = datetime.strptime(data['Scadenza'], '%d/%m/%y')
            bond.maturity = unpol_date.date()
            bond.max_y = locale.atof(data['Max Anno'])
            bond.min_y = locale.atof(data['Min Anno'])
            # print(bond.name)
            yields = compute_yield(bond.maturity, bond.coupon, bond.price)
            bond.yield_tot, bond.yield_y = yields
            bond.progress = compute_progress(bond.price, bond.threshold[1:])
            sleep(1)
    session.commit()


def update_stock(stocks_list):
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


def tbalance(threshold):
    if ',' in threshold:
        threshold = threshold.replace(',', '.')
    if threshold[0] != '+':
        return ''.join(['-', threshold])
    return threshold


def tforce_sign(matrix, col_index):
    for row in matrix:
        for i in col_index:
            row[i] = int(row[i])
            if row[i] < 0:
                row[i] = str(row[i])
            else:
                row[i] = '{}{}'.format('+', row[i])
    return matrix


def stock_table(stocks):
    columns_names = ['Soglia', 'Nome', 'Progresso', 'Prezzo', 'Variazione']

    content_s = [[s.threshold, s.name.lower(), s.progress, s.price,
                  s.variation] for s in stocks]
    content_s.sort(key=lambda x: x[1])
    content_s.insert(0, columns_names)
    return content_s


def bond_table(bonds):
    columns_names = ['Soglia', 'Nome', 'Progresso', 'Prezzo', 'Max_y', 'Min_y',
                     'Yield_y', 'Yield']
    raw_content_b = [[b.threshold, b.name, b.progress, b.price,
                      b.max_y, b.min_y, b.yield_y, b.yield_tot,
                      b.maturity] for b in bonds]
    raw_content_b.sort(key=lambda x: x[-1])
    content_b = [line[:-1] for line in raw_content_b]
    content_b = tforce_sign(content_b, Const.COSTUM_COLOR_B)
    content_b.insert(0, columns_names)
    return content_b


def bond_tr_table(bonds):
    columns_names = ['Soglia', 'Nome', 'Progresso', 'Prezzo', 'Yield_y',
                     'Yield']
    raw_content_b = [[b.threshold, b.name, b.progress, b.price, b.yield_y,
                      b.yield_tot, b.maturity] for b in bonds]
    raw_content_b.sort(key=lambda x: x[-1])
    content_b = [line[:-1] for line in raw_content_b]
    content_b = tforce_sign(content_b, Const.COSTUM_COLOR_BT)
    content_b.insert(0, columns_names)
    return content_b


def add_bond_it(name, threshold, isin, typology, coupon):

    threshold = tbalance(threshold)
    coupon = locale.atof(coupon)
    bond = Bond_IT(name=name.lower(), isin=isin.upper(), threshold=threshold,
                   typology=typology, coupon=coupon)
    try:
        session.add(bond)
        session.commit()
    except IntegrityError:
        return '\nATTENZIONE isin già presente'

    update_bond_it([bond])

    return '\n{} inserito!'.format(name)


def add_bond_tr(name, threshold, maturity, coupon):

    threshold = tbalance(threshold)

    mat = datetime.strptime(maturity, '%m/%d/%Y').date()
    bond = Bond_TR(name=name.lower(), maturity=mat, threshold=threshold,
                   coupon=coupon)
    try:
        session.add(bond)
        session.commit()
    except IntegrityError:
        return '\nATTENZIONE isin o data già presente'

    update_bond_tr([bond])

    return '\n{} inserito!'.format(name)


def add_bond_etlx(name, threshold, isin):

    threshold = tbalance(threshold)
    bond = Bond_ETLX(name=name.lower(), isin=isin.upper(), threshold=threshold)
    try:
        session.add(bond)
        session.commit()
    except IntegrityError:
        return '\nATTENZIONE isin già presente'

    update_bond_etlx([bond])

    return '\n{} inserito!'.format(name)


def add_stock(name, symbol, threshold):

    threshold = tbalance(threshold)

    stock = Stock(name=name.lower(), symbol=symbol, threshold=threshold)
    try:
        session.add(stock)
        session.commit()
    except IntegrityError:
        return '\nATTENZIONE simbolo già presente'
    update_stock([stock])
    return '\n{} inserito!'.format(name)


def delete_stock(stock_name):
    query = session.query(Stock).filter(Stock.name == stock_name.lower()).all()
    if not query:
        return 'ATTENZIONE: {} non esiste nel database!'.format(stock_name)
    session.delete(query[0])
    session.flush()
    session.commit()
    return '{} cancellato!'.format(stock_name)


def delete_bond(name, bond_type):
    # da ridefinire cn costanti
    if bond_type == 1:
        _type = Bond_IT
    elif bond_type == 2:
        _type = Bond_TR
    elif bond_type == 3:
        _type = Bond_ETLX
    query = session.query(_type).filter(_type.name == name.lower()).all()
    if not query:
        return 'ATTENZIONE: {} non esiste nel database!'.format(name)
    session.delete(query[0])
    session.flush()
    session.commit()
    return '{} cancellato!'.format(name)


def show_assets():
    stock_columns_names = ['nome', 'simbolo', 'soglia']
    bond_it_columns_names = ['nome', 'isin', 'soglia']
    bond_etlx_columns_names = ['nome', 'isin', 'soglia']
    bond_tr_columns_names = ['nome', 'scadenza', 'soglia']
    stocks = session.query(Stock).all()
    bonds_it = session.query(Bond_IT).all()
    bonds_etlx = session.query(Bond_ETLX).all()
    bonds_tr = session.query(Bond_TR).all()
    content_s = [[s.name, s.symbol, s.threshold] for s in stocks]
    content_bi = [[b.name, b.isin, b.threshold] for b in bonds_it]
    content_be = [[b.name, b.isin, b.threshold] for b in bonds_etlx]
    content_bt = [[b.name, b.maturity, b.threshold] for b in bonds_tr]
    content_s.insert(0, stock_columns_names)
    content_bi.insert(0, bond_it_columns_names)
    content_be.insert(0, bond_etlx_columns_names)
    content_bt.insert(0, bond_tr_columns_names)
    return (content_s, content_bi, content_bt, content_be)


def update_db(forced=False):

    bonds_it = session.query(Bond_IT).all()
    bonds_tr = session.query(Bond_TR).all()
    bonds_etlx = session.query(Bond_ETLX).all()
    stocks = session.query(Stock).all()

    now = datetime.today()
    timeout_s = Const.STOCK_TIMEOUT
    timeout_b = Const.BOND_TIMEOUT

    with open(Const.CONFIGS, 'r')as f:
        previous_s = f.readline()
        previous_b = f.readline()
        other_configs = f.readlines()

    raw_s = previous_s.strip('\n').split('.')[0]
    raw_b = previous_b.strip('\n').split('.')[0]

    last_stock_update = datetime.strptime(raw_s, '%Y-%m-%d %H:%M:%S')
    last_bond_update = datetime.strptime(raw_b, '%Y-%m-%d %H:%M:%S')
    seconds_from_last_s = (now - last_stock_update).total_seconds()
    seconds_from_last_b = (now - last_bond_update).total_seconds()

    updating_stocks = False
    updating_bonds = False

    if seconds_from_last_s > timeout_s or forced:
        updating_stocks = True
        raw_s = '{}\n'.format(str(now))
    else:
        raw_s = previous_s

    if seconds_from_last_b > timeout_b or forced:
        updating_bonds = True
        raw_b = '{}\n'.format(str(now))
    else:
        raw_b = previous_b

    with open(Const.CONFIGS, 'w') as f:
        lines = [raw_s, raw_b] + other_configs
        for line in lines:
            f.write(line)

    if updating_stocks:
        update_stock(stocks)
    if updating_bonds:
        update_bond_it(bonds_it)
        update_bond_tr(bonds_tr)
        update_bond_etlx(bonds_etlx)


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
    fixed_t = Const.REPAYMENT
    fixed = ['bond_it', 'bond_tr', 'bond_etlx']
    if asset_list:
        for asset in asset_list:
            if asset.price is not None:
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
                if asset.__tablename__ in fixed and asset.price < fixed_t:
                    msg = ''.join([msg, msg_txt_down.format(asset.name,
                                   str(Const.REPAYMENT), asset.price)])
        if not msg:
            msg = 'Nessun {} ha superato le soglie prefissate\n'
    else:
        return None
    return msg
