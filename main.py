import datetime
import os
import platform
import pandas as pd
import re
import shutil
import sqlite3
import tzlocal

from tqdm import tqdm


def is_post_high_sierra():
    version = platform.mac_ver()[0].split(".")
    if int(version[0]) < 10:
        return False
    elif int(version[1]) < 13:
        return False
    else:
        return True


def convert_date(date, use_new_date):
    start = datetime.datetime(2001, 1, 1)
    if use_new_date:
        return start + datetime.timedelta(seconds=date / 1000000000)
    else:
        return start + datetime.timedelta(seconds=date)


def get_messages(db, limit=None, after_datetime=None):
    if limit is None:
        query = "SELECT * FROM message"
    else:
        query = f"SELECT * FROM message LIMIT {limit}"

    messages = pd.read_sql_query(query, db)
    messages.rename(columns={"ROWID": "message_id"}, inplace=True)

    messages = messages.loc[
        (messages["is_from_me"] == 0) & (messages["is_empty"] == 0), :
    ]

    messages = messages[["message_id", "handle_id", "date"]]
    use_new_date = is_post_high_sierra()
    messages["date"] = messages["date"].apply(
        lambda x: convert_date(x, use_new_date))
    latest_date = messages["date"].sort_values(ascending=False).values[0]
    if after_datetime:
        messages = messages.loc[messages["date"] > after_datetime, :]

    return messages, latest_date


def examine_filetypes(accepted):
    path = os.path.join(os.path.expanduser(
        "~"), "Library/Messages/Attachments")
    all_files = []
    for root, dirs, files in os.walk(path):
        all_files += files

    missing = set()
    for f in all_files:
        ext = os.path.splitext(f)[1]
        if ext not in accepted:
            missing.add(ext)

    print(f"Missing extentions: {missing}")


def main():
    accepted_file_types = set(
        [
            ".png",
            ".JPEG",
            ".mp4",
            ".jpg",
            ".jpeg",
            ".HEIC",
            ".JPG",
            ".svg",
            ".mov",
            ".tiff",
            ".PNG",
            ".MOV",
            ".heic",
        ]
    )
    examine_filetypes(accepted_file_types)

    files = ["chat.db", "chat.db-shm", "chat.db-wal"]
    home_path = os.path.expanduser("~")
    data_path = "data"
    output_path = "output"

    if not os.path.exists(data_path):
        os.makedirs(data_path)
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    for f in files:
        new_path = os.path.join(data_path, f)
        if os.path.exists(new_path):
            continue
        og_data = os.path.join(home_path, "Library/Messages", f)
        shutil.copyfile(og_data, new_path)

    db_path = os.path.join(data_path, files[0])
    db = sqlite3.connect(db_path)

    messages, latest_date = get_messages(db)

    attachments = pd.read_sql_query("select * from attachment", db)
    attachments.rename(columns={"ROWID": "attachment_id"}, inplace=True)

    maj = pd.read_sql_query("select * from message_attachment_join", db)
    handles = pd.read_sql_query("select * from handle", db)
    handles.rename(columns={"id": "phone_number",
                            "ROWID": "handle_id"}, inplace=True)

    messages = pd.merge(
        messages, handles[["handle_id", "phone_number"]], on="handle_id"
    )

    messages = pd.merge(messages, maj, on="message_id")
    messages = pd.merge(
        messages,
        attachments[["attachment_id", "filename", "total_bytes"]],
        on="attachment_id",
        how="right",
    )

    messages = messages.sort_values(by=["phone_number"], ascending=False)
    messages["phone_number"] = messages["phone_number"].fillna("unknown_phone")

    grouped = messages.groupby(by="phone_number")

    skipped = []
    sizes = []
    for phone, df in tqdm(grouped):
        sub_folder = os.path.join(output_path, phone)
        if not os.path.exists(sub_folder):
            os.makedirs(sub_folder)

        size_mb = df["total_bytes"].sum()*1e-6
        sizes.append(f"{phone}, {size_mb:.0f} MB\n")
        all_paths = list(df["filename"])
        for og_path in all_paths:
            if not og_path:
                continue
            ext = os.path.splitext(og_path)[1]
            if ext not in accepted_file_types:
                continue
            og_path = og_path.replace("~", home_path)
            if not os.path.exists(og_path):
                print(f"Skipped \'{og_path}\' in \'{phone}\'")
                skipped.append(f"{phone},{og_path}\n")
                continue
            file_name = os.path.basename(og_path)
            new_path = os.path.join(sub_folder, file_name)
            shutil.copy2(og_path, new_path)

    if skipped:
        f = open("skipped.csv", "w")
        f.writelines(skipped)
        f.close()

    f = open("sizes.csv", "w")
    f.writelines(sizes)
    f.close()

    print(f"Found: {len(messages)} images")


if __name__ == "__main__":
    main()
