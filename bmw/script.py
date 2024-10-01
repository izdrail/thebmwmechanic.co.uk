import os
import sqlite3
import requests
import logging
from spire.pdf import PdfDocument, FileFormat
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, HTTPException
from pathlib import Path
from typing import List, Optional
from sqlmodel import Field, Session, SQLModel, create_engine, select

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG = {
    'pdf_directory': 'manuals_pdfs',
    'html_directory': 'manuals_html',
    'text_directory': 'app/manuals_text',
    'markdown_directory': 'manuals_md',
    'db_name': 'sqlite:///manuals.db',
    'api_url': 'https://club.autodoc.co.uk/api/v4/instructions/all?order_key=popular&order_type=desc&q=&maker_id=16&type=1&limit=1000&offset=0',
    'max_workers': 5
}


# SQLModel setup
class Manual(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    manual_title: str
    txt_path: Optional[str] = None


# Create the SQLite database and table
engine = create_engine(CONFIG['db_name'])
SQLModel.metadata.create_all(engine)

# Initialize FastAPI app
app = FastAPI()

# Ensure directories exist
for directory in [CONFIG['pdf_directory'], CONFIG['html_directory'], CONFIG['text_directory'],
                  CONFIG['markdown_directory']]:
    os.makedirs(directory, exist_ok=True)


def create_table_if_not_exists():
    """Function to create the table if it doesn't exist."""
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
    logging.info("Table 'manuals' ensured to exist.")


class ManualProcessor:
    """Processes manuals from a database into Markdown files."""

    def __init__(self, txt_folder: Path, output_folder: Path):
        self.txt_folder = txt_folder
        self.output_folder = output_folder

    def fetch_manual_content(self, txt_path: Optional[str]) -> Optional[str]:
        """Fetches manual content from text files."""
        if not txt_path:
            return None
        manual_file = self.txt_folder / txt_path
        if manual_file.exists():
            with open(manual_file, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            logging.warning(f"{manual_file} not found.")
            return None

    def generate_markdown(self, manual: Manual, manual_content: str):
        """Generates Markdown files from manual data."""
        markdown_content = f"""---
title: {manual.manual_title}
description: {manual.manual_title}
author: Stefan
categories: [Manual]
---
{manual_content}
"""
        self.output_folder.mkdir(parents=True, exist_ok=True)
        output_file = self.output_folder / f"{manual.id}.md"
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(markdown_content)
        logging.info(f"Markdown generated: {output_file}")

    def process_all_manuals(self, session: Session):
        """Processes all manuals in the database."""
        manuals = session.exec(select(Manual)).all()
        for manual in manuals:
            content = self.fetch_manual_content(f"{manual.txt_path}.txt")
            if content:
                self.generate_markdown(manual, content)


class Pipeline:
    def __init__(self):
        self.data = None
        self.replace_phrases = ["Evaluation Warning : The document was created with Spire.PDF for Python.",
                                "CLUB.AUTODOC.CO.UK", "SIMILAR VIDEO TUTORIAL", "AUTODOC", "Buy tools",
                                "VIEW MORE TUTORIALS", "WELL DONE!", "To protect the environment from pollution..."]

    def fetch_data(self):
        """Fetches manual data from the API."""
        try:
            response = requests.get(CONFIG['api_url'])
            response.raise_for_status()
            self.data = response.json()
            logging.info("Fetched data successfully.")
        except requests.RequestException as e:
            logging.error(f"Failed to fetch data: {e}")
            raise HTTPException(status_code=500, detail="Error fetching data from API")

    def insert_manuals_into_db(self, session: Session):
        """Inserts fetched manuals into the SQLite database."""
        if not self.data or not self.data.get('instructions', {}).get('data', []):
            raise HTTPException(status_code=400, detail="No data to process")

        instructions = self.data['instructions']['data']
        for item in instructions:
            manual = Manual(id=item['id'], manual_title=item['manual_title'], txt_path=item['alias'])
            session.add(manual)
            logging.info(f"Inserted manual: {manual.manual_title}")
        session.commit()

    def process_manuals(self, session: Session):
        """Processes manuals with PDF download and text extraction."""
        instructions = self.data['instructions']['data']
        with ThreadPoolExecutor(max_workers=CONFIG['max_workers']) as executor:
            futures = [executor.submit(self.process_single_manual, item, session) for item in instructions]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error in processing manual: {e}")

    def process_single_manual(self, item, session: Session):
        """Processes a single manual."""
        pdf_path = self.download_pdf(item['manual_link'], item['manual_title'])
        if pdf_path:
            page_count = self.count_pdf_pages(pdf_path)
            if page_count > 2:
                self.modify_pdf(pdf_path)
                text = self.extract_text_from_pdf(pdf_path)
                cleaned_text = self.clean_text(text)
                self.save_text(cleaned_text, item['manual_title'])

    def download_pdf(self, link: str, title: str) -> Optional[str]:
        """Downloads the PDF from the provided link."""
        try:
            response = requests.get(link)
            response.raise_for_status()
            filepath = os.path.join(CONFIG['pdf_directory'], f"{title.replace(' ', '_')}.pdf")
            with open(filepath, 'wb') as pdf_file:
                pdf_file.write(response.content)
            logging.info(f"Downloaded PDF: {filepath}")
            return filepath
        except requests.RequestException as e:
            logging.error(f"Failed to download PDF: {e}")
            return None

    def count_pdf_pages(self, pdf_path: str) -> int:
        """Counts the number of pages in a PDF."""
        try:
            doc = PdfDocument()
            doc.LoadFromFile(pdf_path)
            return doc.Pages.Count
        except Exception as e:
            logging.error(f"Error counting pages: {e}")
            return 0

    def modify_pdf(self, pdf_path: str):
        """Modifies the PDF by removing specific pages."""
        try:
            pdf = PdfDocument()
            pdf.LoadFromFile(pdf_path)
            pdf.Pages.RemoveAt(0)
            pdf.Pages.RemoveAt(pdf.Pages.Count - 1)
            pdf.SaveToFile(pdf_path)
            logging.info(f"Modified PDF: {pdf_path}")
        except Exception as e:
            logging.error(f"Error modifying PDF: {e}")

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extracts text from a PDF."""
        try:
            doc = PdfDocument()
            doc.LoadFromFile(pdf_path)
            text = PdfTextExtractor.ExtractText(doc, PdfTextExtractOptions())
            return text
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        """Cleans the extracted text."""
        for phrase in self.replace_phrases:
            text = text.replace(phrase, "")
        return text

    def save_text(self, text: str, title: str):
        """Saves the cleaned text to a file."""
        filepath = os.path.join(CONFIG['text_directory'], f"{title.replace(' ', '_')}.txt")
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(text)
        logging.info(f"Text saved: {filepath}")


@app.on_event("startup")
def on_startup():
    """Startup event to ensure DB and directories are set up."""
    create_table_if_not_exists()  # Ensure the table exists on startup
    SQLModel.metadata.create_all(engine)


@app.get("/extract")
def extract_data():
    """Endpoint to extract data and store it in the database."""
    pipeline = Pipeline()
    session = Session(engine)
    try:
        pipeline.fetch_data()
        pipeline.insert_manuals_into_db(session)
        return {"message": "Data extraction and insertion successful."}
    except Exception as e:
        logging.error(f"Error during extraction: {e}")
        raise HTTPException(status_code=500, detail="Error during data extraction")


@app.get("/process")
def process_manuals():
    """Endpoint to process manuals (downloading PDFs, extracting text)."""
    pipeline = Pipeline()
    session = Session(engine)
    try:
        pipeline.fetch_data()
        pipeline.process_manuals(session)
        return {"message": "Manual processing completed."}
    except Exception as e:
        logging.error(f"Error during manual processing: {e}")
        raise HTTPException(status_code=500, detail="Error during manual processing")
