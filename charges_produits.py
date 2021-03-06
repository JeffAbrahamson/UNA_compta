#!/usr/bin/env python3

"""Afficher compte par compte toutes les lignes de charges et de
produits.

"""

import argparse
import datetime
import datetime
import jinja2
import os
import piecash

def get_one_account(book):
    """Fetch the list of entries in one account.

    Return a dict whose key is the account name and final balance.
    """
    balance = book.get_balance()
    entries = []
    balance = 0
    for split in book.splits:
        transaction = split.transaction
        for split_line in transaction.splits:
            if split_line.account.name == book.name:
                balance += float(split_line.quantity)
                if split_line.quantity > 0:
                    dx = '{amt:.2f}'.format(amt=split_line.quantity)
                    cx = ''
                else:
                    dx = ''
                    cx = '{amt:.2f}'.format(amt=-split_line.quantity)
                date=transaction.post_date
                descr=transaction.description[:60]
                entry = {'date': date,
                         'description': descr.replace('_', '\_').replace('&', '\&'),
                         'debit': dx,
                         'credit': cx,
                         'balance': '{b:.0f}'.format(b=balance)}
                entries.append(entry)
    return {'name': book.name.replace('_', '\_'),
            'balance': book.get_balance(),
            'lines': entries}

def get_lines(gnucash_filename):
    """Get all the income and expense account entries.

    The gnucash_filename is the sqlite3 format gnucash file of the year's
    accounts.

    The dict returned has keys that are the account names.  The value
    is the account balance.  Since this is a P&L report, we only look
    at 6 and 7 accounts.

    Return a data structure as follows:

       {'charges': charges, 'produits': produits}

    where each of charges and produits is itself a list of dicts as
    returned by get_one_book().

    """
    book = piecash.open_book(gnucash_filename,
                             readonly=True,
                             open_if_lock=True)
    charges = []
    produits = []
    for account in book.accounts:
        if len(account.children) == 0 and account.name[0] in ['6', '7']:
            account_entries = get_one_account(account)
            if len(account_entries['lines']) > 0:
                if account.name[0] == '6':
                    charges.append(account_entries)
                elif account.name[0] == '7':
                    produits.append(account_entries)
                else:
                    print('Account error: {acct}'.format(acct=account.name))
    return {'charges': charges, 'produits': produits}

def generate_pdf(out_filename, template_file, lines):
    """Given a latex template file and the data structure from
    get_lines(), produce a pdf file.

    """
    with open(template_file, 'r') as fp_template:
        template_text = fp_template.read()
    template = jinja2.Template(template_text)
    now = datetime.datetime.now()
    with open(out_filename, 'w') as fp_latex:
        fp_latex.write(template.render(
            charges=lines['charges'],
            produits=lines['produits'],
            quand=now.strftime('%F à %T')))
    os.system('pdflatex ' + out_filename)

def main():
    """Do what we do."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--template', type=str, required=True,
                        help='latex template')
    parser.add_argument('--gnucash', type=str, required=True,
                        help='filename containing sqlite3 gnucash file')
    parser.add_argument('--outfile', type=str, required=True,
                        help='filename of output tex/pdf')
    args = parser.parse_args()
    lines = get_lines(args.gnucash)
    generate_pdf(args.outfile, args.template, lines)

if __name__ == '__main__':
    main()
