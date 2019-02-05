#!/usr/bin/python3

"""Sum helloasso CSV file for certain accounts.

Used for computing balance transfers to next fiscal year.t
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

def find_account(config, descr, sub_descr):
    if descr not in config:
        return 'ignore'
    descr_account = config[descr]
    if 'subdescr' in descr_account and sub_descr in descr_account['subdescr']:
        return descr_account['subdescr'][sub_descr]
    if 'default' in descr_account:
        return descr_account['default']
    return 'ignore'

def make_find_account(config):
    def this_find_account(row):
        ret = find_account(config, row['description'], row['sub_description']),
        return ret
    return this_find_account

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

    data_valid = data[data['Statut'] == 'Validé']
    data_view = data_valid[['description', 'sub_description',
                            'amount', 'account']]
    return data_view.groupby(['account']).sum()

def main():
    """Do what we do.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--infile', type=str, required=True,
                        help='Name of file to read')
    parser.add_argument('--config', type=str, required=True,
                        help='config file mapping descriptions to accounts')
    args = parser.parse_args()

    config = get_account_mappings(args.config)
    data_view = get_data(args.infile, config)
    print(data_view)
    return 0

if __name__ == '__main__':
    retval = main()
    sys.exit(retval)
