#!/usr/bin/python3

"""Convert FFA downloads (CSV) to QIF for import to gnucash.
"""

import argparse
import dateutil.parser as dp
import pandas as pd
import sys
import base64

def piece_comptable(row):
    """Create the accounting ID in the format I want.
    """
    xact_date_raw = row['DATE ECR']
    # Remove time part of date, everything after the first space; also
    # remove '/'.
    xact_date = xact_date_raw[:xact_date_raw.find(' ')].replace('/','')
    xact_id = base64.urlsafe_b64encode(xact_date.encode('ascii')).decode()
    return 'FFA-{date}-{id}'.format(date=xact_date, id=xact_id)

def entry_remark(row):
    """Create the value for the entry's remark field.
    """
    this_fullname = row['LIBELLE']
    return '{d})'.format(d=this_fullname)

def get_data(infile):
    """Read dataframe from CSV file and return view.
    """
    data = pd.read_csv(
        infile,
        sep=';',
    )
    data['amount'] = pd.Series(
        [float(s.replace(',', '.'))
         for s
         in data['DEBIT']])
    data['transaction_date_yyyy_mm_dd'] = pd.Series(
        [dp.parse(val, dayfirst=True)
         for val
         in data['DATE ECR']])
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
         in data.LIBELLE])
    data['type'] = pd.Series(
        [val.strip()
         for val
         in data['TYPE ECR']])

    data['piece-comptable'] = data.apply(piece_comptable, axis=1)

    data_view = data[['transaction_date_yyyy_mm_dd', 'transaction_date_qif',
                      'description', 'type',
                      'piece-comptable', 'amount']]
    return data_view.sort_values(by=['transaction_date_yyyy_mm_dd'])

def make_qif(data_view):
    """Build qif file from dataframe.

    The dataframe should have columns as provided by get_data(), above.
    We want a qif so that we can construct splits.

    Cf. https://en.wikipedia.org/wiki/Quicken_Interchange_Format
    """
    qif_data_view = data_view[['transaction_date_qif', 'piece-comptable',
                               'description', 'type', 'amount']]
    qif = '!Account\n'
    qif += 'N401_FFA licences\n'
    qif += '^\n'
    qif += '!Type:Bank\n'
    def qif_entry(row):
        """Create a single QIF file entry.
        """
        this_transaction_date = row['transaction_date_qif']
        this_piece_comptable = row['piece-comptable']
        this_description = row['description']
        this_type = row['type']
        this_amount = -row['amount']

        # D is the date.  It may be required to be in English "dd mmmm
        #   yyyy" format.
        # T is the amount of the transaction.
        # N is the id number (pièce comptable).
        # P is the payee (which quicken thinks of as the comment, not the account)
        # M is a memo
        entry = 'D{date}\nT{total}\nN{pc}\nP{payee}\nM{memo}\n'.format(
            date=this_transaction_date,
            total=this_amount,
            pc=this_piece_comptable, payee=this_description,
            memo=this_type)
        # S is the split category (account number on split line).
        # $ is the amount of the split entry.
        # E is the split memo.
        split_line = 'S{cpty}\n${amt}\nE{memo}\n'
        entry += split_line.format(
            cpty='6075_FFA licences',
            amt=-this_amount,
            memo='')
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
    parser.add_argument('--outfile', type=str, required=False,
                        help='Name of file to write')
    args = parser.parse_args()

    data_view = get_data(args.infile)
    qif = make_qif(data_view)
    if args.outfile:
        with open(args.outfile, 'w') as f_ptr:
            f_ptr.write(qif)
    else:
        print(qif)
    return 0

if __name__ == '__main__':
    retval = main()
    sys.exit(retval)
