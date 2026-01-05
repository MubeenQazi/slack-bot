#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick webhook test - verifies the alert endpoint works
"""
import requests
import json
import time
import subprocess
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Start server in stub mode
print("Starting Alert Bot in stub mode...")
env = os.environ.copy()
env['SLACK_STUB'] = '1'

server_process = subprocess.Popen(
    [sys.executable, 'app.py'],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Wait for server to start
print("Waiting for server to start...")
time.sleep(3)

try:
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    response = requests.get('http://localhost:3000/health')
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Test webhook alert
    print("\n2. Testing webhook alert...")
    alert_data = {
        "service": "api",
        "severity": "high",
        "message": "Test alert from automated test"
    }
    
    response = requests.post(
        'http://localhost:3000/webhook/alert',
        json=alert_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("Webhook test PASSED")
    else:
        print("Webhook test FAILED")
        sys.exit(1)
    
    # Test invalid request
    print("\n3. Testing invalid request (missing fields)...")
    response = requests.post(
        'http://localhost:3000/webhook/alert',
        json={"service": "api"},  # Missing severity and message
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    if response.status_code == 400:
        print("Validation test PASSED")
    else:
        print("Validation test FAILED")
    
    print("\n" + "=" * 60)
    print("All webhook tests passed!")
    print("=" * 60)
    
except Exception as e:
    print(f"Test failed: {e}")
    sys.exit(1)
    
finally:
    print("\nStopping server...")
    server_process.terminate()
    server_process.wait()
