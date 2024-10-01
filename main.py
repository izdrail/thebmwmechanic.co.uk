import os
import sqlite3
import requests
import logging
from spire.pdf import PdfDocument, FileFormat, PdfTextExtractor, PdfTextExtractOptions
from spire.pdf.common import *

from spire.pdf import *

from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, HTTPException
from pathlib import Path
from typing import List, Optional
from sqlmodel import Field, Session, SQLModel, create_engine, select


from llama_cpp import Llama


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG = {
    'pdf_directory': 'public/manuals_pdfs',
    'html_directory': 'public/manuals_html',
    'text_directory': 'public//manuals_text',
    'markdown_directory': 'public/manuals_md',
    'db_name': 'sqlite:///manuals.db',
    'api_url': 'https://club.autodoc.co.uk/api/v4/instructions/all?order_key=popular&order_type=desc&q=&maker_id=16&type=1&limit=1000&offset=0',
    'max_workers': 5
}


# SQLModel setup
class Manual(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    is_favorite: Optional[bool] = None
    manual_link: Optional[str] = None
    manual_preview: Optional[str] = None
    manual_preview_big: Optional[str] = None
    manual_preview_big_retina: Optional[str] = None
    manual_title: str
    manual_downloads: Optional[int] = None
    manual_size: Optional[int] = None
    axle: Optional[str] = None
    youtube_key: Optional[str] = None
    youtube_title: Optional[str] = None
    alias: Optional[str] = None
    youtube_preview_url: Optional[str] = None
    youtube_view_count: Optional[int] = None
    youtube_published_at: Optional[str] = None  # Use str for compatibility with JSON
    main_maker_title: Optional[str] = None
    main_model_title: Optional[str] = None
    main_group_title: Optional[str] = None
    created_at: Optional[str] = None  # Use str for compatibility with JSON
    single_type: Optional[int] = None
    channel_id: Optional[int] = None
    main_maker_title_cyr: Optional[str] = None
    main_model_title_cyr: Optional[str] = None
    main_group_title_cyr: Optional[str] = None
    is_basic: Optional[bool] = None
    is_universal: Optional[bool] = None
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
            is_universal BOOLEAN,
            txt_path TEXT
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
        if not self.data or 'instructions' not in self.data or not self.data['instructions'].get('data', []):
            raise HTTPException(status_code=400, detail="No data to process")

        instructions = self.data['instructions']['data']
        for item in instructions:
            manual = Manual(
                id=item['id'],
                is_favorite=item.get('is_favorite'),
                manual_link=item.get('manual_link'),
                manual_preview=item.get('manual_preview'),
                manual_preview_big=item.get('manual_preview_big'),
                manual_preview_big_retina=item.get('manual_preview_big_retina'),
                manual_title=item['manual_title'],
                manual_downloads=item.get('manual_downloads'),
                manual_size=item.get('manual_size'),
                axle=item.get('axle'),
                youtube_key=item.get('youtube_key'),
                youtube_title=item.get('youtube_title'),
                alias=item.get('alias'),
                youtube_preview_url=item.get('youtube_preview_url'),
                youtube_view_count=item.get('youtube_view_count'),
                youtube_published_at=item.get('youtube_published_at'),
                main_maker_title=item.get('main_maker_title'),
                main_model_title=item.get('main_model_title'),
                main_group_title=item.get('main_group_title'),
                created_at=item.get('created_at'),
                single_type=item.get('single_type'),
                channel_id=item.get('channel_id'),
                main_maker_title_cyr=item.get('main_maker_title_cyr'),
                main_model_title_cyr=item.get('main_model_title_cyr'),
                main_group_title_cyr=item.get('main_group_title_cyr'),
                is_basic=item.get('is_basic'),
                is_universal=item.get('is_universal'),
                txt_path=item.get('alias')  # Saving alias as txt_path
            )
            session.add(manual)
            logging.info(f"Inserted manual: {manual.manual_title}")
        session.commit()

    def process_manuals(self, session: Session):
        """Processes manuals with PDF download and text extraction."""
        if not self.data or 'instructions' not in self.data or not self.data['instructions'].get('data', []):
            logging.warning("No data available for processing manuals.")
            return

        instructions = self.data['instructions']['data']
        with ThreadPoolExecutor(max_workers=CONFIG['max_workers']) as executor:
            futures = [executor.submit(self.process_single_manual, item, session) for item in instructions]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error in processing manuals: {e}")

    def process_single_manual(self, item, session: Session):
        """Processes a single manual."""
        try:
            logging.info(f"Processing manual: {item['manual_title']}")
            pdf_path = self.download_pdf(item['manual_link'], item['manual_title'])

            print(pdf_path)
            if pdf_path:
                page_count = self.count_pdf_pages(pdf_path)
                if page_count > 2:
                    self.modify_pdf(pdf_path)

                    text = self.extract_text_from_pdf(pdf_path)
                    cleaned_text = self.clean_text(text)

                    self.save_text(cleaned_text, item['manual_title'])

                    manual = session.exec(select(Manual).where(Manual.id == item['id'])).one()
                    manual.txt_path = f"{item['manual_title'].replace(' ', '_')}.txt"
                    session.add(manual)
                    session.commit()
                    logging.info(f"Updated manual record for: {item['manual_title']}")

        except Exception as e:
            logging.error(f"Error in processing manual: {e}")

    def download_pdf(self, manual_link: str, title: str) -> Optional[str]:
        """Downloads a PDF file from the given link."""
        pdf_path = os.path.join(CONFIG['pdf_directory'], f"{title}.pdf")
        try:
            response = requests.get(manual_link)
            response.raise_for_status()
            with open(pdf_path, 'wb') as pdf_file:
                pdf_file.write(response.content)
            logging.info(f"Downloaded PDF: {pdf_path}")
            return pdf_path
        except Exception as e:
            logging.error(f"Error downloading PDF: {e}")
            return None

    def count_pdf_pages(self, pdf_path: str) -> int:
        """Counts the pages of the PDF."""
        print(pdf_path)
        try:
            pdf = PdfDocument()
            pdf.LoadFromFile(pdf_path)
            count = pdf.Pages.Count
            return count
        except Exception as e:
            logging.error(f"Error loading PDF: {e}")
            return 0

    def modify_pdf(self, pdf_path: str):
        """Modifies the PDF file (e.g., remove first page)."""
        #TODO: Fix this to remove the first and last page
        #
        pdf = PdfDocument()
        pdf.LoadFromFile(pdf_path)
        pdf.Pages.RemoveAt(0)  # Remove the first page
        pdf.save(pdf_path, FileFormat.PDF)
        logging.info(f"Modified PDF: {pdf_path}")

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extracts text from a PDF file."""
        text_extractor = PdfTextExtractor()
        doc = PdfDocument.LoadFromFile(pdf_path)
        options = PdfTextExtractOptions()
        extracted_text = text_extractor.extract(doc, options)
        return extracted_text

    def clean_text(self, text: str) -> str:
        """Cleans the extracted text."""
        for phrase in self.replace_phrases:
            text = text.replace(phrase, "")
        return text.strip()

    def save_text(self, text: str, title: str):
        """Saves the cleaned text into a .txt file."""
        txt_file_path = os.path.join(CONFIG['text_directory'], f"{title.replace(' ', '_')}.txt")
        with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        logging.info(f"Saved text file: {txt_file_path}")


@app.on_event("startup")
def startup_event():
    """Run on startup."""
    create_table_if_not_exists()


@app.post("/fetch-manuals/")
def fetch_manuals():
    """Fetch manuals from the external API and save to database."""
    pipeline = Pipeline()
    pipeline.fetch_data()
    with Session(engine) as session:
        pipeline.insert_manuals_into_db(session)
    return {"message": "Manuals fetched and stored successfully."}


@app.get("/process-manuals/")
def process_manuals():
    """Process manuals (download PDFs, extract text, and generate Markdown)."""
    pipeline = Pipeline()
    with Session(engine) as session:
        pipeline.fetch_data()  # Ensure we have the latest data
        pipeline.process_manuals(session)
    return {"message": "Manuals processed successfully."}


@app.get("/manuals/", response_model=List[Manual])
def get_manuals():
    """Retrieve all manuals from the database."""
    with Session(engine) as session:
        manuals = session.exec(select(Manual)).all()
        return manuals


@app.get("/chat", response_model=List[Manual])
def get_chat():
    """Chats with lama cpp."""
    llm = Llama.from_pretrained(
        repo_id="Qwen/Qwen2-0.5B-Instruct-GGUF",
        filename="*q8_0.gguf",
        verbose=True
    )
    output = llm(
        "Q: Name the planets in the solar system? A: ",  # Prompt
        max_tokens=32,  # Generate up to 32 tokens, set to None to generate up to the end of the context window
        stop=["Q:", "\n"],  # Stop generating just before the model would generate a new question
        echo=True  # Echo the prompt back in the output
    )  # Generate a completion, can also call create_completion
    return {
        "data": output
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
