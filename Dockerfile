# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . .

# Make the script executable
RUN chmod +x memory_app.py

# Set the entrypoint to the python interpreter and our script
ENTRYPOINT ["python", "./memory_app.py"]
