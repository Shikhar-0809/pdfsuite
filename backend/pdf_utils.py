import io
import os
import pikepdf
import subprocess  # <-- Make sure this is imported
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from pdf2docx import Converter
# We no longer need to import 'convert' from docx2pdf
# from docx2pdf import convert as convert_docx 
import tempfile

# ... (merge_pdfs, parse_page_ranges, split_pdf, and convert_pdf_to_word are all unchanged) ...
def merge_pdfs(file_streams):
    merger = PdfMerger()
    for stream in file_streams:
        merger.append(stream)
    output_stream = io.BytesIO()
    merger.write(output_stream)
    merger.close()
    output_stream.seek(0)
    return output_stream

def parse_page_ranges(ranges_string, max_pages):
    pages_to_extract = set()
    parts = ranges_string.replace(" ", "").split(',')
    for part in parts:
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start > end or start < 1 or end > max_pages:
                    raise ValueError("Invalid page range.")
                pages_to_extract.update(range(start - 1, end))
            except ValueError:
                raise ValueError(f"Invalid range format: '{part}'")
        else:
            try:
                page = int(part)
                if page < 1 or page > max_pages:
                    raise ValueError(f"Page number {page} is out of bounds.")
                pages_to_extract.add(page - 1)
            except ValueError:
                raise ValueError(f"Invalid page number: '{part}'")
    return sorted(list(pages_to_extract))

def split_pdf(file_stream, ranges_string):
    reader = PdfReader(file_stream)
    writer = PdfWriter()
    total_pages = len(reader.pages)
    try:
        pages_indices = parse_page_ranges(ranges_string, total_pages)
    except ValueError as e:
        raise e
    if not pages_indices:
        raise ValueError("No valid pages selected to split.")
    for index in pages_indices:
        writer.add_page(reader.pages[index])
    output_stream = io.BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream

def convert_pdf_to_word(file_stream):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(file_stream.read())
        temp_pdf_path = temp_pdf.name
    temp_docx_path = temp_pdf_path.replace(".pdf", ".docx")
    cv = Converter(temp_pdf_path)
    cv.convert(temp_docx_path)
    cv.close()
    with open(temp_docx_path, 'rb') as f:
        docx_bytes = f.read()
    os.remove(temp_pdf_path)
    os.remove(temp_docx_path)
    return io.BytesIO(docx_bytes)

# --- THIS IS THE FIXED FUNCTION ---
def convert_word_to_pdf(file_stream):
    """
    Converts a Word document to PDF by directly calling LibreOffice.
    This bypasses the docx2pdf library's faulty auto-detection on Linux.
    """
    # Create a temporary directory to work in
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a path for the temporary input docx file
        temp_docx_path = os.path.join(temp_dir, 'input.docx')
        
        # Write the uploaded file's content to the temporary docx file
        with open(temp_docx_path, 'wb') as f:
            f.write(file_stream.read())
            
        # Construct the command to call LibreOffice directly
        # We use the path we discovered with our debug endpoint
        command = [
            '/usr/bin/libreoffice',
            '--headless',
            '--convert-to',
            'pdf',
            '--outdir',
            temp_dir,
            temp_docx_path
        ]
        
        # Execute the command
        # check=True will raise an error if the conversion fails
        subprocess.run(command, check=True)
        
        # The output file will be named 'input.pdf' in the same directory
        temp_pdf_path = os.path.join(temp_dir, 'input.pdf')
        
        # Read the contents of the newly created PDF file
        with open(temp_pdf_path, 'rb') as f:
            pdf_bytes = f.read()
            
    # The temporary directory and its contents are automatically deleted
    # when the 'with' block is exited.
    
    # Return the PDF data as an in-memory stream
    return io.BytesIO(pdf_bytes)

# ... (compress_pdf, unlock_pdf, and protect_pdf are all unchanged) ...
def compress_pdf(file_stream, level='medium'):
    pdf = pikepdf.Pdf.open(file_stream)
    output_stream = io.BytesIO()
    pdf.save(
        output_stream,
        compress_streams=True,
        linearize=True,
        object_stream_mode=pikepdf.ObjectStreamMode.generate
    )
    pdf.close()
    output_stream.seek(0)
    return output_stream

def unlock_pdf(file_stream, password):
    try:
        pdf = pikepdf.Pdf.open(file_stream, password=password)
        output_stream = io.BytesIO()
        pdf.save(output_stream)
        pdf.close()
        output_stream.seek(0)
        return output_stream
    except pikepdf.PasswordError:
        raise ValueError("Incorrect password provided.")
    except Exception as e:
        raise e

def protect_pdf(file_stream, password):
    try:
        pdf = pikepdf.Pdf.open(file_stream)
        output_stream = io.BytesIO()
        pdf.save(
            output_stream, 
            encryption=pikepdf.Encryption(owner=password, user=password, R=6)
        )
        pdf.close()
        output_stream.seek(0)
        return output_stream
    except Exception as e:
        raise e