# backend/app.py

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from transformers import pipeline
import os
import re

app = Flask(__name__)
CORS(app) # Enable CORS for frontend to communicate with backend

# --- AI Model Initialization ---
# Using a summarization pipeline from Hugging Face Transformers
# 'sshleifer/distilbart-cnn-12-6' is a good balance of speed and quality for summarization
print("Loading AI summarization model... This may take a moment.")
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
print("AI summarization model loaded.")

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'} # We'll only simulate for TXT for simplicity initially

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Helper function for text extraction (simplified) ---
def extract_text_from_file(filepath, file_extension):
    """
    Extracts text from a given file.
    This is a simplified version. For actual PDF/DOCX,
    you'd use libraries like 'PyPDF2'/'pdfplumber' for PDF
    and 'python-docx' for DOCX.
    """
    if file_extension == 'txt':
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    elif file_extension == 'pdf':
        # Placeholder for PDF extraction (requires PyPDF2/pdfplumber)
        # You would install: pip install PyPDF2
        # Example:
        # import PyPDF2
        # with open(filepath, 'rb') as file:
        #     reader = PyPDF2.PdfReader(file)
        #     text = ""
        #     for page in reader.pages:
        #         text += page.extract_text() or ""
        # return text
        return "PDF text extraction not implemented in this demo. Please use .txt"
    elif file_extension == 'docx':
        # Placeholder for DOCX extraction (requires python-docx)
        # You would install: pip install python-docx
        # Example:
        # from docx import Document
        # document = Document(filepath)
        # text = "\n".join([para.text for para in document.paragraphs])
        # return text
        return "DOCX text extraction not implemented in this demo. Please use .txt"
    return ""

# --- Mindmap Generation Logic (Simplified AI) ---
def generate_mindmap_data(text):
    # Step 1: Summarize the text using the loaded model
    # The summarizer often works best with chunks of text if input is very long
    max_chunk_length = 1024 # Max tokens for the model
    chunks = [text[i:i+max_chunk_length] for i in range(0, len(text), max_chunk_length)]
    
    summaries = []
    for chunk in chunks:
        # Ensure input is not empty
        if chunk.strip():
            # Adjust max_length and min_length for desired summary length
            # Note: For very long texts, processing all chunks can be slow
            summary = summarizer(chunk, max_length=150, min_length=30, do_sample=False)
            summaries.append(summary[0]['summary_text'])
    
    full_summary = " ".join(summaries)

    # Step 2: Simulate Mindmap Node Generation
    # For a simple mindmap, we can take the summary and extract key sentences/phrases.
    # A real mindmap AI would do entity recognition (e.g., diseases, drugs, anatomy)
    # and relationship extraction to build a proper hierarchical structure.

    # Here, we'll just split the summary into sentences and treat them as potential nodes.
    # We'll also try to identify some "main topics" based on common medical keywords
    # This is HIGHLY simplistic for demonstration purposes.

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_summary) if s.strip()]

    # Simple keyword-based main topic extraction (very naive)
    medical_keywords = ["disease", "syndrome", "therapy", "treatment", "diagnosis", "patient", "cell", "organ", "system", "medicine", "drug", "condition", "pathology", "physiology"]
    main_topics = []
    for sentence in sentences:
        for keyword in medical_keywords:
            if keyword in sentence.lower() and sentence not in main_topics:
                main_topics.append(sentence)
                break
    
    # If no main topics found, just pick the first few sentences as main
    if not main_topics and sentences:
        main_topics = sentences[:min(3, len(sentences))]

    # Create a simple hierarchical structure for the mindmap
    # The 'root' will be the document title/main theme
    # 'main_topics' will be level 1 nodes
    # Remaining sentences will be sub-nodes of the main topics (very basic assignment)

    mindmap = {
        "id": "root",
        "text": "Medical Document Overview", # Placeholder, ideally derived from doc title
        "children": []
    }

    # Track which sentences have been used as main topics or subtopics
    used_sentences = set()

    for i, topic_sentence in enumerate(main_topics):
        node = {
            "id": f"node-{i}",
            "text": topic_sentence,
            "children": []
        }
        mindmap["children"].append(node)
        used_sentences.add(topic_sentence)

        # Assign other sentences as children to this main topic
        # This is a random/sequential assignment for demo, not intelligent
        sub_nodes_added = 0
        for sub_sentence in sentences:
            if sub_sentence not in used_sentences and sub_nodes_added < 3: # Limit sub-nodes for clarity
                node["children"].append({
                    "id": f"node-{i}-sub-{sub_nodes_added}",
                    "text": sub_sentence
                })
                used_sentences.add(sub_sentence)
                sub_nodes_added += 1

    # Add any remaining unused sentences as children to a generic "Other Details" node if it exists,
    # or to the root if not enough main topics were found.
    if len(sentences) > len(used_sentences):
        other_details_node = {
            "id": "node-other",
            "text": "Other Details",
            "children": []
        }
        for sub_sentence in sentences:
            if sub_sentence not in used_sentences:
                 other_details_node["children"].append({
                    "id": f"node-other-sub-{len(other_details_node['children'])}",
                    "text": sub_sentence
                })
        if other_details_node["children"]:
            mindmap["children"].append(other_details_node)

    return mindmap


# --- API Endpoints ---

@app.route('/api/upload-and-generate', methods=['POST'])
def upload_and_generate():
    if 'document' not in request.files:
        return jsonify({"error": "No document part in the request"}), 400

    file = request.files['document']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = file.filename
        file_extension = filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # 1. Extract text
            text_content = extract_text_from_file(filepath, file_extension)
            if not text_content or "not implemented" in text_content: # Check for placeholder errors
                 return jsonify({"error": text_content}), 400
            
            if len(text_content) < 50: # Basic check for meaningful content
                return jsonify({"error": "Document content is too short for meaningful analysis."}), 400

            # 2. Generate mindmap data using AI
            mindmap_data = generate_mindmap_data(text_content)

            # Optional: Clean up the uploaded file after processing
            # os.remove(filepath)

            return jsonify({"message": "Mindmap generated successfully", "mindmap": mindmap_data}), 200

        except Exception as e:
            app.logger.error(f"Error during processing: {e}")
            return jsonify({"error": f"An error occurred during processing: {str(e)}"}), 500
    else:
        return jsonify({"error": "File type not allowed or no file selected"}), 400

# --- Serve Static Files (Frontend) ---
# This allows Flask to serve your index.html if you access the root URL
@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # Serve other static files from the frontend directory
    # (e.g., if you had separate CSS/JS files)
    return send_from_directory('../frontend', path)


if __name__ == '__main__':
    # When running locally, Flask defaults to http://127.0.0.1:5000/
    # In a production environment, you would use a production-ready WSGI server like Gunicorn.
    app.run(debug=True) # debug=True reloads server on code changes and provides debugger