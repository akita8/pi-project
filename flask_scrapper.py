from data.const import Const
from data.database import session as db_session
from data.models import Stock, Bond_IT, Bond_TR, Bond_ETLX
from data.processing import stock_table, bond_table, bond_tr_table
from data.processing import check_thresholds, show_assets
from data.processing import add_bond_it, add_bond_tr, add_stock, add_bond_etlx
from data.processing import delete_bond, delete_stock
from flask import Flask
from flask import render_template, request, flash, redirect, url_for, session

app = Flask(__name__)

with open(Const.CONFIGS, 'r') as f:
    for i in range(4):
        f.readline()
    app.secret_key = f.readline()


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@app.route('/')
def index():
    query_s = db_session.query(Stock).all()
    query_b = db_session.query(Bond_IT).all()
    query_bt = db_session.query(Bond_TR).all()
    query_be = db_session.query(Bond_ETLX).all()
    if not query_b:
        n_b = ['nessuna obbligazione inserita nel database']
    else:
        n_b = check_thresholds(query_b).format('obbligazione').split('\n')[:-1]
    if not query_s:
        n_s = ['nessuna azione inserita nel database']
    else:
        n_s = check_thresholds(query_s).format('azione').split('\n')[:-1]
    if not query_bt:
        n_bt = ['nessuna treasury inserita nel database']
    else:
        n_bt = check_thresholds(query_bt).format('treasury').split('\n')[:-1]
    if not query_be:
        n_be = ['nessuna obbligazione etlx inserita nel database']
    else:
        n_be = check_thresholds(query_be).format('ETLX').split('\n')[:-1]
    return render_template('index.html',
                           notification_s=n_s, notification_b=n_b,
                           notification_bt=n_bt, notification_be=n_be)


@app.route('/report')
def report():
    query_s = db_session.query(Stock).all()
    query_b = db_session.query(Bond_IT).all()
    query_bt = db_session.query(Bond_TR).all()
    query_be = db_session.query(Bond_ETLX).all()
    table_s = stock_table(query_s)
    table_b = bond_table(query_b)
    table_be = bond_table(query_be)
    table_bt = bond_tr_table(query_bt)
    costum_s = Const.COSTUM_COLOR_S
    costum_b = Const.COSTUM_COLOR_B
    costum_bt = Const.COSTUM_COLOR_BT
    return render_template('report.html', s=table_s, b=table_b, bt=table_bt,
                           be=table_be, color_s=costum_s, color_b=costum_b,
                           color_bt=costum_bt)


@app.route('/modify', methods=['GET', 'POST'])
def modify():
    if request.method == 'POST':
        # should have catched the key error but works like this too
        # and learned a lot of things:)
        if request.form['command_choice'] == 'def':
            flash("ATTENZIONE:  non hai scelto l'operazione da eseguire!")
            return render_template('modify.html')
        elif request.form['type_choice'] == 'def':
            flash('ATTENZIONE:  non hai scelto il tipo di asset!')
            return render_template('modify.html')
        else:
            cmd = request.form['command_choice']
            session['type_choice'] = request.form['type_choice']
            return redirect(url_for(cmd))
    else:
        return render_template('modify.html')


@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        if session.get('type_choice') == 'stock':
            name = request.form['stock_name']
            symbol = request.form['symbol']
            threshold = request.form['threshold']
            response = add_stock(name, symbol, threshold)
        elif session.get('type_choice') == 'bond_it':
            name = request.form['bond_name']
            isin = request.form['isin']
            threshold = request.form['threshold']
            typology = request.form['typology']
            coupon = request.form['coupon']
            response = add_bond_it(name, threshold, isin, typology, coupon)
        elif session.get('type_choice') == 'bond_tr':
            name = request.form['bond_name']
            threshold = request.form['threshold']
            maturity = request.form['maturity']
            coupon = request.form['coupon']
            response = add_bond_tr(name, threshold, maturity, coupon)
        else:
            name = request.form['bond_name']
            isin = request.form['isin']
            threshold = request.form['threshold']
            response = add_bond_etlx(name, threshold, isin)
        return render_template('modify_results.html', r=response)
    else:
        return render_template('add.html', t=session.get('type_choice'))


@app.route('/remove', methods=['GET', 'POST'])
def remove():
    if request.method == 'POST':
        if session.get('type_choice') == 'stock':
            name = request.form['name']
            response = delete_stock(name)
        elif session.get('type_choice') == 'bond_it':
            name = request.form['name']
            response = delete_bond(name, 1)
        elif session.get('type_choice') == 'bond_tr':
            name = request.form['name']
            response = delete_bond(name, 2)
        else:
            name = request.form['name']
            response = delete_bond(name, 3)
        return render_template('modify_results.html', r=response)
    else:
        return render_template('remove.html', t=session.get('type_choice'))


@app.route('/show')
def show():
    table_s, table_b, table_bt, table_be = show_assets()
    return render_template('show.html', s=table_s, b=table_b, bt=table_bt,
                           be=table_be)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
