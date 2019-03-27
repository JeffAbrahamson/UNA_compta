#!/usr/bin/env python3

"""Émettre qif de "A NOUVEAU" à importer.

"""

import argparse
import decimal
import piecash

def get_result(book):
    """Compute the result of the fiscal year.

    The input variable, book, is the open gnucash file.
    """
    sum = decimal.Decimal(0.0)
    for account in book.accounts:
        if not account.children:
            balance = account.get_balance()
            if account.name[0] == '6':
                sum -= balance
            if account.name[0] == '7':
                sum += balance
    return sum

def get_balances(gnucash_filename):
    """Get all the income and expense account entries.

    The gnucash_filename is the sqlite3 format gnucash file of the year's
    accounts.

    The dict returned has keys that are the account names.  The value
    is the account balance.  Since this is a for balance transfer to a
    new year's accounts, we look at all accounts except 6 and 7
    accounts and except 129 (the equity account that opposes the A
    NOUVEAU transactions).

    """
    book = piecash.open_book(gnucash_filename,
                             readonly=True,
                             open_if_lock=True)
    account_balances = {}
    solde = decimal.Decimal(0.0)
    for account in book.accounts:
        if not account.children                   \
           and account.name[0] not in ['6', '7']:
            balance = account.get_balance()
            if balance != 0:
                if account.name[0] == '1':
                    balance = -balance # I don't understand why.
                if account.name[:2] == '40':
                    balance = -balance
                account_balances[account.name] = balance
                solde += balance
    # for abk in sorted(account_balances.keys()):
    #     print('{a:<50s}  {b:-10.2f}'.format(a=abk, b=account_balances[abk]))
    # return print("\n", solde, "    ", get_result(gnucash_filename), "\n")
    result = get_result(book)
    if result != solde:
        raise BaseException('Comptes déséquilibrés : résultat = {r} != {s}'.format(
            r=result, s=solde))
    print('Résultat = {r}'.format(r=result))
    return account_balances

def generate_qif(out_filename, balances):
    """Emit QIF to set new balances.

    Balances is a dict { account name -> balance }.
    """
    def qif_entry(row):
        """Create a single QIF file entry.
        """
        this_transaction_date = row['transaction_date_qif']
        this_piece_comptable = row['piece-comptable']
        this_memo = row['memo']
        this_amount = row['amount']
        this_account = row['account']

        # D is the date.  It may be required to be in English "dd mmmm
        #   yyyy" format.
        # T is the amount of the transaction.
        # N is the id number (pièce comptable).
        # P is the payee (which quicken thinks of as the comment, not the account)
        # M is a memo
        #entry = 'D{date}\nT{total}\nN{pc}\nP{payee}\nM{memo}\n'.format(
        entry = 'D{date}\nT{total}\nN{pc}\nP{payee}\n'.format(
            date=this_transaction_date,
            total=this_amount,
            pc=this_piece_comptable,
            payee=this_memo)
        # S is the split category (account number on split line).
        # $ is the amount of the split entry.
        # E is the split memo.
        split_line = 'S{cpty}\n${amt}\n'
        entry += split_line.format(
            cpty=this_account,
            amt=-this_amount)
        return entry
    qif = '!Account\n'
    # We could be clever and consider a non-deficit.
    # We could be clever and let account be an invocation argument.
    qif += "N129_Résultat de l'exercice (déficit)\n"
    qif += '^\n'
    qif += '!Type:Bank\n'
    index = 0
    transactions = []
    for account_name, balance in balances.items():
        # QIF doesn't like to transfer to self.
        # This is not clever: what if there were sub-accounts of 129?
        if account_name[:3] != '129':
            index += 1
            row = {}
            row['transaction_date_qif'] = '2018-10-01'
            row['piece-comptable'] = 'OT-20181001-{n:03d}'.format(n=index)
            row['memo'] = 'A NOUVEAU'
            row['amount'] = balance
            row['account'] = account_name
            transactions.append(qif_entry(row))
    qif += '\n^\n'.join(transactions) + '\n^\n'
    with open(out_filename, 'w') as fp_out:
        fp_out.write(qif)

def main():
    """Do what we do."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--gnucash', type=str, required=True,
                        help='filename containing sqlite3 gnucash file')
    parser.add_argument('--outfile', type=str, required=True,
                        help='filename of output csv')
    args = parser.parse_args()
    balances = get_balances(args.gnucash)
    generate_qif(args.outfile, balances)

if __name__ == '__main__':
    main()
