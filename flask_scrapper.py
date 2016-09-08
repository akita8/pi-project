from data.const import Const
from data.database import session as db_session
from data.models import Stock, Bond
from data.processing import stock_table, bond_table, update_db, show_assets
from data.processing import check_thresholds
from data.processing import add_bond, add_stock, delete_bond, delete_stock
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
    query_b = db_session.query(Bond).all()
    n_s = check_thresholds(query_s).format('azione').split('\n')[:-1]
    n_b = check_thresholds(query_b).format('obbligazione').split('\n')[:-1]
    if n_b is None:
        n_b = ['nessuna obbligazione inserita nel database']
    elif n_s is None:
        n_s = ['nessuna azione inserita nel database']
    return render_template('index.html', notification_s=n_s,
                           notification_b=n_b)


@app.route('/report')
def report():
    update_db()
    query_s = db_session.query(Stock).all()
    query_b = db_session.query(Bond).all()
    table_s = stock_table(query_s)
    table_b = bond_table(query_b)
    costum_s = Const.COSTUM_COLOR_S
    costum_b = Const.COSTUM_COLOR_B
    return render_template('report.html', s=table_s, b=table_b,
                           color_s=costum_s, color_b=costum_b)


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
        else:
            name = request.form['bond_name']
            isin = request.form['isin']
            threshold = request.form['threshold']
            response = add_bond(name, isin, threshold)
        return render_template('modify_results.html', r=response)
    else:
        return render_template('add.html', t=session.get('type_choice'))


@app.route('/remove', methods=['GET', 'POST'])
def remove():
    if request.method == 'POST':
        if session.get('type_choice') == 'stock':
            name = request.form['name']
            response = delete_stock(name)
        else:
            name = request.form['name']
            response = delete_bond(name)
        return render_template('modify_results.html', r=response)
    else:
        return render_template('remove.html', t=session.get('type_choice'))


@app.route('/show')
def show():
    table_s, table_b = show_assets()
    return render_template('show.html', s=table_s, b=table_b)
