from flask import Flask, request, jsonify
from langchain.document_loaders import PyPDFLoader
import re
import requests

app = Flask(__name__)

# API Unify.ai Configuration
UNIFY_API_URL = "https://api.unify.ai/v0/chat/completions"
UNIFY_API_KEY = "Bearer uX-+1Nhapmvo2Qn+GXXIlfhy5IU3w2MNi5ODtiRHj1k="

# Fungsi untuk memuat dan membersihkan PDF
def load_and_clean_pdf(file_path):
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    all_text = [doc.page_content for doc in documents]
    combined_text = " ".join(all_text)
    clean_text = re.sub(r'(?<![\.\?!])\n', ' ', combined_text)
    return clean_text

# Fungsi untuk membagi teks menjadi chunk
def chunk_text(text, chunk_size=600, overlap=100):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

# Fungsi untuk mengirim chunk ke Unify.ai
def analyze_chunk(chunk):
    prompt = f"""
    You are an expert in evaluating research proposals. Evaluate the following chunk for:
    1. Feasibility (1-10 scale).
    2. Scientific rigor (1-10 scale).
    3. Alignment with funding goals (1-10 scale).
    4. And please add the reasoning behind your analysis in a separated key in JSON.
    
    Chunk: {chunk}

    Provide the scores and reasoning in JSON format.
    """
    json_input = {"messages": [{"content": prompt, "role": "user"}], "model": "gpt-4o-mini@openai", "temperature" : "0.2"}
    headers = {"Authorization": UNIFY_API_KEY}

    response = requests.post(UNIFY_API_URL, json=json_input, headers=headers)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return {"error": response.text}

# Endpoint untuk menerima file PDF dan memprosesnya
@app.route("/process-proposal", methods=["POST"])
def process_proposal():
    try:
        # Ambil file dari request
        file = request.files["file"]
        file_path = f"./{file.filename}"
        file.save(file_path)

        # Proses PDF
        clean_text = load_and_clean_pdf(file_path)
        chunked_texts = chunk_text(clean_text)

        # Kirim tiap chunk ke API dan kumpulkan hasilnya
        results = [analyze_chunk(chunk) for chunk in chunked_texts]

        return jsonify({"status": "success", "results": results}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
