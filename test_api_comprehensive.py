#!/usr/bin/env python3
"""
Comprehensive API Test Suite for Vigilis Pharmacy Backend
Tests all CRUD operations, audit logging, and business logic
"""

import requests
import json
from uuid import uuid4
from typing import Dict, Any, List
import time

BASE_URL = "http://127.0.0.1:8000"

class APITester:
    def __init__(self):
        self.admin_token = None
        self.cashier_token = None
        self.sales_token = None
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, details: str = "", data: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "data": data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def register_users(self):
        """Register test users"""
        print("\n=== Registering Test Users ===")
        
        # Admin user
        admin_data = {
            "username": f"admin_test_{uuid4().hex[:8]}",
            "email": f"admin_test_{uuid4().hex[:8]}@test.com",
            "password": "test123456",
            "full_name": "Test Admin",
            "role": "ADMIN"
        }
        
        response = requests.post(f"{BASE_URL}/auth/register", json=admin_data)
        self.log_result(
            "Admin Registration",
            response.status_code == 201,
            f"Status: {response.status_code}",
            admin_data
        )
        
        # Cashier user
        cashier_data = {
            "username": f"cashier_test_{uuid4().hex[:8]}",
            "email": f"cashier_test_{uuid4().hex[:8]}@test.com",
            "password": "test123456",
            "full_name": "Test Cashier",
            "role": "CASHIER"
        }
        
        response = requests.post(f"{BASE_URL}/auth/register", json=cashier_data)
        self.log_result(
            "Cashier Registration",
            response.status_code == 201,
            f"Status: {response.status_code}",
            cashier_data
        )
        
        # Login and get tokens
        admin_login = requests.post(f"{BASE_URL}/auth/login", json={
            "identifier": admin_data["username"],
            "password": admin_data["password"]
        })
        
        if admin_login.status_code == 200:
            self.admin_token = admin_login.json()["access_token"]
            
        cashier_login = requests.post(f"{BASE_URL}/auth/login", json={
            "identifier": cashier_data["username"],
            "password": cashier_data["password"]
        })
        
        if cashier_login.status_code == 200:
            self.cashier_token = cashier_login.json()["access_token"]
            
    def get_headers(self, token: str) -> Dict[str, str]:
        """Get auth headers"""
        return {"Authorization": f"Bearer {token}"}
        
    def test_products(self):
        """Test product CRUD operations"""
        print("\n=== Testing Products ===")
        
        # Create product
        product_data = {
            "name": f"Test Product {uuid4().hex[:8]}",
            "description": "Test product for API testing",
            "quantity_on_hand": 100
        }
        
        response = requests.post(
            f"{BASE_URL}/products/",
            json=product_data,
            headers=self.get_headers(self.admin_token)
        )
        
        self.log_result(
            "Create Product",
            response.status_code == 200,
            f"Status: {response.status_code}",
            product_data
        )
        
        if response.status_code != 200:
            return None
            
        product = response.json()
        product_id = product["id"]
        
        # Get product
        response = requests.get(
            f"{BASE_URL}/products/{product_id}",
            headers=self.get_headers(self.cashier_token)
        )
        
        self.log_result(
            "Get Product",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # List products
        response = requests.get(
            f"{BASE_URL}/products/",
            headers=self.get_headers(self.cashier_token)
        )
        
        self.log_result(
            "List Products",
            response.status_code == 200,
            f"Status: {response.status_code}, Count: {len(response.json())}"
        )
        
        # Adjust stock
        stock_data = {
            "change_qty": -10,
            "reason": "MANUAL_ADJUSTMENT",
            "note": "API test stock adjustment"
        }
        
        response = requests.post(
            f"{BASE_URL}/products/{product_id}/adjust-stock",
            json=stock_data,
            headers=self.get_headers(self.admin_token)
        )
        
        self.log_result(
            "Adjust Stock",
            response.status_code == 200,
            f"Status: {response.status_code}",
            stock_data
        )
        
        return product_id
        
    def test_invoices(self, product_id: str):
        """Test invoice operations"""
        print("\n=== Testing Invoices ===")
        
        # Create invoice
        invoice_data = {
            "sold_by_id": self.admin_token,  # Using admin ID as sold_by
            "customer_name": "Test Customer"
        }
        
        response = requests.post(
            f"{BASE_URL}/invoices/",
            json=invoice_data,
            headers=self.get_headers(self.cashier_token)
        )
        
        self.log_result(
            "Create Invoice",
            response.status_code == 200,
            f"Status: {response.status_code}",
            invoice_data
        )
        
        if response.status_code != 200:
            return None
            
        invoice = response.json()
        invoice_id = invoice["id"]
        
        # Add item to invoice
        # First get product units
        response = requests.get(
            f"{BASE_URL}/products/{product_id}/units",
            headers=self.get_headers(self.cashier_token)
        )
        
        if response.status_code != 200:
            self.log_result("Get Product Units", False, f"Status: {response.status_code}")
            return None
            
        units = response.json()
        if not units:
            self.log_result("No Product Units", False, "Product has no units")
            return None
            
        unit = units[0]
        
        item_data = {
            "product_id": product_id,
            "product_unit_id": unit["id"],
            "quantity": 2,
            "unit_price": 50.0
        }
        
        response = requests.post(
            f"{BASE_URL}/invoices/{invoice_id}/items",
            json=item_data,
            headers=self.get_headers(self.cashier_token)
        )
        
        self.log_result(
            "Add Invoice Item",
            response.status_code == 200,
            f"Status: {response.status_code}",
            item_data
        )
        
        # Finalize invoice
        response = requests.post(
            f"{BASE_URL}/invoices/{invoice_id}/finalize",
            headers=self.get_headers(self.cashier_token)
        )
        
        self.log_result(
            "Finalize Invoice",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # List invoices
        response = requests.get(
            f"{BASE_URL}/invoices/all",
            headers=self.get_headers(self.cashier_token)
        )
        
        self.log_result(
            "List Invoices",
            response.status_code == 200,
            f"Status: {response.status_code}, Count: {len(response.json())}"
        )
        
        return invoice_id
        
    def test_audit_logs(self):
        """Test audit log access"""
        print("\n=== Testing Audit Logs ===")
        
        response = requests.get(
            f"{BASE_URL}/admin/audit-logs",
            headers=self.get_headers(self.admin_token)
        )
        
        self.log_result(
            "Get Audit Logs",
            response.status_code == 200,
            f"Status: {response.status_code}, Count: {len(response.json().get('logs', []))}"
        )
        
        # Test filtering
        response = requests.get(
            f"{BASE_URL}/admin/audit-logs?action=CREATE&resource_type=PRODUCT",
            headers=self.get_headers(self.admin_token)
        )
        
        self.log_result(
            "Filtered Audit Logs",
            response.status_code == 200,
            f"Status: {response.status_code}, Filtered count: {len(response.json().get('logs', []))}"
        )
        
    def test_permissions(self):
        """Test role-based permissions"""
        print("\n=== Testing Permissions ===")
        
        # Test cashier trying to access admin endpoints
        response = requests.get(
            f"{BASE_URL}/admin/audit-logs",
            headers=self.get_headers(self.cashier_token)
        )
        
        self.log_result(
            "Cashier Access to Admin Logs",
            response.status_code == 403,
            f"Status: {response.status_code} (should be 403)"
        )
        
        # Test non-admin trying to create product
        response = requests.post(
            f"{BASE_URL}/products/",
            json={"name": "Test", "quantity_on_hand": 10},
            headers=self.get_headers(self.cashier_token)
        )
        
        self.log_result(
            "Cashier Create Product",
            response.status_code == 403,
            f"Status: {response.status_code} (should be 403)"
        )
        
    def test_error_cases(self):
        """Test error handling"""
        print("\n=== Testing Error Cases ===")
        
        # Test invalid login
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "identifier": "nonexistent",
            "password": "wrong"
        })
        
        self.log_result(
            "Invalid Login",
            response.status_code == 401,
            f"Status: {response.status_code} (should be 401)"
        )
        
        # Test creating invoice with insufficient stock
        # First create a product with low stock
        product_data = {
            "name": f"Low Stock Product {uuid4().hex[:8]}",
            "description": "Low stock test product",
            "quantity_on_hand": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/products/",
            json=product_data,
            headers=self.get_headers(self.admin_token)
        )
        
        if response.status_code == 200:
            product_id = response.json()["id"]
            
            # Create invoice
            invoice_data = {"sold_by_id": self.admin_token}
            response = requests.post(
                f"{BASE_URL}/invoices/",
                json=invoice_data,
                headers=self.get_headers(self.cashier_token)
            )
            
            if response.status_code == 200:
                invoice_id = response.json()["id"]
                
                # Get product units
                response = requests.get(f"{BASE_URL}/products/{product_id}/units")
                if response.status_code == 200 and response.json():
                    unit = response.json()[0]
                    
                    # Try to add more items than available stock
                    item_data = {
                        "product_id": product_id,
                        "product_unit_id": unit["id"],
                        "quantity": 10,  # More than available
                        "unit_price": 50.0
                    }
                    
                    response = requests.post(
                        f"{BASE_URL}/invoices/{invoice_id}/items",
                        json=item_data,
                        headers=self.get_headers(self.cashier_token)
                    )
                    
                    # Try to finalize - should fail due to insufficient stock
                    response = requests.post(
                        f"{BASE_URL}/invoices/{invoice_id}/finalize",
                        headers=self.get_headers(self.cashier_token)
                    )
                    
                    self.log_result(
                        "Finalize with Insufficient Stock",
                        response.status_code == 400,
                        f"Status: {response.status_code} (should be 400)"
                    )
        
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🧪 Starting Comprehensive API Test Suite")
        print("=" * 50)
        
        # Wait for server to be ready
        time.sleep(2)
        
        # Check server health
        try:
            response = requests.get(f"{BASE_URL}/docs")
            if response.status_code != 200:
                print("❌ Server not ready - cannot run tests")
                return
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server - make sure it's running")
            return
            
        print("✅ Server is ready")
        
        # Register users
        self.register_users()
        
        if not self.admin_token or not self.cashier_token:
            print("❌ Failed to register/login users")
            return
            
        # Test products
        product_id = self.test_products()
        
        # Test invoices
        if product_id:
            self.test_invoices(product_id)
            
        # Test audit logs
        self.test_audit_logs()
        
        # Test permissions
        self.test_permissions()
        
        # Test error cases
        self.test_error_cases()
        
        # Generate report
        self.generate_report()
        
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 50)
        print("📊 TEST REPORT")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
                    
        print("\n🎯 All tests completed!")
        
        # Save detailed report
        report_data = {
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
            },
            "tests": self.test_results
        }
        
        with open("api_test_report.json", "w") as f:
            json.dump(report_data, f, indent=2)
            
        print("📄 Detailed report saved to: api_test_report.json")

if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()
