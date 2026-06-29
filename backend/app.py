from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()

from routes.upload import upload_bp
from routes.chat import chat_bp
from routes.auth import auth_bp
from config import Config
Config.validate()

from database import init_db
init_db()

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "http://localhost:3000",  # Next.js local
                "http://localhost:5173",  # Vite local
                "https://doc-bot-frontend.vercel.app" # production
            ]
        }
    }
)

app.config["MAX_CONTENT_LENGTH"] = Config.MAX_FILE_SIZE_MB * 1024 * 1024

app.register_blueprint(upload_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(auth_bp)

@app.route("/health", methods=["GET"])
def health():
    return {
        "status": "healthy"
    }, 200

@app.route("/")
def home():
    return {
        "message": "Smart Document Q&A Chatbot backend is running"
    }, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)