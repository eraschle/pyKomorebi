import sys
from pprint import pp


from pyKomorebi import __main__ as app


if __name__ == '__main__':
    pp(f"Started with: {sys.argv}")
    # first = sys.argv.pop(0)
    # pp(f"Remove {first} stil exist {sys.argv}")
    app.execute()
