#!/usr/bin/env python3
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return "Simple test"

@app.route('/data')
def get_data():
    return jsonify([{"test": "data"}])

@app.route('/device_groups')
def get_groups():
    return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
