#!/usr/bin/python3

"""Compute a (French-style) balance sheet.

The input is an EBP text export of the current year's books.
"""

import argparse
import datetime
import pandas as pd
import jinja2
import os
import datetime

def valid_date(date_str):
    """Parse a date for argparse.
    """
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(date_str)
        raise argparse.ArgumentTypeError(msg)

def get_data(book_filename, max_date):
    """Fetch book data, return as a pandas DataFrame.
    """
    with open(book_filename, 'r') as book_fp:
        book = pd.read_csv(
            book_fp, sep=';', header=0,
            names=["Code journal", "Description du journal", "Date",
                   "Date au format L47", "account", "Intitulé du compte",
                   "Pièce", "Date de pièce", "Document", "Libellé", "Débit",
                   "Crédit", "Montant",
                   "Montant (associé au sens)", "Sens", "Statut",
                   "Date de lettrage", "Lettrage", "Partiel",
                   "Date de l'échéance", "Moyen de paiement", "Notes",
                   "N° de ligne pour les documents associés",
                   "Documents associés", "Plan analytique", "Poste analytique"],
            usecols=["Date", "account", "Intitulé du compte",
                     "Pièce", "Date de pièce", "Document", "Libellé",
                     "Montant"],
            parse_dates=['Date', 'Date de pièce'],
            dayfirst=True,
        )
    if max_date is None:
        filtered_book = book
    else:
        filtered_book = book[book.Date <= max_date]
    return filtered_book

def get_account_balances(book_filename, max_date):
    """Read and interpret data, compute account balances as a dict.

    The book_filename is a text export of the year's accounts (le
    grand livre).

    The dict returned has keys that are the account names.  The value
    is the account balance.

    """
    book = get_data(book_filename, max_date)
    # Make dict of { account -> balance }.
    account_sums = book.groupby(['account']).sum().to_dict()['Montant']
    return account_sums

def compute_balance_sheet_list(config_column, balances):
    """Compute one side of a balance sheet.

    The input is the part of the config that represents a column of
    the balance sheet (expeneses or income) and a map from account
    name to balance.

    The output is a list of lists, each of which has either one
    element (a title string) or three elements (a label, a budget, and
    a balance).

    """
    balance_sheet_column = []
    for line in config_column:
        if len(line) == 1:
            balance_sheet_column.append(line)
        else:
            these_accounts = set(line[2])
            balance = abs(sum([balance for account, balance in balances.items()
                               if account in these_accounts]))
            balance_sheet_column.append([line[0], line[1], balance])
    return balance_sheet_column

def scan_for_missing_accounts(config_column, balance_accounts):
    """Print any expense or income accounts (6, 7) not in the config.

    The data format of config_column is as for
    compute_balance_sheet_list, above, though here it is both columns
    and not just once side.

    The balance_accounts is a list of accounts seen in the general ledger.

    """
    config_accounts = set()
    for line in config_column:
        if len(line) > 1:
            these_accounts = set(line[2])
            config_accounts = config_accounts.union(these_accounts)
    income_expense_accounts = set()
    income_or_expense = set(['6', '7'])
    for account in balance_accounts:
        if account[0] in income_or_expense:
            income_expense_accounts.add(account)
    print('Missing accounts from config: {m}'.format(
        m=income_expense_accounts - config_accounts))

def get_balance_sheet_as_list(config_filename, balances):
    """Group account balances as requested by the config.

    The contents of config_filename is python code.  It should be a
    list of two lists, each of which contains two or three members:
      - The balance sheet line name
      - Budget (eventually should go to a separate file)
      - Either absent or a list of accounts to aggregate.  If absent,
        then this is a title.

    The returned list contains two lists, the first for expenses, the
    second for income.  In each list, the elements contain a list
    which has one element (a title) or three (a label, a budget, and a
    realised amount spent or received).

    """
    with open(config_filename, 'r') as config_fp:
        config = eval(config_fp.read())
    expenses = compute_balance_sheet_list(config[0], balances)
    income = compute_balance_sheet_list(config[1], balances)
    scan_for_missing_accounts(config[0] + config[1],
                              [account for account, balance in balances.items()])
    return [expenses, income]

