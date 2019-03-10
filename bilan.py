#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Compute a (French-style) balance sheet (bilan) and P&L report
(compte de résultat).  The intent is to conform reasonably closely to
the CERFA.

The input is a sqlite3-format gnucash file.

"""

import argparse
import datetime
import jinja2
import os
import piecash
import decimal

def get_account_balances(book_filename):
    """Read and interpret data, compute account balances as a dict.

    The book_filename is the sqlite3 format gnucash file of the year's
    accounts.

    The dict returned has keys that are the account names.  The value
    is the account balance.

    """
    book = piecash.open_book(book_filename,
                             readonly=True,
                             open_if_lock=True)
    account_sums = {}
    for account in book.accounts:
        if not account.children:
            balance = account.get_balance()
            if balance != 0:
                account_sums[account.name] = balance
    return account_sums

def add_entry_assets(sheet, column, key, account_name, balance):
    """Add an entry to the assets side of the balance sheet.

    The assets part of the sheet is a dictionary indexed first by key
    (the line group), then by column ('brute' or 'amort'), which leads
    to a dict with the following keys:

        entries: an array of tuples of (account_name, balance)
        balance: the sum of the balances in entries

    """
    if key not in sheet:
        # The balance is -pi, because zero would be a bit too
        # easy to miss if unset.
        sheet[key] = {'brute': {'entries': [], 'balance': -3.1415},
                      'amort': {'entries': [], 'balance': -3.1415}}
    sheet[key][column]['entries'].append((account_name, balance))

def add_to_assets(sheet, prefix, column, key, account_name, balance):
    """
    If account_name starts with prefix, add to the sheet.
    """
    if account_name[:len(str(prefix))] == str(prefix):
        add_entry_assets(sheet, column, key, account_name, balance)

def add_entry(sheet, key, account_name, balance):
    """Add an entry to the liabilities side of the balance sheet or to the
    P&L report.

    The non-assets part of the sheet is a dictionary indexed by key
    (the line group), which leads to a dict with the following keys:

        entries: an array of tuples of (account_name, balance)
        balance: the sum of the balances in entries

    """
    if key not in sheet:
        sheet[key] = {'entries': [], 'balance': 0}
    sheet[key]['entries'].append((account_name, balance))

def add_to_sheet(sheet, prefix, key, account_name, balance):
    """
    If account_name starts with prefix, add to the sheet.
    """
    if account_name[:len(str(prefix))] == str(prefix):
        add_entry(sheet, key, account_name, balance)

def sum_entries(entries_group):
    """Compute the balance item for one set of entries.

    The input entries_group should be a dict with fields balance and
    entries (a list of (account_name, balance) tuples).

    """
    balance = decimal.Decimal(0.0)
    for entry in entries_group['entries']:
        balance += entry[1]
    entries_group['balance'] = balance

def sum_all_entries(sheet):
    """Sum the entries in a balance sheet and P&L.

    """
    for value in sheet.values():
        if 'entries' in value:
            # The most common case, so put first.
            sum_entries(value)
        else:
            if 'brute' in value:
                sum_entries(value['brute'])
            if 'amort' in value:
                sum_entries(value['amort'])

def build_assets(sheet, account_name, balance):
    """Build the assets portion of the balance sheet.

    """
    ## Actif.
    # Immobilisations incorporelles.
    add_to_assets(sheet, 206, 'brute', 'immo_incorp__fonds_commercial', account_name, balance)
    add_to_assets(sheet, 207, 'brute', 'immo_incorp__fonds_commercial', account_name, balance)
    add_to_assets(sheet, 2906, 'amort', 'immo_incorp__fonds_commercial', account_name, balance)
    add_to_assets(sheet, 2909, 'amort', 'immo_incorp__fonds_commercial', account_name, balance)
    add_to_assets(sheet, 201, 'brute', 'immo_incorp__autres', account_name, balance)
    add_to_assets(sheet, 203, 'brute', 'immo_incorp__autres', account_name, balance)
    add_to_assets(sheet, 205, 'brute', 'immo_incorp__autres', account_name, balance)
    add_to_assets(sheet, 208, 'brute', 'immo_incorp__autres', account_name, balance)
    add_to_assets(sheet, 280, 'amort', 'immo_incorp__autres', account_name, balance)
    add_to_assets(sheet, 2905, 'amort', 'immo_incorp__autres', account_name, balance)
    add_to_assets(sheet, 2908, 'amort', 'immo_incorp__autres', account_name, balance)
    # Immobilisations corporelles.
    add_to_assets(sheet, 21, 'brute', 'immo_corp', account_name, balance)
    add_to_assets(sheet, 22, 'brute', 'immo_corp', account_name, balance)
    add_to_assets(sheet, 23, 'brute', 'immo_corp', account_name, balance)
    add_to_assets(sheet, 281, 'amort', 'immo_corp', account_name, balance)
    add_to_assets(sheet, 291, 'amort', 'immo_corp', account_name, balance)
    # Immobilisations financières.
    add_to_assets(sheet, 26, 'brute', 'immo_fin', account_name, balance)
    add_to_assets(sheet, 27, 'brute', 'immo_fin', account_name, balance)
    add_to_assets(sheet, 296, 'amort', 'immo_fin', account_name, balance)
    add_to_assets(sheet, 297, 'amort', 'immo_fin', account_name, balance)
    # Stocks (atures que marchandises).
    for prefix in range(31, 36):
        add_to_assets(sheet, prefix, 'brute', 'stock_pas_marchandises', account_name, balance)
    for prefix in range(391, 396):
        add_to_assets(sheet, prefix, 'amort', 'stock_pas_marchandises', account_name, balance)
    # Stocks de marchandises.
    add_to_assets(sheet, 37, 'brute', 'stock_marchandises', account_name, balance)
    add_to_assets(sheet, 397, 'amort', 'stock_marchandises', account_name, balance)
    # Avances et acomptes versés.
    add_to_assets(sheet, 4091, 'brute', 'avances', account_name, balance)
    # Créances : clients et comptes rattachés.
    add_to_assets(sheet, 491, 'amort', 'creances_clients', account_name, balance)
    # Valeurs mobilières de placement.
    add_to_assets(sheet, 50, 'brute', 'mobil_placement', account_name, balance)
    add_to_assets(sheet, 590, 'amort', 'mobil_placement', account_name, balance)
    # Disponibilités (autres que caisse).
    add_to_assets(sheet, 54, 'brute', 'disponibilite_non_caisse', account_name, balance)
    add_to_assets(sheet, 58, 'brute', 'disponibilite_non_caisse', account_name, balance)
    # Caisse.
    add_to_assets(sheet, 53, 'brute', 'caisse', account_name, balance)
    # Charges constatées d'avance.
    add_to_assets(sheet, 486, 'brute', 'charges_constates_avance', account_name, balance)
    # Créances : autres créances.
    add_to_assets(sheet, 496, 'amort', 'creances_autres', account_name, balance)

    if balance > 0:
        # Créances : clients et comptes rattachés.
        add_to_assets(sheet, 41, 'brute', 'creances_clients', account_name, balance)
        # Créances : autres créances.
        if account_name[:4] != '4091':
            add_to_assets(sheet, 40, 'brute', 'creances_autres', account_name, balance)
        add_to_assets(sheet, 42, 'brute', 'creances_autres', account_name, balance)
        add_to_assets(sheet, 43, 'brute', 'creances_autres', account_name, balance)
        add_to_assets(sheet, 44, 'brute', 'creances_autres', account_name, balance)
        add_to_assets(sheet, 45, 'brute', 'creances_autres', account_name, balance)
        add_to_assets(sheet, 46, 'brute', 'creances_autres', account_name, balance)
        # Disponibilités (autres que caisse).
        add_to_assets(sheet, 51, 'brute', 'disponibilite_non_caisse', account_name, balance)

def assets_latex_section(name, sheet, key):
    """Create latex for one group of entries in the assets section.
    """
    if key not in sheet:
        return ""
    entries_group = sheet[key]
    group_latex = '{bfb}{title}{bfe} & {bfb}{brut}{bfe} & {bfb}{amort}{bfe} & {bfb}{net}{bfe} & {bfb}{n1}{bfe}\\\\ \n'.format(
        bfb='\\textbf{',
        bfe='}',
        title=name,
        brut=entries_group['brute']['balance'],
        amort=-entries_group['amort']['balance'],
        net=(entries_group['brute']['balance'] + entries_group['amort']['balance']),
        n1=0)
    table = {}
    for column in entries_group.keys():
        # brute ou amort.
        for entry in entries_group[column]['entries']:
            account_name = entry[0]
            if account_name not in table:
                table[account_name] = {}
            table[account_name][column] = entry[1]
    for account_name in sorted(table.keys()):
        brute = table[account_name].get('brute', 0)
        amort = -table[account_name].get('amort', 0)
        net = brute - amort
        n1 = 0
        group_latex += '{title} & {brute} & {amort} & {net} & {n1} \\\\ \n'.format(
            title=account_name.replace('_', ' '),
            brute=brute, amort=amort, net=net, n1=n1)
    group_latex += '&&&&\\\\ \n'
    return group_latex

def build_assets_latex(sheet):
    """Create the content latex for the assets section.
    """
    assets = ""
    assets += assets_latex_section("Immobilisations Incorporelles : fond commercial",
                                   sheet, 'immo_incorp__fonds_commercial')
    assets += assets_latex_section("Immobilisations Incorporelles : autres",
                                   sheet, 'immo_incorp__autres')
    assets += assets_latex_section("Immobilisations Incorporelles",
                                   sheet, 'immo_incorp__fonds_commercial')
    assets += assets_latex_section("Immobilisations Corporelles",
                                   sheet, 'immo_corp')
    assets += assets_latex_section("Immobilisations financières",
                                   sheet, 'immo_fin')
    assets += assets_latex_section("Stocks (autre que marchandises)",
                                   sheet, 'stock_pas_marchandises')
    assets += assets_latex_section("Stocks de marchandises",
                                   sheet, 'stock_marchandises')
    assets += assets_latex_section("Avances et acomptes versés",
                                   sheet, 'avances')
    assets += assets_latex_section("Créances : clients et comptes rattachés",
                                   sheet, 'creances_clients')
    assets += assets_latex_section("Créances : autres créances",
                                   sheet, 'creances_clients')
    assets += assets_latex_section("Valeurs mobilières de placement",
                                   sheet, 'mobil_placement')
    assets += assets_latex_section("Disponibilités (autres que caisse)",
                                   sheet, 'disponibilite_non_caisse')
    assets += assets_latex_section("Caisse", sheet, 'caisse')
    assets += assets_latex_section("Charges constatées d'avance",
                                   sheet, 'charges_constates_avance')
    return assets

def simple_latex_section(name, sheet, key):
    """Create latex for one group of entries in the liabilities or PL section.
    """
    print(key, '    ', name)
    if key not in sheet:
        print('================================================')
        return ""
    entries_group = sheet[key]
    group_latex = '{bfb}{title}{bfe} & {bfb}{n}{bfe} & {bfb}{n1}{bfe}\\\\ \n'.format(
        bfb='\\textbf{',
        bfe='}',
        title=name,
        n=entries_group['balance'],
        n1=0)
    table = {}
    for entry in sorted(entries_group['entries']):
        n = entry[1]
        n1 = 0
        group_latex += '{title} & {n} & {n1} \\\\ \n'.format(
            title=entry[0].replace('_', ' '),
            n=n, n1=n1)
    group_latex += '&&\\\\ \n'
    return group_latex


def build_liabilities(sheet, account_name, balance):
    """Build the assets portion of the balance sheet.

    """
    ## Passif.
    # Capital.
    add_to_sheet(sheet, 101, 'capital', account_name, balance)
    add_to_sheet(sheet, 108, 'capital', account_name, balance)
    # Écarts de réévaluation.
    add_to_sheet(sheet, 105, 'ecarts_de_reevaluation', account_name, balance)
    # Réserves légales.
    add_to_sheet(sheet, 1061, 'reserves_legale', account_name, balance)
    # Réserves réglementées.
    add_to_sheet(sheet, 1064, 'reserves_reglementaire', account_name, balance)
    # Réserves, autres.
    add_to_sheet(sheet, 1063, 'reserves_autre', account_name, balance)
    add_to_sheet(sheet, 1068, 'reserves_autre', account_name, balance)
    # Report à nouveau.
    add_to_sheet(sheet, 110, 'report_a_nouveau', account_name, balance)
    add_to_sheet(sheet, 119, 'report_a_nouveau', account_name, balance)
    # Provisions réglementées.
    add_to_sheet(sheet, 14, 'provisions_relgementees', account_name, balance)
    # Provisions.
    add_to_sheet(sheet, 15, 'provisions', account_name, balance)
    # Emprunts et dettes assimilées.
    add_to_sheet(sheet, 16, 'dettes_emprunts', account_name, balance)
    # Produits constatés d'avance.
    add_to_sheet(sheet, 487, 'produits_constates_avance', account_name, balance)

    if balance < 0:
        # Disponibilités (autres que caisse).
        add_to_sheet(sheet, 51, 'dettes_emprunts', account_name, balance)
        # Avances et acomptes reçus.
        add_to_sheet(sheet, 4191, 'dettes_avances', account_name, balance)
        # Fournisseurs et comptes rattachés.
        add_to_sheet(sheet, 40, 'dettes_fournisseurs', account_name, balance)
        # Dettes, autres.
        if account_name[:4] != '4191':
            add_to_sheet(sheet, 41, 'dettes_autres', account_name, balance)
        add_to_sheet(sheet, 42, 'dettes_autres', account_name, balance)
        add_to_sheet(sheet, 43, 'dettes_autres', account_name, balance)
        add_to_sheet(sheet, 44, 'dettes_autres', account_name, balance)
        add_to_sheet(sheet, 45, 'dettes_autres', account_name, balance)
        add_to_sheet(sheet, 46, 'dettes_autres', account_name, balance)

def build_liabilities_latex(sheet):
    """Create the content latex for the liabilities section.
    """
    liabilities = ""
    liabilities += simple_latex_section("Capital", sheet, 'capital')
    liabilities += simple_latex_section("Écart de réévaluation",
                                        sheet, 'ecarts_de_reevaluation')
    liabilities += simple_latex_section("Réserve légale",
                                        sheet, 'reserves_legale')
    liabilities += simple_latex_section("Réserves réglementées",
                                        sheet, 'reserves_reglementaire')
    liabilities += simple_latex_section("Réserves : autres",
                                        sheet, 'reserves_autre')
    liabilities += simple_latex_section("Report à nouveau",
                                        sheet,  'report_a_nouveau')
    liabilities += simple_latex_section("Résultat de l'exercice",
                                        sheet, 0) # ################
    liabilities += simple_latex_section("Provisions réglementées",
                                        sheet, 'provisions_relgementees')
    liabilities += simple_latex_section("Provisions", sheet, 'provisions')
    liabilities += simple_latex_section("Emprunts et dettes assimilées",
                                        sheet, 'dettes_emprunts')
    liabilities += simple_latex_section("Avances et acomptes reçus",
                                        sheet, 'dettes_avances')
    liabilities += simple_latex_section("Fournisseurs et comptes rattachés",
                                        sheet, 'dettes_fournisseurs')
    liabilities += simple_latex_section("Dettes : autres", sheet, 'dettes_autres')
    liabilities += simple_latex_section("Produits constatés d'avance", 
                                        sheet, 'produits_constates_avance')
    return liabilities

def build_p_l(sheet, account_name, balance):
    """Build the assets portion of the balance sheet.

    """
    ## Compte de résultat.
    # Achats de marchandises
    add_to_sheet(sheet, 607, 'achat_marchandises', account_name, balance)
    add_to_sheet(sheet, 6097, 'achat_marchandises', account_name, balance)
    # Variation de stocks (marchandises)
    add_to_sheet(sheet, 6037, 'variation_stocks', account_name, balance)
    # Achats d'approvisionnements.
    add_to_sheet(sheet, 601, 'achats_approvisionnements', account_name, balance)
    add_to_sheet(sheet, 602, 'achats_approvisionnements', account_name, balance)
    add_to_sheet(sheet, 604, 'achats_approvisionnements', account_name, balance)
    add_to_sheet(sheet, 605, 'achats_approvisionnements', account_name, balance)
    add_to_sheet(sheet, 606, 'achats_approvisionnements', account_name, balance)
    # Variation de stocks.
    add_to_sheet(sheet, 6031, 'variation_stocks', account_name, balance)
    add_to_sheet(sheet, 6032, 'variation_stocks', account_name, balance)
    # Autres charges externes.
    add_to_sheet(sheet, 61, 'autres_charges_externes', account_name, balance)
    add_to_sheet(sheet, 62, 'autres_charges_externes', account_name, balance)
    # Impôts, taxes, et assimilés.
    add_to_sheet(sheet, 63, 'impots', account_name, balance)
    # Rémunération personnel.
    add_to_sheet(sheet, 641, 'remuneration', account_name, balance)
    add_to_sheet(sheet, 644, 'remuneration', account_name, balance)
    # Charges sociales.
    add_to_sheet(sheet, 645, 'charges_sociales', account_name, balance)
    add_to_sheet(sheet, 646, 'charges_sociales', account_name, balance)
    # Dotation aux amortissements.
    add_to_sheet(sheet, 6811, 'dotations_amort', account_name, balance)
    # Dotation aux provisions (et dépréciations).
    add_to_sheet(sheet, 6815, 'dotations_provisions', account_name, balance)
    add_to_sheet(sheet, 6817, 'dotations_provisions', account_name, balance)
    # Autres charges (d'exploitation).
    add_to_sheet(sheet, 65, 'autres_charges', account_name, balance)
    # Charges financières.
    add_to_sheet(sheet, 66, 'charges_financieres', account_name, balance)
    add_to_sheet(sheet, 686, 'charges_financieres', account_name, balance)
    # Charges exceptionnelles.
    add_to_sheet(sheet, 67, 'charges_exception', account_name, balance)
    add_to_sheet(sheet, 687, 'charges_exception', account_name, balance)
    # Impôt sur les bénéfices.
    add_to_sheet(sheet, 695, 'impots_benefices', account_name, balance)
    add_to_sheet(sheet, 697, 'impots_benefices', account_name, balance)
    # Ventes de marchandises.
    add_to_sheet(sheet, 707, 'ventes_marchandises', account_name, balance)
    add_to_sheet(sheet, 7097, 'ventes_marchandises', account_name, balance)
    # Production vendue.
    for prefix in [701, 706, 708, 7091, 7096, 7098]:
        add_to_sheet(sheet, prefix, 'production_vendue', account_name, balance)
    # Production stockée.
    add_to_sheet(sheet, 713, 'production_stockee', account_name, balance)
    # Production immobilisée.
    add_to_sheet(sheet, 72, 'production_immobilisee', account_name, balance)
    # Subventions d'exploitation.
    add_to_sheet(sheet, 74, 'subvention_exploit', account_name, balance)
    # Autres produits.
    for prefix in [75, 781, 791]:
        add_to_sheet(sheet, prefix, 'autre_produits', account_name, balance)
    # Produits financiers.
    for prefix in [76, 786, 796]:
        add_to_sheet(sheet, prefix, 'produits_financiers', account_name, balance)
    # Produits excetptionnels.
    for prefix in [77, 787, 797]:
        add_to_sheet(sheet, prefix, 'produits_except', account_name, balance)

def build_p_l_latex(sheet):
    """Create the content latex for the P&L section.
    """
    return 'a&b&c\\\\ \n'

def construct_reports(accounts, template_filename, out_filename):
    """Construct the lists for the reports, build the reports.

    The accounts argument is a dict, as provided by
    get_account_balances(), that maps account name to balance of the
    account.

    """
    sheet = {}
    for account_name, balance in accounts.items():
        build_assets(sheet, account_name, balance)
        build_liabilities(sheet, account_name, balance)
        build_p_l(sheet, account_name, balance)
    sum_all_entries(sheet)
    # It's a bit nitty to do the arithmetic in jinja2.  So we
    # construct the body latex here.
    assets_latex = build_assets_latex(sheet)
    liabilities_latex = build_liabilities_latex(sheet)
    pl_latex = build_p_l_latex(sheet)
    with open(template_filename, 'r') as fp_template:
        template_text = fp_template.read()
    template = jinja2.Template(template_text)
    now = datetime.datetime.now()
    with open(out_filename, 'w') as fp_latex:
        fp_latex.write(template.render(
            assets=assets_latex,
            liabilities=liabilities_latex,
            pl_latex=pl_latex,
            quand=now.strftime('%F à %T')))
    os.system('pdflatex ' + out_filename)

def main():
    """Do what we do."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--gnucash', type=str, required=True,
                        help='filename containing sqlite3 gnucash file')
    parser.add_argument('--template', type=str, required=True,
                        help='Latex template filename (with .tex)')
    parser.add_argument('--outfile', type=str, required=True,
                        help='Latex template filename (with .tex)')
    args = parser.parse_args()
    account_sums = get_account_balances(args.gnucash)
    construct_reports(account_sums, args.template, args.outfile)

if __name__ == '__main__':
    main()
