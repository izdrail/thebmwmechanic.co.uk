import os
import requests
import sqlite3
import pdfplumber
import markdownify
import io

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
# Directories
directories = {
    'pdf': 'manuals_pdfs',
    'markdown': 'manuals_markdown',
    'html': 'manuals_html'
}

# Create directories if they don't exist
for dir_path in directories.values():
    os.makedirs(dir_path, exist_ok=True)

# Fetch JSON data
def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Failed to fetch data: {e}")
        return None

# Create the SQLite table
def create_table():
    with sqlite3.connect('manuals.db') as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS manuals (
                id INTEGER PRIMARY KEY,
                is_favorite BOOLEAN, manual_link TEXT, manual_title TEXT,
                manual_downloads INTEGER, manual_size INTEGER, axle TEXT,
                youtube_key TEXT, youtube_title TEXT, alias TEXT,
                youtube_preview_url TEXT, youtube_view_count INTEGER, 
                youtube_published_at DATETIME, main_maker_title TEXT, 
                main_model_title TEXT, main_group_title TEXT, created_at DATETIME
            )
        """)

# Download PDF
def download_pdf(link, title):
    try:
        response = requests.get(link)
        response.raise_for_status()
        filename = f"{title.replace(' ', '_')}.pdf"
        path = os.path.join(directories['pdf'], filename)
        with open(path, 'wb') as file:
            file.write(response.content)
        return path
    except requests.RequestException as e:
        print(f"Failed to download PDF: {e}")
        return None

# Process PDF to Markdown
def pdf_to_markdown(path, title):
    try:
        with pdfplumber.open(path) as pdf:
            content = "\n\n".join(page.extract_text_simple() for page in pdf.pages if page.extract_text_simple())
        markdown = markdownify.markdownify(content)
        filepath = os.path.join(directories['markdown'], f"{title.replace(' ', '_')}.md")
        with open(filepath, 'w') as file:
            file.write(markdown)
    except Exception as e:
        print(f"Failed to convert PDF to Markdown: {e}")

# Process PDF to HTML
def pdf_to_html(path, title):
    try:
        with pdfplumber.open(path) as pdf:
            content = "\n".join(f"<div>{page.extract_text()}</div>" for page in pdf.pages if page.extract_text())
        html = f"<html><body>{content}</body></html>"
        filepath = os.path.join(directories['html'], f"{title.replace(' ', '_')}.html")
        with open(filepath, 'w') as file:
            file.write(html)
    except Exception as e:
        print(f"Failed to convert PDF to HTML: {e}")


def convert_pdf_to_txt(path, title):
    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos = set()

    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages,
                                  password=password,
                                  caching=caching,
                                  check_extractable=True):
        interpreter.process_page(page)



    fp.close()
    device.close()
    text = retstr.getvalue()
    retstr.close()
    markdown = markdownify.markdownify(text)
    filepath = os.path.join(directories['markdown'], f"{title.replace(' ', '_')}.md")
    with open(filepath, 'w') as file:
        file.write(markdown)
# Insert data and process PDFs
def insert_data(data):
    with sqlite3.connect('manuals.db') as conn:
        for item in data:
            conn.execute("""
                INSERT INTO manuals (id, is_favorite, manual_link, manual_title, 
                manual_downloads, manual_size, axle, youtube_key, youtube_title, 
                alias, youtube_preview_url, youtube_view_count, youtube_published_at, 
                main_maker_title, main_model_title, main_group_title, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item['id'], item['is_favorite'], item['manual_link'], item['manual_title'],
                item['manual_downloads'], item['manual_size'], item['axle'], item['youtube_key'],
                item['youtube_title'], item['alias'], item['youtube_preview_url'], item['youtube_view_count'],
                item['youtube_published_at'], item['main_maker_title'], item['main_model_title'],
                item['main_group_title'], item['created_at']
            ))
            pdf_path = download_pdf(item['manual_link'], item['manual_title'])
            if pdf_path:
                #pdf_to_markdown(pdf_path, item['manual_title'])
                #pdf_to_html(pdf_path, item['manual_title'])
                convert_pdf_to_txt(pdf_path,item['manual_title'])

# Main execution
if __name__ == "__main__":
    url = 'https://club.autodoc.co.uk/api/v4/instructions/all?order_key=popular&order_type=desc&q=&maker_id=16&type=1&limit=1000&offset=0'
    create_table()
    data = fetch_data(url)
    if data:
        insert_data(data['instructions']['data'])
        print("Data inserted and PDFs processed successfully.")
