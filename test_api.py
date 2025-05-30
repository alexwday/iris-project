#!/usr/bin/env python3
"""
IRIS API Testing Examples

This script demonstrates how to test the IRIS FastAPI endpoints with various
methods including Python requests, cURL commands, and FastAPI test client.

Usage:
    python test_api.py

Make sure the API server is running first:
    uvicorn iris.src.api:app --host 0.0.0.0 --port 8000
"""

import requests
import json
import time
from typing import Dict, Any

# API base URL (adjust for your environment)
API_BASE_URL = "http://localhost:8000"

def test_health_endpoint():
    """Test the health check endpoint"""
    print("🔍 Testing Health Endpoint...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Health check passed!")
        else:
            print("❌ Health check failed!")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check error: {e}")
    
    print("-" * 50)

def test_chat_endpoint():
    """Test the chat endpoint with a sample conversation"""
    print("💬 Testing Chat Endpoint...")
    
    # Sample conversation
    test_conversation = {
        "messages": [
            {"role": "user", "content": "What are the latest tax regulations for Canadian corporations?"}
        ],
        "stream": False
    }
    
    try:
        print(f"Sending request: {json.dumps(test_conversation, indent=2)}")
        
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json=test_conversation,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minutes timeout for chat processing
        )
        end_time = time.time()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {(end_time - start_time):.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Chat request successful!")
            print(f"Response: {result.get('response', 'No response')[:200]}...")
            print(f"Agent Used: {result.get('agent_used', 'Unknown')}")
            print(f"Processing Time: {result.get('processing_time_ms', 0)}ms")
            print(f"Run UUID: {result.get('run_uuid', 'None')}")
            
            if result.get('token_usage'):
                print(f"Token Usage: {result['token_usage']}")
        else:
            print("❌ Chat request failed!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Chat request error: {e}")
    
    print("-" * 50)

def test_with_conversation_history():
    """Test with multi-turn conversation"""
    print("🔄 Testing Multi-turn Conversation...")
    
    conversation = {
        "messages": [
            {"role": "user", "content": "What is IFRS 16?"},
            {"role": "assistant", "content": "IFRS 16 is the International Financial Reporting Standard that deals with lease accounting..."},
            {"role": "user", "content": "How does it affect financial statements?"}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json=conversation,
            headers={"Content-Type": "application/json"},
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Multi-turn conversation successful!")
            print(f"Response: {result.get('response', 'No response')[:200]}...")
        else:
            print("❌ Multi-turn conversation failed!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Multi-turn conversation error: {e}")
    
    print("-" * 50)

def print_curl_examples():
    """Print cURL command examples"""
    print("📋 cURL Examples:")
    print("\n1. Health Check:")
    print(f"curl -X GET \"{API_BASE_URL}/health\"")
    
    print("\n2. Simple Chat:")
    print(f"""curl -X POST "{API_BASE_URL}/chat" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "messages": [
      {{"role": "user", "content": "What is the current tax rate?"}}
    ],
    "stream": false
  }}'""")
    
    print("\n3. Multi-turn Chat:")
    print(f"""curl -X POST "{API_BASE_URL}/chat" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "messages": [
      {{"role": "user", "content": "What is IFRS 16?"}},
      {{"role": "assistant", "content": "IFRS 16 deals with lease accounting..."}},
      {{"role": "user", "content": "How does it affect balance sheets?"}}
    ]
  }}'""")
    
    print("-" * 50)

def test_fastapi_client():
    """Test using FastAPI test client (requires the API code to be importable)"""
    print("🧪 Testing with FastAPI Test Client...")
    
    try:
        from fastapi.testclient import TestClient
        from iris.src.api import app
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        print(f"Health check status: {response.status_code}")
        
        # Test chat endpoint
        test_data = {
            "messages": [{"role": "user", "content": "Test message"}],
            "stream": False
        }
        
        response = client.post("/chat", json=test_data)
        print(f"Chat test status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ FastAPI test client works!")
        else:
            print(f"❌ FastAPI test client error: {response.text}")
            
    except ImportError:
        print("⚠️  FastAPI test client not available (API not importable or dependencies missing)")
    except Exception as e:
        print(f"❌ FastAPI test client error: {e}")
    
    print("-" * 50)

def main():
    """Run all tests"""
    print("🚀 IRIS API Testing Suite")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print(f"✅ API server is running at {API_BASE_URL}")
        else:
            print(f"⚠️  API server responded with status {response.status_code}")
    except requests.exceptions.RequestException:
        print(f"❌ Cannot connect to API server at {API_BASE_URL}")
        print("Make sure to start the server first:")
        print("uvicorn iris.src.api:app --host 0.0.0.0 --port 8000")
        return
    
    print("=" * 50)
    
    # Run tests
    test_health_endpoint()
    test_chat_endpoint()
    test_with_conversation_history()
    test_fastapi_client()
    print_curl_examples()
    
    print("🏁 Testing completed!")

if __name__ == "__main__":
    main()