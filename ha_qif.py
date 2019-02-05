#!/usr/bin/python3

"""Convert helloasso CSV file to QIF that gnucash can read.
"""

import argparse
import dateutil.parser as dp
import pandas as pd
import sys
from tabulate import tabulate

# We have several get_data() functions, as the format changes slightly
# from campaign to campaign.  The dataframe that they each return should
# be the same format.

def get_account_mappings(config_filename):
    """Get the mapping from helloasso descriptions to accounts.

    This is a python-format config file in the form of a dict, each of
    whose keys corresponds to a description value in the import file.
    The values are dicts, one key is "default" and,if present,
    represents the default account for that description.  The other
    key is "subdescr" with value a dict mapping subaccount
    descriptions to accounts.

    """
    with open(config_filename, 'r') as config_fp:
        config = eval(config_fp.read())
    return config

def fullname(row):
    """The human's full name.
    """
    email_1 = str(row['Email'])
    email_2 = str(row['Champ additionnel: Email'])
    email_3 = str(row['Champ additionnel: Email contributeur'])
    emails = set([email_1, email_2, email_3])
    other_emails = emails.difference(set([email_1]))
    email = email_1.strip()
    if other_emails:
        other_email = list(other_emails)[0].strip()
        if 'nan' == other_email:
            other_email = email_1
    else:
        other_email = email_1.strip()

    fn = str(row['Prénom'])
    ln = str(row['Nom'])
    name = '{fn} {ln} <{em}>'.format(
        fn=fn, ln=ln, em=email)
    other_fn = str(row['Prénom acheteur'])
    other_ln = str(row['Nom acheteur'])
    other_name = '{fn} {ln} <{em}>'.format(
        fn=other_fn, ln=other_ln, em=other_email)

    if name == other_name:
        return name
    return '{n} (via {on})'.format(n=name, on=other_name)

def find_account(config, descr, sub_descr, don):
    if don:
        return '746_Dons'
    if descr not in config:
        print('Missing description: "{d}"'.format(d=descr))
        sys.exit(1)
    descr_account = config[descr]
    if 'subdescr' in descr_account and sub_descr in descr_account['subdescr']:
        return descr_account['subdescr'][sub_descr]
    if 'default' in descr_account:
        return descr_account['default']
    print('Missing sub-description for "{d}": "{sd}"'.format(d=descr, sd=sub_descr))
    sys.exit(1)

def make_find_account(config):
    def this_find_account(row):
        ret = find_account(config, row['description'], row['sub_description'],
                           'Don unique' == row['Type'])
        if type(ret) != str:
            print(type(ret))
            print('{d}//{s}//{n}'.format(d=row['description'],
                                         s=row['sub_description'],
                                         n=('Don unique' == row['Type'])))
            print(row)
        return find_account(config, row['description'], row['sub_description'],
                            'Don unique' == row['Type'])
    return this_find_account

def piece_comptable(row):
    """Create the accounting ID in the format I want.
    """
    xact_date = row['transaction_yyyymmdd']
    xact_id = row['Numéro']
    return 'HA-{date}-{id}'.format(date=xact_date, id=xact_id)

def entry_remark(row):
    """Create the value for the entry's remark field.
    """
    this_fullname = row['fullname']
    return '{d})'.format(d=this_fullname)

