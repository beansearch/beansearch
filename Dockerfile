# Use an official Python image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the Flask port
EXPOSE 5000

# Run the Flask app
#CMD ["python", "app.py"]
CMD ["gunicorn", "--access-logfile", "-", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
