# PyTeal

[![Build Status](https://travis-ci.com/algorand/pyteal.svg?token=B9eSse5TZikdgKBemvq3&branch=master)](https://travis-ci.com/algorand/pyteal)
[![Documentation Status](https://readthedocs.org/projects/pyteal/badge/?version=latest)](https://pyteal.readthedocs.io/en/latest/?badge=latest)

PyTeal is a Python language binding for Algorand's Smart Contracts (ASC1s). 

Algorand Smart Contracts are implemented using a new language that is stack-based and created by Algorand, 
called [Transaction Execution Approval Language (TEAL)](https://developer.algorand.org/docs/teal). 
This a non-Turing complete language that allows branch forwards but prevents recursive logic 
to maximize safety and performance. 

While TEAL is essentially an assembly based language. PyTeal allows smart contracts developers express there smart contract logic purely using Python. It provides higher level functional programming style abstactions over TEAL and does type checking at construction time.

PyTeal **hasn't been security audited**. Use it at your own risk.

### Install 

pyteal requires python version >= 3.6

* `pip3 install -r requirements.txt`

### Run Demo

In pyteal root directory:

* `jupyter notebook demo/Pyteal\ Demonstration.ipynb`


### Development Setup

Setup venv (one time):
 * `python3 -m venv venv`


Active venv:
 * `. venv/bin/activate.fish` (if your shell is fish)
 * `. venv/bin/activate` (if your shell is bash/zsh)


Pip install pyteal in editable state
 * `pip install -e .`
 
Type checking using mypy
* `mypy pyteal`

Run tests:
* `pytest`
