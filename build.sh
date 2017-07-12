#!/bin/bash

rm bilan_20*

book=/home/jeff/work/UNA/comite-directeur/trésorier/ebp-compta-exports/export.txt
./bilan.py --config bilan.cfg  --book $book --render-as latex
