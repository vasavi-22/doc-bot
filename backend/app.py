from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()

from routes.upload import upload_bp
from routes.chat import chat_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(upload_bp)
app.register_blueprint(chat_bp)

if __name__ == "__main__":
    app.run(debug=True)