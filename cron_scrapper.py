from json import dumps, load
from data.const import Const
from data.database import session
from data.models import Bond_IT, Bond_TR, Stock, Bond_ETLX
from data.processing import update_db
from datetime import date


def db_to_json():
    now = str(date.today())
    with open(Const.LOG, 'r') as f:
        daily_logs = load(f)
    if now not in daily_logs:
        st = session.query(Stock).all()
        bit = session.query(Bond_IT).all()
        btr = session.query(Bond_TR).all()
        bte = session.query(Bond_ETLX).all()
        st_nor = [{
            'nome': q.name, 'soglia': q.threshold, 'prezzo': q.price,
            'progresso': q.progress, 'variazione': q.variation}
            for q in st]
        bit_nor = [{
            'nome': q.name, 'soglia': q.threshold, 'prezzo': q.price,
            'progresso': q.progress, 'yield_y': q.yield_y,
            'yield_tot': q.yield_tot}
            for q in bit]
        btr_nor = [{
            'nome': q.name, 'soglia': q.threshold, 'prezzo': q.price,
            'progresso': q.progress, 'yield_y': q.yield_y,
            'yield_tot': q.yield_tot}
            for q in btr]
        bte_nor = [{
            'nome': q.name, 'soglia': q.threshold, 'prezzo': q.price,
            'progresso': q.progress, 'yield_y': q.yield_y,
            'yield_tot': q.yield_tot}
            for q in bte]
        data = {
            'stock': st_nor,
            'bond_it': bit_nor,
            'bond_tr': btr_nor,
            'bond_etlx': bte_nor}
        daily_logs[now] = data
        with open(Const.LOG, 'w') as f:
            f.write(dumps(daily_logs))


if __name__ == '__main__':
    try:
        db_to_json()
        update_db()
        # check_email()
    except SystemExit:
        pass
