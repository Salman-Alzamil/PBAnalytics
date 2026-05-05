import re
import pandas as pd

def normalize_phone(phone_number):  # Strips non-digit characters and adds +966 country code to produce a standard format
    if pd.isna(phone_number):
        return None
    # Remove all non-digit characters
    phone = str(phone_number)
    phone = re.sub(r'\D', '', phone)

    if phone.startswith('966'):
        return "+" + phone
    
    if phone.startswith('0'):
        phone = phone[1:]

    return "+966" + phone


def clean_contacts(contacts_df): # Normalises names, phones, and emails; removes exact duplicates; flags possible duplicates
    df = contacts_df.copy()

    df["first_name"] = df["first_name"].str.strip().str.title()
    df["last_name"] = df["last_name"].str.strip().str.title()
    df["phone"] = df["phone"].apply(normalize_phone)
    df["email"] = df["email"].str.strip().str.lower()

    df = df.drop_duplicates(subset=["phone", "email"])
    df["possible_duplicates"] = df["phone"].duplicated(keep=False)
    

    return df

def clean_calls(df, contacts_df=None): # Parses date/time columns, fills missing contact names via phone lookup, replaces NaN with None
    df = df.copy()

    df["phone_number"] = df["phone_number"].apply(normalize_phone)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["time"] = pd.to_datetime(df["time"], format="%H:%M:%S").dt.time

    if contacts_df is not None:
        phone_to_name = {
            row["phone"]: f"{row['first_name']} {row['last_name']}"
            for _, row in contacts_df.iterrows()
        }

        df["contact_name"] = df.apply(
            lambda row: phone_to_name.get(row["phone_number"], row["contact_name"])
            if pd.isna(row["contact_name"]) or row["contact_name"] == ""
            else row["contact_name"],
            axis=1
        )

    # Globally replace nan values so psycopg doesn't fail on inserts
    df = df.replace({pd.NA: None, float('nan'): None})

    return df