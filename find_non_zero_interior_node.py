#!/usr/bin/env python3

"""Note any accounts that are not leaves but that contain transactions.

"""

import argparse
import piecash

def find_interior(gnucash_filename):
    """Scan all accounts and report non-leaves that have transactions.

    """
    book = piecash.open_book(gnucash_filename,
                             readonly=True,
                             open_if_lock=True)
    for account in book.accounts:
        if account.children and account.splits:
            print(account.name)

def main():
    """Do what we do."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--gnucash', type=str, required=True,
                        help='filename containing sqlite3 gnucash file')
    args = parser.parse_args()
    find_interior(args.gnucash)

if __name__ == '__main__':
    main()
