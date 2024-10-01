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

@app.get("/chat", response_model=List[Manual])
def get_chat():
    """Chats with lama cpp."""
    llm = Llama.from_pretrained(
        repo_id="Orenguteng/Llama-3.1-8B-Lexi-Uncensored-V2-GGUF",
        filename="*Llama-3.1-8B-Lexi-Uncensored_V2_Q8.gguf",
        verbose=True
    )
    llm.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that outputs in markdown format.",
            },
            {
                "role": "system",
                "content": "You will write a blogpost in a professional mechanic engineer tone from a text you receive .",
            },
            {"role": "user", "content": "How to change tailgate struts on BMW 3 Saloon (E90) – replacement guideSIMILAR VIDEO TUTORIAL This video shows the replacement procedure of a similar car part on another vehicle Important! This replacement procedure can be used for: BMW 3 Saloon (E90) 320i 2.0, BMW 3 Saloon (E90) 325i 2.5, BMW 3 Saloon (E90) 330i 3.0, BMW 3 Saloon (E90) 320d 2.0, BMW 3 Saloon (E90) 318i 2.0, BMW 3 Saloon (E90) 318d 2.0, BMW 3 Saloon (E90) 330d 3.0, BMW 3 Saloon (E90) 325xi 2.5, BMW 3 Saloon (E90) 330xi 3.0, BMW 3 Saloon (E90) 330xd 3.0, BMW 3 Saloon (E90) 320si 2.0, BMW 3 Saloon (E90) 335i 3.0, BMW 3 Saloon (E90) 335d 3.0, BMW 3 Saloon (E90) 325d 3.0, BMW 3 Saloon (E90) 335xi 3.0, (+ 11) The steps may slightly vary depending on the car design. This tutorial was created based on the replacement procedure for a similar car part on: BMW 3 Coupe (E92) 330i 3.0 CLUB.AUTODOC.CO.UK 1–7REPLACEMENT: TAILGATE STRUTS – BMW 3 SALOON (E90). TOOLS YOU'LL NEED: Multipurpose grease Flat Screwdriver Buy tools CLUB.AUTODOC.CO.UK 2–7Replacement: tailgate struts – BMW 3 Saloon (E90). AUTODOC recommends: Right and left gas struts of the boot lid should be replaced simultaneously. The replacement procedure is identical for the right and left gas struts of the boot lid. All work should be done with the engine stopped. REPLACEMENT: TAILGATE STRUTS – BMW 3 SALOON (E90). RECOMMENDED SEQUENCE OF STEPS: 1Open the boot lid. 2Release the circlip connecting the gas strut to the boot lid. Use a flat screwdriver. CLUB.AUTODOC.CO.UK 3–73 Release the circlip connecting the gas strut to the car body. Use a flat screwdriver. Replacement: tailgate struts – BMW 3 Saloon (E90). AUTODOC experts recommend: To avoid any injuries, be sure to hold the boot lid while demounting the gas struts. 4Remove the boot lid gas strut. 5Clean the fasteners of the boot lid gas strut. CLUB.AUTODOC.CO.UK 4–76Treat the fasteners of the boot lid gas strut. Use a multipurpose grease. 7Install the new boot lid gas strut. Replacement: tailgate struts – BMW 3 Saloon (E90). Professionals recommend: To avoid any injuries, be sure to hold the boot lid while installing the gas strut. 8Snap on the circlip connecting the gas strut to the boot lid. 9Snap on the circlip connecting the gas strut to the car body. CLUB.AUTODOC.CO.UK 5–710Check the working condition of the boot lid gas springs after they are installed. 11Close the lid of the luggage compartment. WELL DONE! VIEW MORE TUTORIALS CLUB.AUTODOC.CO.UK 6–7AUTODOC — TOP QUALITY AND AFFORDABLE CAR PARTS ONLINE AUTODOC MOBI"},
        ],
        response_format={
            "type": "json_object",
        },
        temperature=0.7,
    )
    return {
        "data": output
    }

