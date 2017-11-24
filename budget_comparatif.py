#!/usr/bin/python3

"""Compare two budgets.

"""

import argparse
import datetime
import numpy as np
import pandas as pd
import jinja2
import os
import datetime

def compare_budget_lists(config_1_column, config_2_column):
    """Compute one side of a budget comparison.

    The input is the part of the config that represents a column of
    the budget (expenses or income) and a map from account
    name to balance.

    The output is a list of lists, each of which has either one
    element (a title string) or three elements (a label, a budget_1,
    and a budget_2).

    """
    if len(config_1_column) == 0 or len(config_2_column) == 0:
        print("Empty budgets not allowed.")
        return [["Empty budgets aren't allowed", 0, 0]]
    labels_1 = [x[0] for x in config_1_column]
    label_set_1 = set(labels_1)
    labels_2 = [x[0] for x in config_2_column]
    label_set_2 = set(labels_2)
    label_to_amount_1 = {x[0]: x[1] for x in config_1_column if len(x) == 3}
    label_to_amount_2 = {x[0]: x[1] for x in config_2_column if len(x) == 3}
    # Map config 1 label to config 2 labels that should follow it.
    # This only has entries if there are config 2 labels not in config 1
    # that should follow the item.
    additions = {}
    last_label = labels_1[0]
    for label in labels_2:
        if label not in label_set_1:
            additions[last_label] = label
        else:
            last_label = label  # Label is in both configs 1 and 2.
    out_labels = []
    #for label in labels_1:
    for label_index in range(len(labels_1)):
        label = labels_1[label_index]
        out_labels.append(label)
        while label in additions:
            out_labels.append(additions[label])
            label_index += 1
            if label_index < len(labels_1):
                label = labels_1[label_index]
            else:
                label = None    # Break out of loop.
    return [[label,
             label_to_amount_1.get(label, 0),
             label_to_amount_2.get(label, 0)]
            for label in out_labels]

def compare_budgets(config_filename_1, config_filename_2):
    """Compare two budgets.

    The contents of config_filename* are python code.  It should be a
    list of two lists, each of which contains one or three members:
      - The budget line name.  If this is the only list element,
        then it is a title.
      - Budgeted amount
      - A list of accounts to aggregate.

    We don't actually look at the accounts to aggregate here, only at
    the budgeted values.  On the other hand, we do want to compare
    values between the two budgets.

    If we change the label of a line, this program will consider them
    to be different between the two budgets.

    The returned list contains two lists, the first for expenses, the
    second for income.  In each list, the elements contain a list
    which has one element (a title) or three (a label, a year N
    budget, and a year N+1 budget.

    """
    with open(config_filename_1, 'r') as config_fp:
        config_1 = eval(config_fp.read())
    with open(config_filename_2, 'r') as config_fp:
        config_2 = eval(config_fp.read())
    expenses = compare_budget_lists(config_1[0], config_2[0])
    income = compare_budget_lists(config_1[1], config_2[1])
    return [expenses, income]

def budget_warnings(budgets):
    """Return a string with any warnings about the budgets.

    The input budget is the computed comparison: two lists (one for
    income, one for expenses) of label, N, N+1.

    """
    income_n = sum([x[1] for x in budgets[0]])
    income_n1 = sum([x[2] for x in budgets[0]])
    expenses_n = sum([x[1] for x in budgets[1]])
    expenses_n1 = sum([x[2] for x in budgets[1]])
    if np.round(income_n1, 2) - np.round(expenses_n1, 2) or \
       np.round(income_n, 2) != np.round(expenses_n, 2):
        return "À noter : déséquilibre : $N$={n}, $N+1$={n1}".format(
            n=income_n - expenses_n,
            n1=income_n1 - expenses_n1)
    return ""

def render_as_text_one_column(budget_column):
    """Render one column of a balance sheet as text.
    """
    total_budget_1 = 0
    total_budget_2 = 0
    for line in budget_column:
        if len(line) == 1:
            print('\n', line[0])
        else:
            total_budget_1 += line[1]
            total_budget_2 += line[2]
            print('{label:40s}  {budget:6.2f}  {realised:6.2f}'.format(
                label=line[0], budget=line[1], realised=line[2]))
    print('{nothing:40s}  {budget:6.2f}  {realised:6.2f}'.format(
        nothing='', budget=total_budget_1, realised=total_budget_2))

def render_as_text(budget):
    """Print the balance sheet to stdout as text in a single column.

    The balance sheet is in list of lists format.  The first list is
    expenses, the second income.  Cf comment in
    get_budget_as_list() for more.

    """
    print('==== Dépenses ====')
    render_as_text_one_column(budget[0])
    print('\n==== Recettes ====')
    render_as_text_one_column(budget[1])

def render_as_latex_one_column(budget_column):
    """Return a string that is the latex for one column.

    We're in a tabu environment with three columns.  Return a sequence
    of "label & budget & balance" lines.

    """
    table = ""
    total_budget_1 = 0
    total_budget_2 = 0
    for line in budget_column:
        if 0 == line[1] and 0 == line[2]:
            table += r'\textbf{{ {label} }}&&\\'.format(label=line[0])
            table += '\n'
        else:
            total_budget_1 += line[1]
            total_budget_2 += line[2]
            table += r'{label}&{budget:6.0f}&{realised:6.0f}\\[1mm]'.format(
                label=line[0], budget=line[1], realised=line[2])
            table += '\n'
    table += r'\hline' + '\n'
    table += r'Total & {budget:6.0f} & {realised:6.0f}\\'.format(
        nothing='', budget=total_budget_1, realised=total_budget_2)
    table += '\n'
    return table;

def render_as_latex(budget):
    """Print the balance sheet to budget_<date>.tex as latex.

    The balance sheet is in list of lists format.  The first list is
    expenses, the second income.  Cf comment in
    get_budget_as_list() for more.

    Latex the file to create budget_<date>.pdf.

    """
    with open('budget_comparison.tex', 'r') as fp_template:
        template_text = fp_template.read()
    template = jinja2.Template(template_text)
    out_filename = 'budget-comparison_{date}.tex'.format(
        date=datetime.date.today().strftime('%Y%m%d'))
    with open(out_filename, 'w') as fp_latex:
        fp_latex.write(template.render(
            expenses=render_as_latex_one_column(budget[0]),
            income=render_as_latex_one_column(budget[1]),
            warnings=budget_warnings(budget)))
    os.system('pdflatex ' + out_filename)

def main():
    """Do what we do."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-N', type=str, required=True,
                        help='config file mapping accounts to budget lines, year N')
    parser.add_argument('--config-N1', type=str, required=True,
                        help='config file mapping accounts to budget lines, year N+1')
    parser.add_argument('--render-as', type=str, required=False,
                        default='text',
                        help='One of text or latex')
    args = parser.parse_args()
    budgets = compare_budgets(args.config_N, args.config_N1)
    if 'text' == args.render_as:
        render_as_text(budgets)
    if 'latex' == args.render_as:
        render_as_latex(budgets)

if __name__ == '__main__':
    main()
