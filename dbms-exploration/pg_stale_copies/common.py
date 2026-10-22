"""Connection shared by every script. Nothing to learn here."""
import psycopg


def pg():
    return psycopg.connect("postgresql://lab:lab@localhost:5435/shop", autocommit=True)


def show(label, value):
    print(f"{label:<38} {value}")
