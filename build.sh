#!/bin/bash

rm -f budget_20*

book=/home/jeff/.una/2017.csv
./suivie_budgétaire.py --config budget.cfg  --book $book --render-as latex
