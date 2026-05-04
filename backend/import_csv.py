import argparse
import pandas as pd

from database import SessionLocal
from models import Contact, CallHistory
from utils.cleaner import clean_contacts, clean_calls

def save_to_db(contacts_df, calls_df): # Clears existing data and bulk-inserts cleaned contacts and calls; rolls back on any error
    db = SessionLocal()

    try:
        db.query(Contact).delete()
        db.query(CallHistory).delete()

        contacts = [
            Contact(**row)
            for row in contacts_df.to_dict(orient="records")
        ]

        calls = [
            CallHistory(**row)
            for row in calls_df.to_dict(orient="records")
        ]

        db.add_all(contacts)
        db.add_all(calls)
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Error saving to database: {e}")
        raise

    finally:
        db.close()


def main(): # CLI entry point — parses --contacts and --calls file paths, cleans the data, then saves to DB
    parser = argparse.ArgumentParser(description="Import contacts and call history from CSV files")
    parser.add_argument("--contacts", required=True)
    parser.add_argument("--calls", required=True)
    args = parser.parse_args()

    contacts_df = pd.read_csv(args.contacts)
    calls_df = pd.read_csv(args.calls)

    cleaned_contacts = clean_contacts(contacts_df)
    cleaned_calls = clean_calls(calls_df, cleaned_contacts)

    save_to_db(cleaned_contacts, cleaned_calls)
    print(f"{len(cleaned_contacts)} contacts loaded")
    print(f"{cleaned_contacts['possible_duplicates'].sum()} duplicates flagged")
    print(f"{len(cleaned_calls)} calls imported")

if __name__ == "__main__":
    main()    