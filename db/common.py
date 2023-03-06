
from pathlib import Path

type_names = {
    "Z": "integer",
    "Q": "rational number",
    "R": "real number",
    "C": "complex number",
    "Qp": "p-adic number",
    "Zp": "p-adic integer",
    "ZI": "integer interval",
    "RI": "real interval",
    "CI": "complex interval",
    "RB": "real ball",
    "CB": "complex ball",
    "*R": "hyperreal number",
    "Z[]": "integral polynomial",
    "Q[]": "rational polynomial",
}  

table_id_prefix = "T"

path_numberdb_website = Path.cwd()

path_numberdb_data = path_numberdb_website / '..' / 'numberdb-data'

test_table_ids = [
    'T0', #Zero (integer)
    'T7', #Pi (real number)
    'T35',	#Algebraic numbers of degree 2 (complex numbers)
    'T41', #Hyperreal numbers (hyperreal)
    'T45', #p-adic logarithm of integers (p-adic)
    'T101', #Legendre polynomials (rational polynomials)
    'T107', #Equations satisfied by Igusa invariants of split Jacobians (integral polynomials)
]
