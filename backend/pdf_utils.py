import io
import os
import pikepdf
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from pdf2docx import Converter
from docx2pdf import convert as convert_docx
import tempfile

# --- MERGE & SPLIT ---
def merge_pdfs(file_streams):
    """
    Merges multiple PDF file streams into one.
    :param file_streams: A list of file-like objects (streams).
    :return: An io.BytesIO object containing the merged PDF.
    """
    merger = PdfMerger()
    for stream in file_streams:
        merger.append(stream)
    output_stream = io.BytesIO()
    merger.write(output_stream)
    merger.close()
    output_stream.seek(0)
    return output_stream

def parse_page_ranges(ranges_string, max_pages):
    """
    Parses a string like "1-3,5,8" into a set of page indices (0-based).
    Validates against the total number of pages.
    """
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
    """
    Extracts specific pages from a PDF file stream.
    """
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

# --- CONVERSIONS ---
def convert_pdf_to_word(file_stream):
    """
    Converts a PDF file stream into a Word document stream using temporary files.
    """
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

def convert_word_to_pdf(file_stream):
    """
    Converts a Word document stream into a PDF stream using temporary files.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx:
        temp_docx.write(file_stream.read())
        temp_docx_path = temp_docx.name
    temp_pdf_path = temp_docx_path.replace(".docx", ".pdf")
    convert_docx(temp_docx_path, temp_pdf_path)
    with open(temp_pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    os.remove(temp_docx_path)
    os.remove(temp_pdf_path)
    return io.BytesIO(pdf_bytes)

# --- COMPRESSION & SECURITY ---
def compress_pdf(file_stream, level='medium'):
    """
    Compresses a PDF by re-saving it with optimized settings.
    """
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
    """
    Removes password protection from a PDF file stream.
    """
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
    """
    Encrypts a PDF file stream with a user-provided password.
    """
    try:
        pdf = pikepdf.Pdf.open(file_stream)
        output_stream = io.BytesIO()
        # Apply AES-256 bit encryption (R=6) and save to the new stream
        pdf.save(
            output_stream, 
            encryption=pikepdf.Encryption(owner=password, user=password, R=6)
        )
        pdf.close()
        output_stream.seek(0)
        return output_stream
    except Exception as e:
        raise e