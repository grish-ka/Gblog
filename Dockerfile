FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port Flask runs on
EXPOSE 8080

# Set environment variables
ENV FLASK_APP=Gblog.py
ENV FLASK_ENV=production
ENV OAUTHLIB_INSECURE_TRANSPORT=1

# Run Flask with proper signal handling
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8080"]