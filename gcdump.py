#!/usr/bin/env python3

"""Build text file from gnucash.

"""

import argparse
import piecash


def read_gnucash(filename):
    data = []
    book = piecash.open_book(filename,
                             readonly=True,
                             open_if_lock=True)
    accounts = []
    for account in book.accounts:
        if len(account.children) == 0:
            for split in account.splits:
                transaction = split.transaction
                data.append({
                    'date': transaction.enter_date,
                    'num': transaction.num,
                    'memo': split.memo,
                    'descr': transaction.description,
                    'notes': transaction.notes,
                    'quantity': split.quantity,
                    'name': split.account.name,
                })
    return data

def write_text(filename, data):
    with open(filename, 'w') as fp_out:
        for line in data:
            fp_out.write('{date}  {num:<18s}  {note:<110s}  {acct:<25s}  {quantity:>10.2f}\n'.format(
                date=line['date'].strftime('%Y%m%d'),
                num=line['num'],
                note='{memo} / {descr} / {notes}'.format(
                    memo=line['memo'], descr=line['descr'], notes=line['notes']),
                acct=line['name'],
                quantity=line['quantity']))

def main():
    """Do what we do."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--gnucash', type=str, required=True,
                        help='filename containing sqlite3 gnucash file')
    parser.add_argument('-o','--out-file', type=str, required=True,
                        help='filename of output text file')
    args = parser.parse_args()
    data = read_gnucash(args.gnucash)
    write_text(args.out_file, data)

if __name__ == '__main__':
    main()
