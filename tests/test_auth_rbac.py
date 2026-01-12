#!/usr/bin/env python3
"""
Test script for authentication and role-based access control.
Run with: uv run python tests/test_auth_rbac.py
"""

import json
import requests
from typing import Dict

BASE_URL = "http://127.0.0.1:8000"

class AuthTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.tokens: Dict[str, str] = {}
        self.users: Dict[str, Dict] = {}

    def register_user(self, username: str, email: str, role: str, password: str = "test12345"):
        """Register a new user"""
        response = requests.post(
            f"{self.base_url}/auth/register",
            json={
                "username": username,
                "email": email,
                "full_name": f"{role} User",
                "password": password,
                "role": role
            }
        )
        if response.status_code == 201:
            self.users[role.lower()] = {"username": username, "password": password}
            print(f"✅ Registered {role} user: {username}")
            return response.json()
        elif response.status_code == 400 and "already registered" in response.text:
            # User already exists, just store credentials
            self.users[role.lower()] = {"username": username, "password": password}
            print(f"✅ {role} user already exists: {username}")
            return None
        else:
            print(f"❌ Failed to register {role}: {response.text}")
            return None

    def login(self, role: str) -> str | None:
        """Login and return token"""
        if role.lower() not in self.users:
            print(f"❌ No {role} user registered")
            return None
        
        user = self.users[role.lower()]
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={
                "identifier": user["username"],
                "password": user["password"]
            }
        )
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.tokens[role.lower()] = token
            print(f"✅ {role} logged in successfully")
            return token
        else:
            print(f"❌ {role} login failed: {response.text}")
            return None

    def get_headers(self, role: str) -> Dict[str, str]:
        """Get auth headers for a role"""
        token = self.tokens.get(role.lower())
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def test_endpoint(self, method: str, path: str, role: str, expected_status: int, json_data: Dict = None):
        """Test an endpoint with a specific role"""
        headers = self.get_headers(role)
        url = f"{self.base_url}{path}"
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data or {})
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=json_data or {})
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        
        status = "✅" if response.status_code == expected_status else "❌"
        print(f"{status} {role} {method} {path}: {response.status_code} (expected {expected_status})")
        
        if response.status_code != expected_status:
            print(f"   Response: {response.text[:200]}")
        
        return response.status_code == expected_status

    def run_all_tests(self):
        """Run comprehensive auth and RBAC tests"""
        print("\n🚀 Starting Auth & RBAC Tests\n")
        
        # 1. Register users
        print("1. Registering users...")
        self.register_user("admin", "admin@vigilis.ph", "ADMIN")
        self.register_user("cashier", "cashier@vigilis.ph", "CASHIER")
        self.register_user("sales", "sales@vigilis.ph", "SALES")
        
        # 2. Login users
        print("\n2. Testing login...")
        for role in ["ADMIN", "CASHIER", "SALES"]:
            self.login(role)
        
        # 3. Test auth endpoints
        print("\n3. Testing auth endpoints...")
        self.test_endpoint("GET", "/auth/me", "ADMIN", 200)
        self.test_endpoint("GET", "/auth/me", "CASHIER", 200)
        self.test_endpoint("GET", "/auth/me", "SALES", 200)
        self.test_endpoint("GET", "/auth/me", "UNAUTHORIZED", 401)  # No token
        
        # 4. Test product permissions
        print("\n4. Testing product permissions...")
        
        # Create unique products for each test
        import uuid
        product_id = str(uuid.uuid4())[:8]
        product_data = {
            "sku": f"TEST{product_id}",
            "name": f"Test Product {product_id}",
            "brand_name": "Test Brand",
            "category": "Test Category",
            "quantity_on_hand": 100,
            "reorder_level": 10
        }
        
        self.test_endpoint("POST", "/products/", "ADMIN", 200, product_data)
        self.test_endpoint("POST", "/products/", "CASHIER", 403, product_data)
        self.test_endpoint("POST", "/products/", "SALES", 403, product_data)
        
        # Read products
        self.test_endpoint("GET", "/products/", "ADMIN", 200)
        self.test_endpoint("GET", "/products/", "CASHIER", 200)
        self.test_endpoint("GET", "/products/", "SALES", 200)
        
        # 5. Test invoice permissions
        print("\n5. Testing invoice permissions...")
        
        invoice_data = {
            "sold_by_name": "Test User"
        }
        
        # Create invoice
        self.test_endpoint("POST", "/invoices/", "ADMIN", 200, invoice_data)
        self.test_endpoint("POST", "/invoices/", "CASHIER", 200, invoice_data)
        self.test_endpoint("POST", "/invoices/", "SALES", 200, invoice_data)
        
        # List invoices
        self.test_endpoint("GET", "/invoices/all", "ADMIN", 200)
        self.test_endpoint("GET", "/invoices/all", "CASHIER", 200)
        self.test_endpoint("GET", "/invoices/all", "SALES", 403)  # SALES can't list all
        
        # 6. Test stock adjustment
        print("\n6. Testing stock adjustment...")
        stock_data = {"change_qty": 5, "reason": "MANUAL_ADJUSTMENT"}
        
        # Get the first product ID for stock adjustment
        response = requests.get(f"{self.base_url}/products/", headers=self.get_headers("ADMIN"))
        if response.status_code == 200:
            products = response.json()
            if products:
                product_id = products[0]["id"]
                self.test_endpoint("POST", f"/products/{product_id}/adjust-stock", "ADMIN", 200, stock_data)
                self.test_endpoint("POST", f"/products/{product_id}/adjust-stock", "CASHIER", 200, stock_data)
                self.test_endpoint("POST", f"/products/{product_id}/adjust-stock", "SALES", 403, stock_data)
            else:
                print("❌ No products found for stock adjustment test")
        else:
            print("❌ Failed to fetch products for stock adjustment test")
        
        # 7. Test product deletion
        print("\n7. Testing product deletion...")
        # Create a new product specifically for deletion test
        delete_product_id = str(uuid.uuid4())[:8]
        delete_product_data = {
            "sku": f"DEL{delete_product_id}",
            "name": f"Delete Product {delete_product_id}",
            "brand_name": "Test Brand",
            "category": "Test Category",
            "quantity_on_hand": 50,
            "reorder_level": 5
        }
        
        # Create the product first
        create_response = requests.post(
            f"{self.base_url}/products/",
            headers=self.get_headers("ADMIN"),
            json=delete_product_data
        )
        
        if create_response.status_code == 200:
            created_product = create_response.json()
            product_id = created_product["id"]
            
            # Test deletion
            self.test_endpoint("DELETE", f"/products/{product_id}", "ADMIN", 200)
            self.test_endpoint("DELETE", f"/products/{product_id}", "CASHIER", 403)  # Should be 403 (permissions checked before existence)
            self.test_endpoint("DELETE", f"/products/{product_id}", "SALES", 403)   # Should be 403 (permissions checked before existence)
        else:
            print("❌ Failed to create product for deletion test")
        
        print("\n✅ All tests completed!")

if __name__ == "__main__":
    tester = AuthTester()
    tester.run_all_tests()
