"""
Utility script to check available Ollama API endpoints.
This script helps determine which API endpoints are available on your Ollama server.
"""
import requests
import json
import sys

def check_endpoint(base_url, endpoint_path, method="GET", payload=None):
    """
    Check if an endpoint is available on the Ollama server
    
    Args:
        base_url: Base URL of the Ollama server
        endpoint_path: Path to check
        method: HTTP method to use
        payload: Optional payload for POST requests
        
    Returns:
        Tuple of (available, response text or error)
    """
    url = f"{base_url}{endpoint_path}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:  # POST
            response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            try:
                return True, response.json()
            except json.JSONDecodeError:
                return True, response.text
        else:
            return False, f"Status code: {response.status_code}, Response: {response.text}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Main function to check Ollama endpoints"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:11434"
    
    print(f"Checking Ollama API endpoints at {base_url}")
    
    # Check various endpoints
    endpoints_to_check = [
        # Basic server info endpoints
        {"path": "/", "method": "GET", "description": "Root endpoint"},
        {"path": "/api/version", "method": "GET", "description": "Version endpoint"},
        {"path": "/api", "method": "GET", "description": "API root"},
        
        # OpenAI-compatible endpoints
        {"path": "/v1/models", "method": "GET", "description": "OpenAI-compatible models list"},
        {"path": "/v1/chat/completions", "method": "POST", 
         "payload": {"model": "llama3", "messages": [{"role": "user", "content": "Hello"}]},
         "description": "OpenAI-compatible chat completions"},
        {"path": "/v1/completions", "method": "POST", 
         "payload": {"model": "llama3", "prompt": "Hello"},
         "description": "OpenAI-compatible completions"},
        {"path": "/v1/embeddings", "method": "POST", 
         "payload": {"model": "llama3", "input": "Hello"},
         "description": "OpenAI-compatible embeddings"},
        
        # Ollama-specific endpoints
        {"path": "/api/generate", "method": "POST", 
         "payload": {"model": "llama3", "prompt": "Hello"},
         "description": "Ollama generate endpoint"},
        {"path": "/api/chat", "method": "POST", 
         "payload": {"model": "llama3", "messages": [{"role": "user", "content": "Hello"}]},
         "description": "Ollama chat endpoint"},
        {"path": "/api/embeddings", "method": "POST", 
         "payload": {"model": "llama3", "prompt": "Hello"},
         "description": "Ollama embeddings (prompt parameter)"},
        {"path": "/api/embeddings", "method": "POST", 
         "payload": {"model": "llama3", "input": "Hello"},
         "description": "Ollama embeddings (input parameter)"},
    ]
    
    working_endpoints = []
    not_working_endpoints = []
    
    for endpoint in endpoints_to_check:
        print(f"\nChecking {endpoint['description']}: {endpoint['method']} {endpoint['path']}")
        available, result = check_endpoint(
            base_url, 
            endpoint['path'], 
            endpoint['method'],
            endpoint.get('payload')
        )
        
        if available:
            print(f"✅ Available! Response: {result}")
            working_endpoints.append({
                "path": endpoint['path'],
                "method": endpoint['method'],
                "description": endpoint['description']
            })
        else:
            print(f"❌ Not available: {result}")
            not_working_endpoints.append({
                "path": endpoint['path'],
                "method": endpoint['method'],
                "description": endpoint['description'],
                "error": result
            })
    
    print("\n----- SUMMARY -----")
    print(f"Working endpoints ({len(working_endpoints)}):")
    for endpoint in working_endpoints:
        print(f"  • {endpoint['method']} {endpoint['path']} - {endpoint['description']}")
    
    print(f"\nNon-working endpoints ({len(not_working_endpoints)}):")
    for endpoint in not_working_endpoints:
        print(f"  • {endpoint['method']} {endpoint['path']} - {endpoint['description']}")
    
    if working_endpoints:
        print("\nBased on the available endpoints, update your utils/llm.py to use these working endpoints.")
    else:
        print("\nNo working endpoints found. Check if your Ollama server is running.")
    
    # Provide detailed recommendations
    recommended_changes = []
    if any(e['path'] == '/api/version' for e in working_endpoints):
        if any(e['path'] == '/v1/chat/completions' for e in working_endpoints):
            recommended_changes.append("Your Ollama version appears to support OpenAI-compatible endpoints.")
        elif any(e['path'] == '/api/chat' for e in working_endpoints):
            recommended_changes.append("Your Ollama version appears to use the legacy /api endpoints.")
    
    # Print recommendations
    if recommended_changes:
        print("\nRecommendations:")
        for i, rec in enumerate(recommended_changes, 1):
            print(f"{i}. {rec}")

if __name__ == "__main__":
    main()