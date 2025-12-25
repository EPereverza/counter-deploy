import os
import time
from flask import Flask, jsonify
from redis import Redis, RedisError
from dotenv import load_dotenv
from pathlib import Path
from flask import send_from_directory, request
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD') or None

app = Flask(__name__, static_folder=str(BASE_DIR / 'static'), static_url_path='/')
CORS(app)

# Connect to redis with retry
def get_redis_client(retries=5, wait=1):
    for i in range(retries):
        try:
            client = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, decode_responses=True)
            # test
            client.ping()
            return client
        except RedisError as e:
            if i == retries - 1:
                raise
            time.sleep(wait)
    raise RedisError("Cannot connect to Redis")

r = get_redis_client()

COUNTER_KEY = 'counter:value'

# Ensure key exists
if r.get(COUNTER_KEY) is None:
    r.set(COUNTER_KEY, 0)

@app.route('/api/counter', methods=['GET'])
def get_counter():
    try:
        v = int(r.get(COUNTER_KEY) or 0)
        return jsonify({"value": v})
    except Exception as e:
        return jsonify({"error": "Redis error"}), 500

@app.route('/api/counter/increment', methods=['POST'])
def increment():
    try:
        v = r.incr(COUNTER_KEY)
        return jsonify({"value": int(v)})
    except Exception as e:
        return jsonify({"error": "Redis error"}), 500

@app.route('/api/counter/decrement', methods=['POST'])
def decrement():
    try:
        current_value = r.get(COUNTER_KEY)
        current_value = int(current_value) if current_value else 0
        
        if current_value > 0:
            v = r.decr(COUNTER_KEY)
        else:
            v = current_value
            
        return jsonify({"value": int(v)})
    except Exception as e:
        return jsonify({"error": "Redis error"}), 400

@app.route('/api/counter/reset', methods=['POST'])
def reset():
    try:
        r.set(COUNTER_KEY, 0)
        return jsonify({"value": 0})
    except Exception as e:
        return jsonify({"error": "Redis error"}), 500

# Serve SPA
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    static_dir = BASE_DIR / 'static'
    if path != "" and (static_dir / path).exists():
        return send_from_directory(str(static_dir), path)
    return send_from_directory(str(static_dir), 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8000)))
