from flask import Flask, request, jsonify, render_template
import os
import time
from StakeholderAgent import StakeholderAgent

app = Flask(__name__, static_folder='.', template_folder='.')

# Initialize the Stakeholder Agent
stakeholder_agent = StakeholderAgent()

@app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        uploaded_file = request.files.get("file")
        text_input = request.form.get("text", "").strip()
        
        print(f"Received file: {uploaded_file.filename if uploaded_file else 'None'}")
        print(f"Received text: {text_input[:100]}..." if text_input else "No text")
        
        if not text_input and not uploaded_file:
            return jsonify({'error': 'No input provided'}), 400

        # Create uploads directory
        uploads_dir = './uploads'
        os.makedirs(uploads_dir, exist_ok=True)
        
        file_path = None
        file_type = None
        
        if uploaded_file and uploaded_file.filename != "":
            file_path = os.path.join(uploads_dir, uploaded_file.filename)
            uploaded_file.save(file_path)
            
            # Determine file type for tool routing
            file_ext = os.path.splitext(uploaded_file.filename)[1].lower()
            file_type_mapping = {
                '.txt': 'text',
                '.pdf': 'pdf', 
                '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image',
                '.wav': 'audio', '.mp3': 'audio', '.m4a': 'audio',
                '.csv': 'csv',
                '.ppt': 'ppt', '.pptx': 'ppt',
                '.doc': 'doc', '.docx': 'doc',
                '.xls': 'xlsx', '.xlsx': 'xlsx'
            }
            file_type = file_type_mapping.get(file_ext, 'unknown')

        print(f"Processing with file_type: {file_type}")

        # Use the Stakeholder Agent to process the input
        try:
            result = stakeholder_agent.process_web_input(
                text_input=text_input,
                file_path=file_path,
                file_type=file_type
            )
            
            return jsonify({
                "message": "GMI Analysis completed successfully",
                "final_markdown": result
            })
            
        except Exception as e:
            print(f"Error in stakeholder processing: {e}")
            return jsonify({'error': f'Processing error: {str(e)}'}), 500

    except Exception as e:
        print(f"Error in upload_file: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    print("🚀 Starting GMI Web Interface with integrated Stakeholder Agent...")
    print("📱 Beautiful UI with full multimodal capabilities")
    print("🤖 Direct StakeholderAgent integration with A2A compatibility")
    print("🌐 Access at: http://localhost:3000")
    print("=" * 65)
    app.run(debug=True, port=3000)
