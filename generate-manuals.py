import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Pipeline Step 1: Database Query Pipeline
def fetch_manuals_from_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, manual_title, main_maker_title, main_model_title,
               main_group_title, created_at, txt_path
        FROM manuals
    """)

    manuals = cursor.fetchall()
    conn.close()
    return manuals

# Pipeline Step 2: Manual Fetching Pipeline
def fetch_manual_content(txt_folder, txt_path):
    manual_file = Path(txt_folder) / txt_path
    if manual_file.exists():
        with open(manual_file, 'r', encoding='utf-8') as file:
            return file.read()
    else:
        print(f"Warning: {manual_file} not found.")
        return None

# Pipeline Step 3: Markdown Generation Pipeline
def generate_markdown(manual_data, manual_content, output_folder):
    manual_id, title, maker, model, group, created_at, txt_path = manual_data

    # Set up markdown structure
    markdown_content = f"""---
title: {title}
description: {maker}, {model}, {group}
author: Stefan
pubDate: {created_at}
categories:
  - {maker}
  - {model}
---
{manual_content}
"""

    # Create output folder if it doesn't exist
    output_folder_path = Path(output_folder)
    output_folder_path.mkdir(parents=True, exist_ok=True)

    # Save markdown file
    output_file = output_folder_path / f"{manual_id}.md"
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(markdown_content)

    print(f"Markdown generated: {output_file}")

# Main Pipeline Execution
def main(db_path, txt_folder, output_folder):
    manuals = fetch_manuals_from_db(db_path)

    for manual in manuals:
        manual_content = fetch_manual_content(txt_folder, manual[6])

        if manual_content:
            generate_markdown(manual, manual_content, output_folder)

# Configure paths
db_path = "app/manuals.db"
txt_folder = "app/manuals_txt/"
output_folder = "app/manuals_md/"

if __name__ == "__main__":
    main(db_path, txt_folder, output_folder)
