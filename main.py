import os
import requests
import sqlite3
import logging
from markdownify import markdownify as md

from spire.pdf import PdfDocument, PdfTextExtractor, PdfTextExtractOptions, FileFormat
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI
from pathlib import Path
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG = {
    'pdf_directory': 'manuals_pdfs',
    'html_directory': 'manuals_html',
    'text_directory': 'app/manuals_text',
    'markdown_directory': 'manuals_md',
    'db_name': 'manuals.db',
    'api_url': 'https://club.autodoc.co.uk/api/v4/instructions/all?order_key=popular&order_type=desc&q=&maker_id=16&type=1&limit=1000&offset=0',
    'max_workers': 5
}
# Create necessary directories
for directory in [CONFIG['pdf_directory'], CONFIG['html_directory'], CONFIG['text_directory'], CONFIG['markdown_directory']]:
    os.makedirs(directory, exist_ok=True)


class ManualProcessor:
    """Processes manuals from a database into Markdown files."""
    def __init__(self, db_path, txt_folder, output_folder):
        self.db_path = db_path
        self.txt_folder = Path(txt_folder)
        self.output_folder = Path(output_folder)

    def fetch_manuals_from_db(self):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("""
                SELECT id, manual_title, main_maker_title, main_model_title,
                       main_group_title, created_at, alias
                FROM manuals
            """).fetchall()

    def fetch_manual_content(self, txt_path: Optional[str]) -> Optional[str]:
        """
        Fetches the content of a manual text file, handling missing paths.

        Args:
            txt_path: (Optional) Path to the manual text file.

        Returns:
            The content of the file as a string, or None if the file is not found or `txt_path` is None.
        """
        if not txt_path:
            return None

        manual_file = self.txt_folder / txt_path
        if manual_file.exists():
            with open(manual_file, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            logging.warning(f"Warning: {manual_file} not found.")
            return None

    def generate_markdown(self, manual_data, manual_content):
        manual_id, title, maker, model, group, created_at, _ = manual_data
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
        self.output_folder.mkdir(parents=True, exist_ok=True)
        output_file = self.output_folder / f"{manual_id}.md"
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(markdown_content)
        logging.info(f"Markdown generated: {output_file}")

    def process_all_manuals(self):
        manuals = self.fetch_manuals_from_db()
        for manual in manuals:
            content = self.fetch_manual_content(f"{manual[6]}.txt")
            if content:
                self.generate_markdown(manual, content)


class Pipeline:
    def __init__(self, config):
        self.config = config
        self.data = None
        self.replace_phrases = ["Evaluation Warning : The document was created with Spire.PDF for Python.",
                                "CLUB.AUTODOC.CO.UK", "SIMILAR VIDEO TUTORIAL", "AUTODOC", "Buy tools",
                                "VIEW MORE TUTORIALS", "WELL DONE!", "To protect the environment from pollution..."]

    def fetch_data(self):
        try:
            response = requests.get(self.config['api_url'])
            response.raise_for_status()
            self.data = response.json()
            logging.info("Fetched data successfully.")
        except requests.RequestException as e:
            logging.error(f"Failed to fetch data: {e}")
            raise

    def create_database(self):
        with sqlite3.connect(self.config['db_name']) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS manuals (
                    id INT PRIMARY KEY,
                    manual_title TEXT,
                    txt_path TEXT
                )
            """)
            logging.info("Database table created successfully.")

    def process_manuals(self):
        if not self.data or not self.data.get('instructions', {}).get('data', []):
            logging.error("No data to process.")
            return

        instructions = self.data['instructions']['data']
        with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
            futures = [executor.submit(self.process_single_manual, item) for item in instructions]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error in processing manual: {e}")

    def process_single_manual(self, item):
        pdf_path = self.download_pdf(item['manual_link'], item['manual_title'])
        if pdf_path:
            page_count = self.count_pdf_pages(pdf_path)
            if page_count > 2:
                self.modify_pdf(pdf_path)
                text = self.extract_text_from_pdf(pdf_path, pdf_path)
                cleaned_text = self.clean_text(text)
                self.save_text(cleaned_text, item['manual_title'])

    def download_pdf(self, link, title):
        try:
            response = requests.get(link)
            response.raise_for_status()
            filepath = os.path.join(self.config['pdf_directory'], f"{title.replace(' ', '_')}.pdf")
            with open(filepath, 'wb') as pdf_file:
                pdf_file.write(response.content)
            logging.info(f"Downloaded PDF: {filepath}")
            return filepath
        except requests.RequestException as e:
            logging.error(f"Failed to download PDF: {e}")
            return None

    def count_pdf_pages(self, pdf_path):
        try:
            doc = PdfDocument()
            doc.LoadFromFile(pdf_path)
            return doc.Pages.Count
        except Exception as e:
            logging.error(f"Error counting pages: {e}")
            return 0

    def modify_pdf(self, pdf_path):
        try:
            pdf = PdfDocument()
            pdf.LoadFromFile(pdf_path)
            pdf.Pages.RemoveAt(0)
            pdf.Pages.RemoveAt(pdf.Pages.Count - 1)
            pdf.SaveToFile(pdf_path)
            logging.info(f"Modified PDF: {pdf_path}")
        except Exception as e:
            logging.error(f"Error modifying PDF: {e}")

    def extract_text_from_pdf(self, pdf_path: str, output_file: str) -> str:
        """
        Extract text from a PDF and return it. Converts the PDF to Markdown format.

        Args:
            pdf_path: Path to the input PDF file.
            output_file: Path to save the output Markdown file.

        Returns:
            The extracted text as a string.
        """
        try:
            # Load the PDF document
            doc = PdfDocument()
            doc.LoadFromFile(pdf_path)

            # Save the document as a Markdown file
            doc.SaveToFile(output_file, FileFormat.HTML)

            # Reading the content from the saved Markdown file
            with open(output_file, 'r', encoding='utf-8') as file:
                extracted_text = file.read()
                #@todo add here a markdown html to md with keeping the images rendered
            logging.info(f"Extracted text from PDF and saved as Markdown: {output_file}")
            return extracted_text
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {e}")
            raise

    def clean_text(self, text):
        for phrase in self.replace_phrases:
            text = text.replace(phrase, "")
        return text

    def save_text(self, text, title):
        filepath = os.path.join(self.config['text_directory'], f"{title.replace(' ', '_')}.txt")
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(text)
        logging.info(f"Text saved: {filepath}")


app = FastAPI()

@app.get("/extract")
def extract_data():
    pipeline = Pipeline(CONFIG)
    pipeline.fetch_data()
    pipeline.create_database()
    pipeline.process_manuals()
    return {"status": "success"}

@app.get("/process")
def process_data():
    processor = ManualProcessor(CONFIG['db_name'], CONFIG['text_directory'], CONFIG['markdown_directory'])
    processor.process_all_manuals()
    return {"status": "success"}
