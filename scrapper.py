import click
from data.const import Const
from data.database import session, init_db
from data.models import Bond, Stock
from data.processing import update_db, check_thresholds
from data.processing import delete_stock, delete_bond, add_stock, add_bond
from data.processing import stock_table, bond_table, show_assets
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
            table = stock_table(stocks)
            pretty_s = format_pretty_table(table[1:], column_names=table[0])
            text_s = '{}\n{}\n\n'.format(notification_s.format('azione'),
                                         pretty_s)
        else:
            text_s = '\nATTENZIONE nessuna azione inserita nel database'

        if notification_b is not None:
            table = bond_table(bonds)
            pretty_b = format_pretty_table(table[1:], column_names=table[0])
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
    if bond:
        n, i, t = bond
        response = add_bond(n, i, t)
        click.echo(response)
    if stock:
        n, s, t = stock
        response = add_stock(n, s, t)
        click.echo(response)


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
        if bond and click.confirm(prompt.format(bond), default=False):
            click.echo(delete_bond(bond))
        if stock and click.confirm(prompt.format(stock), default=False):
            click.echo(delete_stock(stock))


@cli.command()
def show():
    '''mostra le azioni e obbligazioni inserite'''
    table_s, table_b = show_assets()
    pretty_table_s = format_pretty_table(table_s[1:], table_s[0])
    pretty_table_b = format_pretty_table(table_b[1:], table_b[0])
    click.echo_via_pager('{}\n{}'.format(pretty_table_s, pretty_table_b))


if __name__ == '__main__':
    cli()
