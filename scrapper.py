import click
from data.const import Const
from data.database import session, init_db
from data.models import Bond, Stock
from data.processing import update_db, check_thresholds
from sqlalchemy.exc import IntegrityError
from os.path import isfile
from humanfriendly.tables import format_pretty_table


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if not isfile(Const.DB):
        init_db()
    if not isfile(Const.CONFIGS):
        with open(Const.CONFIGS, 'w') as f:
            f.write('2000-01-01 00:00:00.000000\n')
            f.write('2000-01-01 00:00:00.000000\n')
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option('--forced', is_flag=True)
@click.option('--stock', 'only_one', flag_value='stock',
              help='controlla solo le azioni')
@click.option('--bond', 'only_one', flag_value='bond',
              help='controlla solo le obbligazioni')
def get(forced, only_one):
    '''attiva il programma'''
    stock_columns_names = ['soglia', 'nome', 'progresso', 'prezzo', 'variazione']
    bond_columns_names = ['soglia', 'nome', 'progresso', 'prezzo', 'max_y', 'min_y',
                          'yield_y', 'yield']

    if forced:
        click.echo('\nAggiorno il database\n')
    else:
        click.echo('\nAggiorno il database se necessario\n')
    try:
        update_db(forced)
        stocks = session.query(Stock).all()
        bonds = session.query(Bond).all()
        notification_s = check_thresholds(stocks)
        notification_b = check_thresholds(bonds)

        if notification_s is not None:
            content_s = [[s.threshold, s.name.lower(), s.progress, s.price,
                          s.variation] for s in stocks]
            content_s.sort(key=lambda x: x[1])
            pretty_s = format_pretty_table(content_s, stock_columns_names)
            text_s = '{}\n{}\n\n'.format(notification_s.format('azione'),
                                         pretty_s)
        else:
            text_s = '\nATTENZIONE nessuna azione inserita nel database'

        if notification_b is not None:
            raw_content_b = [[b.threshold, b.name, b.progress, b.price,
                              b.max_y, b.min_y, b.yield_y, b.yield_tot,
                              b.maturity] for b in bonds]
            raw_content_b.sort(key=lambda x: x[-1])
            content_b = [line[:-1] for line in raw_content_b]
            pretty_b = format_pretty_table(content_b, bond_columns_names)
            text_b = '{}\n{}\n\n'.format(notification_b.format('obbligazione'),
                                         pretty_b)
        else:
            text_b = '\nATTENZIONE nessuna obbligazione inserita nel database'

        if only_one == 'stock':
            click.echo(text_s)
        elif only_one == 'bond':
            click.echo(text_b)
        else:
            click.echo(''.join([text_s, text_b]))
    except SystemExit:
        click.echo('\nATTENZIONE nessuna connessione internet')


@cli.command()
@click.option('--bond', nargs=3, type=str, default=(),
              help='obbligazione : NOME-CEDOLA ISIN SOGLIA')
@click.option('--stock', nargs=3, type=str, default=(),
              help='azione : NOME SIMBOLO SOGLIA')
def add(bond, stock):
    ''' aggiungi un azione o obbligazione'''
    # sqlalchemy.exc.IntegrityError da gestire
    success = '\n{} inserito!'
    try:
        if bond:
            name, isin, threshold = bond
            if threshold[0] is not '+':
                threshold = ''.join(['-', threshold])
            session.add(Bond(name=name, isin=isin, threshold=threshold))
            session.commit()
            click.echo(success.format(name))
        if stock:
            name, symbol, threshold = stock
            if threshold[0] is not '+':
                threshold = ''.join(['-', threshold])
            session.add(Stock(name=name, symbol=symbol, threshold=threshold))
            session.commit()
            click.echo(success.format(name))
        update_db(forced=True)
    except IntegrityError:
        click.echo('\nATTENZIONE simbolo o isin gia presente')


@cli.command()
@click.option('--mod', default='', help='modifica la soglia di notifica')
@click.option('--bond', default='',
              help='NOME obbligazione da rimuovere o modificare')
@click.option('--stock', default='',
              help='NOME azione da rimuovere o modificare')
def remove(mod, bond, stock):
    '''rimuovi un azione o obbligazione'''
    if mod:
        if bond:
            for b in session.query(Bond).filter(Bond.name == bond):
                b.threshold = mod
            session.commit()
        if stock:
            for s in session.query(Stock).filter(Stock.name == stock):
                s.threshold = mod
            session.commit()
    else:
        prompt = 'Vuoi davvero cancellare {}'
        if bond:
            if click.confirm(prompt.format(bond), default=False):
                for b in session.query(Bond).filter(Bond.name == bond):
                    session.delete(b)
                session.commit()

        if stock:
            if click.confirm(prompt.format(stock), default=False):
                for s in session.query(Stock).filter(Stock.name == stock):
                    session.delete(s)
                session.commit()


@cli.command()
def show():
    '''mostra le azioni e obbligazioni inserite'''
    stock_columns_names = ['nome', 'simbolo', 'soglia']
    bond_columns_names = ['nome', 'isin', 'soglia']
    stocks = session.query(Stock).all()
    bonds = session.query(Bond).all()
    content_s = [[s.name, s.symbol, s.threshold] for s in stocks]
    content_b = [[b.name, b.isin, b.threshold] for b in bonds]
    pretty_table_s = format_pretty_table(content_s, stock_columns_names)
    pretty_table_b = format_pretty_table(content_b, bond_columns_names)
    click.echo_via_pager('{}\n{}'.format(pretty_table_s, pretty_table_b))


if __name__ == '__main__':
    cli()
