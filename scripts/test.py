import os
import requests
import sqlite3
import pdfplumber
import markdownify

# Directories
directories = {
    'pdf': 'manuals_pdfs',
    'markdown': 'manuals_markdown',
    'html': 'manuals_html'
}

# Create directories if they don't exist
for dir_path in directories.values():
    os.makedirs(dir_path, exist_ok=True)
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
# Fetch JSON data
def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Failed to fetch data: {e}")
        return None
def insert_data(data):
    for item in data:
        pdf_path = download_pdf(item['manual_link'], item['manual_title'])
        md_text = pymupdf4llm.to_markdown(pdf_path)
        print(md_text)
        exit(1)

# Main execution
if __name__ == "__main__":
    url = 'https://club.autodoc.co.uk/api/v4/instructions/all?order_key=popular&order_type=desc&q=&maker_id=16&type=1&limit=1000&offset=0'
    data = fetch_data(url)
    if data:
        insert_data(data['instructions']['data'])
        print("Data inserted and PDFs processed successfully.")
