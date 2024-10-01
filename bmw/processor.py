import os
import requests
import sqlite3
import pdfplumber
import markdownify

# Directory to save the downloaded PDF files
pdf_directory = 'manuals_pdfs'
# Directory to save the processed Markdown files
markdown_directory = 'manuals_markdown'
# Directory to save the processed HTML files
html_directory = 'manuals_html'

# Create the directories if they do not exist
for directory in [pdf_directory, markdown_directory, html_directory]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Function to fetch JSON data from the URL
def fetch_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch data from the URL:", url)
        return None

# Function to create the table if it doesn't exist
def create_table_if_not_exists():
    conn = sqlite3.connect('manuals.db')
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS manuals (
            id INT PRIMARY KEY,
            is_favorite BOOLEAN,
            manual_link TEXT,
            manual_preview TEXT,
            manual_preview_big TEXT,
            manual_preview_big_retina TEXT,
            manual_title TEXT,
            manual_downloads INT,
            manual_size INT,
            axle TEXT,
            youtube_key TEXT,
            youtube_title TEXT,
            alias TEXT,
            youtube_preview_url TEXT,
            youtube_view_count INT,
            youtube_published_at DATETIME,
            main_maker_title TEXT,
            main_model_title TEXT,
            main_group_title TEXT,
            created_at DATETIME,
            single_type INT,
            channel_id INT,
            main_maker_title_cyr TEXT,
            main_model_title_cyr TEXT,
            main_group_title_cyr TEXT,
            is_basic BOOLEAN,
            is_universal BOOLEAN
        )
    """)

    conn.commit()
    conn.close()

# Function to download and save a PDF file
def download_pdf(manual_link, manual_title):
    try:
        response = requests.get(manual_link)
        if response.status_code == 200:
            # Generate a safe filename from the manual title
            filename = f"{manual_title.replace(' ', '_')}.pdf"
            filepath = os.path.join(pdf_directory, filename)
            with open(filepath, 'wb') as pdf_file:
                pdf_file.write(response.content)
            print(f"Downloaded and saved PDF: {filename}")
            return filepath
        else:
            print(f"Failed to download PDF from: {manual_link}")
            return None
    except Exception as e:
        print(f"Error downloading PDF from {manual_link}: {e}")
        return None

# Function to process the PDF and convert to Markdown
def process_pdf_to_markdown(pdf_path, manual_title):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            markdown_content = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    markdown_content += text + "\n\n"

        # Convert text to Markdown format
        markdown_content = markdownify.markdownify(markdown_content)

        # Save the Markdown content to a file
        markdown_filename = f"{manual_title.replace(' ', '_')}.md"
        markdown_filepath = os.path.join(markdown_directory, markdown_filename)
        with open(markdown_filepath, 'w') as markdown_file:
            markdown_file.write(markdown_content)

        print(f"Processed and saved Markdown file: {markdown_filename}")

    except Exception as e:
        print(f"Error processing PDF {pdf_path} to Markdown: {e}")

# Function to process the PDF and convert to HTML
def process_pdf_to_html(pdf_path, manual_title):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            html_content = "<html><body>\n"
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    html_content += "<div>" + text.replace('\n', '<br>') + "</div>\n"
            html_content += "</body></html>"

        # Save the HTML content to a file
        html_filename = f"{manual_title.replace(' ', '_')}.html"
        html_filepath = os.path.join(html_directory, html_filename)
        with open(html_filepath, 'w') as html_file:
            html_file.write(html_content)

        print(f"Processed and saved HTML file: {html_filename}")

    except Exception as e:
        print(f"Error processing PDF {pdf_path} to HTML: {e}")

# Function to insert data into the database
def insert_data(data):
    conn = sqlite3.connect('manuals.db')
    cursor = conn.cursor()

    for item in data:
        cursor.execute("""
            INSERT INTO manuals (id, is_favorite, manual_link, manual_preview, manual_preview_big, manual_preview_big_retina,
            manual_title, manual_downloads, manual_size, axle, youtube_key, youtube_title, alias, youtube_preview_url,
            youtube_view_count, youtube_published_at, main_maker_title, main_model_title, main_group_title, created_at,
            single_type, channel_id, main_maker_title_cyr, main_model_title_cyr, main_group_title_cyr, is_basic, is_universal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item['id'], item['is_favorite'], item['manual_link'], item['manual_preview'], item['manual_preview_big'],
            item['manual_preview_big_retina'], item['manual_title'], item['manual_downloads'], item['manual_size'],
            item['axle'], item['youtube_key'], item['youtube_title'], item['alias'], item['youtube_preview_url'],
            item['youtube_view_count'], item['youtube_published_at'], item['main_maker_title'], item['main_model_title'],
            item['main_group_title'], item['created_at'], item['single_type'], item['channel_id'],
            item['main_maker_title_cyr'], item['main_model_title_cyr'], item['main_group_title_cyr'],
            item['is_basic'], item['is_universal']
        ))

        # Download the PDF file for the manual link
        pdf_path = download_pdf(item['manual_link'], item['manual_title'])

        # Process the PDF to Markdown and HTML if download was successful
        if pdf_path:
            process_pdf_to_markdown(pdf_path, item['manual_title'])
            process_pdf_to_html(pdf_path, item['manual_title'])

    conn.commit()
    conn.close()

# URL to fetch JSON data
url = 'https://club.autodoc.co.uk/api/v4/instructions/all?order_key=popular&order_type=desc&q=&maker_id=16&type=1&limit=1000&offset=0'

# Create table if it doesn't exist
create_table_if_not_exists()

# Fetch JSON data from the URL
data = fetch_data(url)

# Insert data into the database and process PDFs
if data:
    insert_data(data['instructions']['data'])
    print("Data inserted and PDFs processed successfully.")
