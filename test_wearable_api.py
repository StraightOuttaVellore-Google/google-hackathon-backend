#!/usr/bin/env python3
"""
Test script for Wearable API endpoints
Run this to verify all wearable endpoints are working
"""

import requests
import json
import sys
from datetime import datetime, date

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    "username": "testuser",
    "email": "test@example.com", 
    "password": "testpass123"
}

def test_endpoint(method, endpoint, data=None, headers=None, expected_status=200):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        
        status_ok = response.status_code == expected_status
        status_icon = "✅" if status_ok else "❌"
        
        print(f"{status_icon} {method} {endpoint} - Status: {response.status_code}")
        
        if not status_ok:
            print(f"   Expected: {expected_status}, Got: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        
        return response, status_ok
        
    except requests.exceptions.ConnectionError:
        print(f"❌ {method} {endpoint} - Connection Error (Server not running?)")
        return None, False
    except Exception as e:
        print(f"❌ {method} {endpoint} - Error: {str(e)}")
        return None, False

def main():
    print("🧪 Testing Wearable API Endpoints")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1. 🏥 Health Check")
    test_endpoint("GET", "/health-de1f4b3133627b2cacac9aad5ddfe07c")
    
    # Test 2: User Registration (for authentication)
    print("\n2. 👤 User Registration")
    response, success = test_endpoint("POST", "/auth/signup", TEST_USER, expected_status=201)
    
    if not success:
        print("   ⚠️  User might already exist, trying login...")
        login_data = {"username": TEST_USER["username"], "password": TEST_USER["password"]}
        response, success = test_endpoint("POST", "/auth/login", login_data)
    
    # Get auth token
    auth_token = None
    if success and response:
        try:
            token_data = response.json()
            auth_token = token_data.get("access_token")
            print(f"   ✅ Auth token obtained: {auth_token[:20]}...")
        except:
            print("   ❌ Could not get auth token")
    
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    
    # Test 3: Register Wearable Device
    print("\n3. ⌚ Register Wearable Device")
    device_data = {
        "device_type": "smart_watch",
        "device_name": "Test Apple Watch Series 9",
        "device_id": "test_device_001"
    }
    response, success = test_endpoint("POST", "/wearable/devices", device_data, headers, 201)
    
    # Test 4: Get User Devices
    print("\n4. 📱 Get User Devices")
    test_endpoint("GET", "/wearable/devices", headers=headers)
    
    # Test 5: Generate Mock Data
    print("\n5. 🎭 Generate Mock Wearable Data")
    today = date.today().isoformat()
    test_endpoint("POST", f"/wearable/mock-data/{today}", headers=headers, expected_status=201)
    
    # Test 6: Get Wearable Data
    print("\n6. 📊 Get Wearable Data")
    test_endpoint("GET", f"/wearable/data/{today}", headers=headers)
    
    # Test 7: Get Recovery Score
    print("\n7. 💪 Get Recovery Score")
    test_endpoint("GET", "/wearable/recovery-score", headers=headers)
    
    # Test 8: AI Analysis
    print("\n8. 🤖 AI Analysis")
    analysis_data = {
        "data_date": today,
        "analysis_type": "comprehensive",
        "include_recommendations": True
    }
    test_endpoint("POST", "/wearable/ai/analyze", analysis_data, headers, 201)
    
    # Test 9: Get AI Insights
    print("\n9. 🧠 Get AI Insights")
    test_endpoint("GET", f"/wearable/insights/{today}", headers=headers)
    
    # Test 10: Get AI Recommendations
    print("\n10. 💡 Get AI Recommendations")
    test_endpoint("GET", "/wearable/ai/recommendations", headers=headers)
    
    print("\n" + "=" * 50)
    print("🎉 Wearable API Testing Complete!")
    print("\n📝 Next Steps:")
    print("   1. Check the frontend at http://localhost:5173")
    print("   2. Navigate to Wellness section")
    print("   3. Click on 'Wearable Insights' card")
    print("   4. Verify data is displayed correctly")

if __name__ == "__main__":
    main()