def get_balance_sheet(config_filename, book_filename, max_date):
    """Fetch data and return a balance sheet as a list of two lists.
    """
    balances = get_account_balances(book_filename, max_date)
    balance_sheet = get_balance_sheet_as_list(config_filename, balances)
    sum_expenses = sum([line[2] for line in balance_sheet[0]
                        if len(line) == 3])
    sum_income = sum([line[2] for line in balance_sheet[1]
                        if len(line) == 3])
    result = sum_income - sum_expenses
    balance_sheet[0].append(["Résultat de l'exercice", 0, result])
    return balance_sheet

def render_as_text_one_column(balance_sheet_column):
    """Render one column of a balance sheet as text.
    """
    total_budget = 0
    total_realised = 0
    for line in balance_sheet_column:
        if len(line) == 1:
            print('\n', line[0])
        else:
            total_budget += line[1]
            total_realised += line[2]
            print('{label:40s}  {budget:6.2f}  {realised:6.2f}'.format(
                label=line[0], budget=line[1], realised=line[2]))
    print('{nothing:40s}  {budget:6.2f}  {realised:6.2f}'.format(
        nothing='', budget=total_budget, realised=total_realised))

def render_as_text(balance_sheet):
    """Print the balance sheet to stdout as text in a single column.

    The balance sheet is in list of lists format.  The first list is
    expenses, the second income.  Cf comment in
    get_balance_sheet_as_list() for more.

    """
    print('==== Dépenses ====')
    render_as_text_one_column(balance_sheet[0])
    print('\n==== Recettes ====')
    render_as_text_one_column(balance_sheet[1])

def render_as_latex_one_column(balance_sheet_column):
    """Return a string that is the latex for one column.

    We're in a tabu environment with three columns.  Return a sequence
    of "label & budget & balance" lines.

    """
    table = ""
    total_budget = 0
    total_realised = 0
    for line in balance_sheet_column:
        if len(line) == 1:
            table += r'\textbf{{ {label} }}&&\\'.format(label=line[0])
            table += '\n'
        else:
            total_budget += line[1]
            total_realised += line[2]
            table += r'{label}&{budget:6.0f}&{realised:6.0f}\\[1mm]'.format(
                label=line[0], budget=line[1], realised=line[2])
            table += '\n'
    table += r'\hline' + '\n'
    table += r'Total & {budget:6.0f} & {realised:6.0f}\\'.format(
        nothing='', budget=total_budget, realised=total_realised)
    table += '\n'
    return table;

def render_as_latex(balance_sheet):
    """Print the balance sheet to bilan_<date>.tex as latex.

    The balance sheet is in list of lists format.  The first list is
    expenses, the second income.  Cf comment in
    get_balance_sheet_as_list() for more.

    Latex the file to create bilan_<date>.pdf.

    """
    with open('bilan.tex', 'r') as fp_template:
        template_text = fp_template.read()
    template = jinja2.Template(template_text)
    out_filename = 'bilan_{date}.tex'.format(date=datetime.date.today().strftime('%Y%m%d'))
    with open(out_filename, 'w') as fp_latex:
        fp_latex.write(template.render(
            expenses=render_as_latex_one_column(balance_sheet[0]),
            income=render_as_latex_one_column(balance_sheet[1])))
    os.system('pdflatex ' + out_filename)

def main():
    """Do what we do."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True,
                        default='',
                        help='config file mapping accounts to BS lines')
    parser.add_argument('--book', type=str, required=False,
                        default='/home/jeff/work/UNA/comite-directeur/trésorier/' +
                        'ebp-compta-exports/export.txt',
                        help='filename containing text export of book')
    parser.add_argument('--max_date', type=valid_date, required=False,
                        default=None,
                        help='Cut-off date for inclusion in balance sheet, format YYYY-MM-DD')
    parser.add_argument('--render-as', type=str, required=False,
                        default='text',
                        help='One of text or latex')
    args = parser.parse_args()
    balance_sheet = get_balance_sheet(args.config, args.book, args.max_date)
    if 'text' == args.render_as:
        render_as_text(balance_sheet)
    if 'latex' == args.render_as:
        render_as_latex(balance_sheet)

if __name__ == '__main__':
    main()
