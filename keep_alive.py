from flask import Flask, jsonify
from threading import Thread
import time
import os

app = Flask(__name__)


@app.route('/')
def home():
    """Health check endpoint for UptimeRobot"""
    return jsonify({
        "status": "alive",
        "message": "Discord Bot is running",
        "timestamp": time.time()
    })


@app.route('/health')
def health():
    """Additional health check endpoint"""
    return jsonify({
        "status": "healthy",
        "uptime": time.time(),
        "service": "Discord Bot - Policia Civil"
    })


@app.route('/status')
def status():
    """Bot status endpoint"""
    return jsonify({
        "bot_name":
        "Policia Civil Bot",
        "version":
        "1.0.0",
        "status":
        "operational",
        "features": [
            "pc!entorno - Emergency services menu",
            "pc!whitelist - Whitelist application system",
            "Reaction logging system", "24/7 uptime monitoring"
        ]
    })


def run():
    """Run the Flask server"""
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


def keep_alive():
    """Start the Flask server in a separate thread"""
    print("🌐 Iniciando servidor keep-alive...")
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print("✅ Servidor keep-alive iniciado en puerto 5000")
