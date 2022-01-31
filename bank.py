from datetime import datetime, timedelta

import click
from click_shell import shell
import sqlite3
from tabulate import tabulate

clients = [("John Jones",),
           ("Jane Doe",)]


def create_connection(db_name):
    """Создание связи для заданной базы данных
    :arg db_name: название базы данных
    :return: con
    """
    con = None
    try:
        con = sqlite3.connect(db_name)
        return con
    except sqlite3.Error as e:
        print(e)
    return con


def create_table(connect, create_table_sql):
    """Создание таблицы из заданного query
    :param connect
    :param create_table_sql: заданный query
    """
    try:
        c = connect.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)


def drop_tables(connect, tables):
    """Удаление всех таблиц из базы данных
    :param connect:
    :param tables: название созданных таблиц
    """
    try:
        c = connect.cursor()
        for table in tables:
            c.execute(f"DROP TABLE IF EXISTS {table}")
    except sqlite3.Error as e:
        print(e)


def create_db(db_name):
    """
    :param db_name: название базы данных
    """
    clients_table_sql = """CREATE TABLE "clients" (
        	"id"	INTEGER PRIMARY KEY AUTOINCREMENT ,
        	"name"	TEXT NOT NULL
        )"""
    deposit_table_sql = """CREATE TABLE "deposit" (
    	"id"	INTEGER PRIMARY KEY AUTOINCREMENT,
    	"client_id"	INTEGER NOT NULL,
    	"date"	TEXT NOT NULL,
    	"d_amount"	INTEGER,
    	"description" TEXT,
    	FOREIGN KEY (client_id)
           REFERENCES clients (id)
    )"""
    withdraw_table_sql = """CREATE TABLE "withdraw" (
    	"id"	INTEGER PRIMARY KEY AUTOINCREMENT,
    	"client_id"	INTEGER NOT NULL,
    	"date"	TEXT NOT NULL,
    	"w_amount"	INTEGER,
    	"description" TEXT,
    	FOREIGN KEY (client_id)
           REFERENCES clients (id)
    )"""
    con = create_connection(db_name)
    drop_tables(con, ("clients", "deposit", "withdraw"))
    create_table(con, clients_table_sql)
    create_table(con, deposit_table_sql)
    create_table(con, withdraw_table_sql)
    con.executemany("INSERT INTO clients(name) VALUES(?)", clients)
    con.commit()


@shell(prompt='> ')
def cli():
    """Запуск shell"""
    create_db('bank.db')
    click.echo(f"Service started!")


@cli.command()
@click.option("--client", help="Information about client.")
@click.option("--amount", default=0, help="Amount of money.")
@click.option("--description", prompt="", help="Description of the deposit.")
def deposit(client, amount, description):
    """Операция пополнения счета на сумму
    :param client: имя клиента
    :param amount: количество пополнения
    :param description: описание операции
    """
    con = create_connection('bank.db')
    c = con.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO deposit(client_id, date, d_amount, description) "
              "VALUES ((SELECT id from clients WHERE clients.name=?), ?, ?, ?)",
              (client, date, amount, description))
    con.commit()
    click.echo(f"Deposit operation was successful!")


@cli.command()
@click.option("--client", help="Information about client.")
@click.option("--amount", default=0, help="Amount of money.")
@click.option("--description", help="Description of the withdrawal.")
def withdraw(client, amount, description):
    """Операция снятия со счета
    :param client: имя клиента
    :param amount: количество пополнения
    :param description: описание операции
    """
    con = create_connection('bank.db')
    c = con.cursor()
    date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO withdraw(client_id, date, w_amount, description) "
              "VALUES ((SELECT id from clients WHERE clients.name=?), ?, ?, ?)",
              (client, date, amount, description))
    con.commit()
    click.echo(f"Withdraw operation was successful!")


@cli.command()
@click.option("--client")
@click.option("--since", type=click.DateTime(formats=["%Y-%m-%d %H:%M:%S"]))
@click.option("--till", type=click.DateTime(formats=["%Y-%m-%d %H:%M:%S"]))
def show_bank_statement(client, since, till):
    """Вывод на экран выписки со счета за период,
    :param client: имя клиента
    :param since: дата начала периода
    :param till: дата окончания периода
    """
    table_data = [
        ['Date', 'Description', 'Withdrawals', 'Deposits', 'Balance'],
        ['', 'Previous balance', '', '', '$'],
        ['', 'Totals', '', '', '']
    ]
    con = create_connection('bank.db')
    c = con.cursor()
    c.execute("""DROP TABLE if exists Bank_Data""")
    c.execute(
        """
        CREATE TABLE Bank_Data as 
        SELECT *, sum(IFNULL(Deposits, 0) - IFNULL(Withdrawals, 0)) over (order by date) as Balance
        FROM
        (SELECT date as Date, description as Description, null as Withdrawals, d_amount as Deposits  from deposit
        left join clients on deposit.client_id=clients.id
        where clients.name=?
        UNION ALL
        SELECT date as Date, description as Description, w_amount as Withdrawals, null as Deposits from withdraw
        left join clients on withdraw.client_id=clients.id
        where clients.name=?)
        where date BETWEEN ? and ?
        GROUP by Date
        """, (client, client, since, till))
    data = c.execute("""
    select * from Bank_Data
    UNION
    select null as date,
        'Previous balance',
        null as Withdrawals,
        null as Deposits,
        ifnull((SELECT Balance FROM Bank_Data ORDER BY date DESC LIMIT 1),0)
    from Bank_Data
    UNION ALL
    select null as date,
        'Totals',
        sum(Withdrawals),
        sum(Deposits),
        ifnull((SELECT sum(deposits) - sum(Withdrawals) FROM Bank_Data ORDER BY date),0)
        from Bank_Data
        """)
    result = c.fetchall()

    click.echo(print(tabulate(result,
                              headers=['Date', 'Description', 'Withdrawals', 'Deposits', 'Balance'],
                              tablefmt='grid')))


if __name__ == '__main__':
    cli()
