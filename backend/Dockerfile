# Start with a standard Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies, including LibreOffice for docx conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on (Render will use this)
EXPOSE 5000

# The command to run the application using Gunicorn
# This will run the 'app' object inside the 'app.py' file
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "app:app"]