def get_data(infile, config):
    """Read dataframe from CSV file and return view.
    """
    data = pd.read_csv(
        infile,
        sep=';',
    )
    data['amount'] = pd.Series(
        [float(s.replace(',', '.'))
         for s
         in data['Montant']])
    data['transaction_date_yyyy_mm_dd'] = pd.Series(
        [dp.parse(val, dayfirst=True)
         for val
         in data.Date])
    data['transaction_date_qif'] = pd.Series([
        '{d:0>2d}/{m:0>2d}/{y:0>4d}'.format(y=val.year, m=val.month, d=val.day)
        for val
        in data.transaction_date_yyyy_mm_dd])
    data['transaction_yyyymmdd'] = pd.Series([
        '{y:0>4d}{m:0>2d}{d:0>2d}'.format(y=val.year, m=val.month, d=val.day)
        for val
        in data.transaction_date_yyyy_mm_dd])
    data['description'] = pd.Series(
        [val.strip()
         for val
         in data.Campagne])
    data['sub_description'] = pd.Series(
        [str(val).strip()
         for val
         in data.Désignation])

    # This sometimes needs to be customised to be a switch
    # on data.Formule.
    this_find_account = make_find_account(config)
    data['account'] = data.apply(this_find_account, axis=1)
    data['fullname'] = data.apply(fullname, axis=1)
    data['piece-comptable'] = data.apply(piece_comptable, axis=1)
    data['remark'] = data.apply(entry_remark, axis=1)

    data_valid = data[data['Statut'] == 'Validé']
    data_view = data_valid[['transaction_date_yyyy_mm_dd', 'transaction_date_qif',
                            'description', 'sub_description', 'fullname',
                            'piece-comptable', 'remark', 'amount', 'account']]
    return data_view.sort_values(by=['transaction_date_yyyy_mm_dd'])

def print_table(data_view):
    """Print a human-readable summary of the data.
    """
    data_view['date'] = data_view['transaction_date_yyyy_mm_dd']
    table_data_view = data_view[['date', 'amount', 'fullname']]
    print(tabulate(table_data_view, showindex=False, tablefmt='fancy_grid', headers='keys'))

def make_qif(data_view):
    """Build qif file from dataframe.

    The dataframe should have columns as provided by get_data(), above.
    We want a qif so that we can construct splits.

    Cf. https://en.wikipedia.org/wiki/Quicken_Interchange_Format
    """
    qif_data_view = data_view[['transaction_date_qif', 'piece-comptable', 'remark',
                               'fullname', 'description', 'amount', 'account']]
    qif = '!Account\n'
    qif += 'N512151_Helloasso\n'
    qif += '^\n'
    qif += '!Type:Bank\n'
    def qif_entry(row):
        """Create a single QIF file entry.
        """
        this_transaction_date = row['transaction_date_qif']
        this_piece_comptable = row['piece-comptable']
        this_remark = row['remark']
        this_description = row['description']
        this_amount = row['amount']
        this_fullname = row['fullname']
        this_account = row['account']

        # D is the date.  It may be required to be in English "dd mmmm
        #   yyyy" format.
        # T is the amount of the transaction.
        # N is the id number (pièce comptable).
        # P is the payee (which quicken thinks of as the comment, not the account)
        # M is a memo
        entry = 'D{date}\nT{total}\nN{pc}\nP{payee}\nM{memo}\n'.format(
            date=this_transaction_date,
            total=this_amount,
            pc=this_piece_comptable, payee='{fn}'.format(fn=this_fullname),
            memo=this_description)
        # S is the split category (account number on split line).
        # $ is the amount of the split entry.
        # E is the split memo.
        split_line = 'S{cpty}\n${amt}\nE{memo}\n'
        entry += split_line.format(
            cpty=this_account,
            amt=-this_amount,
            memo=this_remark)
        return entry
    rows = qif_data_view.to_dict('records')
    transactions = []
    for row in rows:
        if row['amount'] != 0:
            transactions.append(qif_entry(row))
    qif += '\n^\n'.join(transactions) + '\n^\n'
    return qif

def main():
    """Do what we do.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--infile', type=str, required=True,
                        help='Name of file to read')
    parser.add_argument('--config', type=str, required=True,
                        help='config file mapping descriptions to accounts')
    parser.add_argument('--outfile', type=str, required=False,
                        help='Name of file to write')
    parser.add_argument('--format', type=str, required=False,
                        default='table',
                        help='Output format type (table, qif)')
    args = parser.parse_args()

    config = get_account_mappings(args.config)
    data_view = get_data(args.infile, config)
    if 'qif' == args.format:
        qif = make_qif(data_view)
        if args.outfile:
            with open(args.outfile, 'w') as f_ptr:
                f_ptr.write(qif)
        else:
            print(qif)
        return 0
    if 'table' == args.format:
        print_table(data_view)
        return 0
    print('Unknown format: ', args.format)
    return 1

if __name__ == '__main__':
    retval = main()
    sys.exit(retval)
