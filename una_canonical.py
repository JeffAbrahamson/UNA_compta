#!/usr/bin/python3

"""Convert the EBP or gnucash export to a canonical form.

The input is a text export of the current year's books.
"""

import argparse
import datetime
import numpy as np
import pandas as pd

def get_data_ebp_v19(book_filename):
    """Fetch book data, return as a pandas DataFrame.

    Assume input file is a csv export from EBP v21 (2017).
    """
    with open(book_filename, 'r') as book_fp:
        book = pd.read_csv(
            book_fp, sep=';', header=0,
            names = ["Journal", "Compte", "Date", "Date de valeur",
                     "Date de saisie", "Echéance", "Poste", "Pièce",
                     "N° document", "Libellé", "Débit", "Crédit",
                     "Devise", "Cours", "Débit devise", "Crédit devise",
                     "Contrevaleur débit", "Contrevaleur crédit", "Lettre",
                     "Rapp.", "Règl.", "N° Chèque", "Compte TVA sur Enc.",
                     "Mois de TVA sur Enc.",
                     "Type d'écriture transférée de la Gestion : (A)voir - (F)acture - (R)èglement",
                     "N° facture ou règlement GC", "Date de Relevé",
                     "Date de lettrage", "Provenance", "Ref. BVR / Motif",
                     "N° adhérent", "Date dernière genération", "Partiel",
                     "bSaisieKM", "Numéro d'écriture"],
            usecols=["Date", "Compte", "Débit", "Crédit",
                     "Pièce", "Libellé"],
            parse_dates=['Date'],
            dayfirst=True,
        )
        book['date'] = book.Date
        book['ymd'] = book['Date'].apply(
            lambda x : '{y:04d}{m:02d}{d:02d}'.format(
                y= x.year, m= x.month, d=x.day))
        book['account'] = book.Compte
        # One of credit or debit will be zero.
        book['amount'] = book['Débit'] - book['Crédit']
        book['cd'] = pd.np.where(book['Débit'] > 0, 'D',
                                 pd.np.where(book['Crédit'] > 0, 'C', '-'))
        book['label'] = book['Libellé']
        book['piece_comptable'] = book['Pièce']
        book['document'] = ''
        book['account_name'] = ''
        return book[['date', 'ymd', 'label', 'amount', 'cd', 'account',
                     'piece_comptable', 'document', 'account_name']]

def get_data_ebp_v21(book_filename):
    """Fetch book data, return as a pandas DataFrame.

    Assume input file is a csv export from EBP v19 (2016).
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
            usecols=["Date", "Date au format L47", "account", "Intitulé du compte",
                     "Pièce", "Document", "Libellé",
                     "Montant"],
            parse_dates=['Date'],
            dayfirst=True,
        )
        book['date'] = book.Date
        book['ymd'] = book['Date au format L47']
        book['label'] = book['Libellé']
        book['amount'] = book.Montant
        book['cd'] = pd.np.where(book['Montant'] > 0, 'D', 'C')
        book['label'] = book['Libellé']
        book['piece_comptable'] = book['Pièce']
        book['document'] = book.Document
        book['account_name'] = book['Intitulé du compte']
        return book[['date', 'ymd', 'label', 'amount', 'cd', 'account',
                     'piece_comptable', 'document', 'account_name']]

def get_data(book_filename):
    """Fetch book data, return as a pandas DataFrame.

    Try to divine the input file format.  If we can't, we'll need a
    new case, and so we say so and bail out.  We determine the format
    by looking at the first line, so it's quite dependent on how one
    exports.  I export all fields in the order proposed by the
    accounting program (EBP or gnucash, for the moment).

    """
    ebp_v19 = """\"Journal";"Compte";"Date";"Date de valeur";"Date de saisie";"Echéance";"Poste";"Pièce";"N° document";"Libellé";"Débit";"Crédit";"Devise";"Cours";"Débit devise";"Crédit devise";"Contrevaleur débit";"Contrevaleur crédit";"Lettre";"Rapp.";"Règl.";"N° Chèque";"Compte TVA sur Enc.";"Mois de TVA sur Enc.";"Type d'écriture transférée de la Gestion : (A)voir - (F)acture - (R)èglement";"N° facture ou règlement GC";"Date de Relevé";"Date de lettrage";"Provenance";"Ref. BVR / Motif";"N° adhérent";"Date dernière genération";"Partiel";"bSaisieKM";"Numéro d'écriture\"\n"""
    ebp_v21 = """Code journal;Description du journal;Date;Date au format L47;N° de compte;Intitulé du compte;Pièce;Date de pièce;Document;Libellé;Débit;Crédit;Montant seul (positif ou négatif);Montant (associé au sens);Sens;Statut;Date de lettrage;Lettrage;Partiel;Date de l'échéance;Moyen de paiement;Notes;N° de ligne pour les documents associés;Documents associés;Plan analytique;Poste analytique\n"""

    with open(book_filename, 'r', encoding='utf-8-sig') as book_fp:
        first_line = book_fp.readline()
        if first_line == ebp_v19:
            book = get_data_ebp_v19(book_filename)
        elif first_line == ebp_v21:
            book = get_data_ebp_v21(book_filename)
        else:
            print('Unrecognized book format.\n')
            raise ImportError(book_filename)
    return book

def main():
    """Do what we do."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--book', type=str, required=True,
                        help='filename containing text export of the general ledger')
    parser.add_argument('--out', type=str, required=True,
                        help='filename to which to write canonical form book')
    args = parser.parse_args()
    book = get_data(args.book);
    with open(args.out, 'w') as fp_out:
        book.to_csv(fp_out, index=False)

if __name__ == '__main__':
    main()
