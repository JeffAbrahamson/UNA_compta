#!/usr/bin/env python3

"""Compute a (French-style) budget tracking (suivie budgétaire).

The input is a text export of the current year's books, as output by
una_canonical.py.

"""

import argparse
import datetime
import datetime
import jinja2
import numpy as np
import os
import pandas as pd
import piecash

def get_account_balances(book_filename):
    """Read and interpret data, compute account balances as a dict.

    The book_filename is the sqlite3 format gnucash file of the year's
    accounts.

    The dict returned has keys that are the account names.  The value
    is the account balance.  Since this is a P&L report, we only look
    at 6 and 7 accounts.

    """
    book = piecash.open_book(book_filename,
                             readonly=True,
                             open_if_lock=True)
    account_sums = {}
    for account in book.accounts:
        if len(account.children) == 0 and account.name[0] in ['6', '7']:
            balance = account.get_balance()
            if balance != 0:
                account_sums[account.name] = balance
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
            balance = sum([balance for account, balance in balances.items()
                           if account in these_accounts])
            balance_sheet_column.append([line[0], line[1], balance])
    return balance_sheet_column

def scan_for_missing_accounts(config_column, balance_accounts):
    """Print any expense or income accounts (6, 7) not in the config.

    The data format of config_column is as for
    compute_balance_sheet_list, above, though here it is both columns
    and not just one side.

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
    missing_accounts = income_expense_accounts - config_accounts
    if len(missing_accounts) > 0:
        warning_separator = '================'
        print('{sep}\nMissing accounts from config: {m}\n{sep}'.format(
            sep=warning_separator,
            m=missing_accounts))

def get_balance_sheet_as_list(config_filename, balances):
    """Group account balances as requested by the config.

    The contents of config_filename is python code.  It should be a
    list of two lists, each of which contains one or three members:
      - The balance sheet line name.  If this is the only list element,
        then it is a title.
      - Budget (eventually should go to a separate file)
      - A list of accounts to aggregate.

    The dict balances maps account name to account balance.

    The returned list contains two lists, the first for expenses, the
    second for income.  In each list, the elements contain a list
    which has one element (a title) or three (a label, a budget, and a
    realised amount spent or received).

    """
    with open(config_filename, 'r') as config_fp:
        config = eval(config_fp.read())
    expenses = compute_balance_sheet_list(config[0], balances)
    income = compute_balance_sheet_list(config[1], balances)
    ## Double check that we've got everything.
    account_expenses = sum([v for k,v in balances.items() if k[0] == '6'])
    account_income = sum([v for k,v in balances.items() if k[0] == '7'])
    display_expenses = sum([x[2] for x in expenses if len(x) == 3])
    display_income = sum([x[2] for x in income if len(x) == 3])
    if account_expenses != display_expenses or \
       account_income != display_income:
        print('Unexpected imbalance:')
        print('            {e:>11s}    {i:>11s}'.format(e='Expenses', i='Income'))
        print('  Balances: {ge:11.2f}    {gi:11.2f}'.format(ge=account_expenses, gi=account_income))
        print('  Display:  {de:11.2f}    {di:11.2f}'.format(de=display_expenses, di=display_income))
        print('')
    ## End double-check.
    scan_for_missing_accounts(config[0] + config[1],
                              [account for account, balance in balances.items()])
    return [expenses, income]

def get_balance_sheet(config_filename, book_filename):
    """Fetch data and return a balance sheet as a list of two lists.
    """
    balances = get_account_balances(book_filename)
    balance_sheet = get_balance_sheet_as_list(config_filename, balances)
    sum_expenses = sum([line[2] for line in balance_sheet[0]
                        if len(line) == 3])
    sum_income = sum([line[2] for line in balance_sheet[1]
                        if len(line) == 3])
    result = sum_income - sum_expenses
    if result > 0:
        balance_sheet[0].append(["Résultat de l'exercice", 0, result])
    else:
        balance_sheet[1].append(["Résultat de l'exercice", 0, -result])
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

def render_as_latex(out_filename, template_filename, balance_sheet):
    """Print the balance sheet to budget_<date>.tex as latex.

    The balance sheet is in list of lists format.  The first list is
    expenses, the second income.  Cf comment in
    get_balance_sheet_as_list() for more.

    Latex the file to create budget_<date>.pdf.

    """
    with open(template_filename, 'r') as fp_template:
        template_text = fp_template.read()
    template = jinja2.Template(template_text)
    now = datetime.datetime.now()
    with open(out_filename, 'w') as fp_latex:
        fp_latex.write(template.render(
            expenses=render_as_latex_one_column(balance_sheet[0]),
            income=render_as_latex_one_column(balance_sheet[1]),
            quand=now.strftime('%F à %T')))
    os.system('pdflatex ' + out_filename)

def main():
    """Do what we do."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True,
                        help='config file mapping accounts to budget lines')
    parser.add_argument('--template', type=str, required=True,
                        help='latex template')
    parser.add_argument('--gnucash', type=str, required=True,
                        help='filename containing sqlite3 gnucash file')
    parser.add_argument('--outfile', type=str, required=True,
                        help='filename of output tex/pdf')
    parser.add_argument('--format', type=str, required=False,
                        default='text',
                        help='One of text or latex')
    args = parser.parse_args()
    balances = get_balance_sheet(args.config, args.gnucash)
    if 'text' == args.format:
        render_as_text(balances)
    if 'latex' == args.format:
        render_as_latex(args.outfile, args.template, balances)

if __name__ == '__main__':
    main()
