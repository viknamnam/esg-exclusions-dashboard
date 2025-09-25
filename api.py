# test_api.py - Test script for FET Risk API
import requests
import json
import time
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"  # Change to your deployed URL
API_KEY = "your-secret-key-here"  # Change to your actual API key


class FETAPITester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        print("🏥 Testing health check...")
        try:
            response = requests.get(f"{self.base_url}/health")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed")
                print(f"   Status: {data['status']}")
                print(f"   Database loaded: {data['database_loaded']}")
                print(f"   Total companies: {data['total_companies']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    def test_single_assessment(self, company_name: str = "BP plc") -> Dict[str, Any]:
        """Test single company risk assessment"""
        print(f"🏢 Testing single assessment for '{company_name}'...")

        try:
            # Test GET endpoint (simple)
            response = requests.get(
                f"{self.base_url}/api/v1/company/{company_name}/risk",
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Single assessment successful")
                print(f"   Company: {data['company_name']}")
                print(f"   Matched: {data.get('matched_company', 'N/A')}")
                print(f"   Risk Level: {data['risk_level']}")
                print(f"   Risk Score: {data['risk_score']}/100")
                print(f"   Recommendation: {data['recommendation']}")
                return data
            else:
                print(f"❌ Single assessment failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return {}

        except Exception as e:
            print(f"❌ Single assessment error: {e}")
            return {}

    def test_detailed_assessment(self, company_name: str = "Shell") -> Dict[str, Any]:
        """Test detailed assessment with POST endpoint"""
        print(f"📊 Testing detailed assessment for '{company_name}'...")

        try:
            payload = {
                "company_name": company_name,
                "include_details": True
            }

            response = requests.post(
                f"{self.base_url}/api/v1/risk-assessment",
                headers=self.headers,
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                risk = data['risk_assessment']
                print(f"✅ Detailed assessment successful")
                print(f"   Company: {risk['company_name']}")
                print(f"   Matched: {risk.get('matched_company', 'N/A')}")
                print(f"   Risk Level: {risk['risk_level']}")
                print(f"   Risk Score: {risk['risk_score']}/100")
                print(f"   Consensus: {risk['consensus_strength']}")
                print(f"   Exclusions: {risk['total_exclusions']}")

                if data.get('exclusion_details'):
                    print(f"   Details included: {len(data['exclusion_details'])} records")

                return data
            else:
                print(f"❌ Detailed assessment failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return {}

        except Exception as e:
            print(f"❌ Detailed assessment error: {e}")
            return {}

    def test_batch_assessment(self, companies: list = None) -> Dict[str, Any]:
        """Test batch assessment"""
        if companies is None:
            companies = ["BP", "Shell", "Tesla", "Apple", "Microsoft"]

        print(f"📦 Testing batch assessment for {len(companies)} companies...")

        try:
            payload = {
                "companies": companies,
                "include_details": False
            }

            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/v1/batch-risk-assessment",
                headers=self.headers,
                json=payload
            )
            end_time = time.time()

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Batch assessment successful")
                print(f"   Total processed: {data['total_processed']}")
                print(f"   API processing time: {data['processing_time_seconds']:.2f}s")
                print(f"   Total request time: {end_time - start_time:.2f}s")

                # Show summary by risk level
                risk_summary = {}
                for result in data['results']:
                    risk_level = result['risk_level']
                    risk_summary[risk_level] = risk_summary.get(risk_level, 0) + 1

                print("   Risk Level Summary:")
                for level, count in risk_summary.items():
                    print(f"     {level}: {count} companies")

                return data
            else:
                print(f"❌ Batch assessment failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return {}

        except Exception as e:
            print(f"❌ Batch assessment error: {e}")
            return {}

    def test_company_search(self, search_term: str = "Shell") -> list:
        """Test company search functionality"""
        print(f"🔍 Testing company search for '{search_term}'...")

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/search/{search_term}",
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                print(f"✅ Search successful")
                print(f"   Found {len(matches)} matches:")
                for i, match in enumerate(matches[:5], 1):  # Show first 5
                    print(f"     {i}. {match}")

                if len(matches) > 5:
                    print(f"     ... and {len(matches) - 5} more")

                return matches
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return []

        except Exception as e:
            print(f"❌ Search error: {e}")
            return []

    def test_authentication(self):
        """Test authentication by making request with wrong API key"""
        print("🔐 Testing authentication...")

        wrong_headers = {
            "Authorization": "Bearer wrong-api-key",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/company/Test/risk",
                headers=wrong_headers
            )

            if response.status_code == 401:
                print("✅ Authentication working - correctly rejected invalid API key")
                return True
            else:
                print(f"❌ Authentication issue - expected 401, got {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Authentication test error: {e}")
            return False

    def run_full_test_suite(self):
        """Run all tests"""
        print("🚀 Starting FET Risk API Test Suite")
        print("=" * 50)

        results = {
            'health_check': self.test_health_check(),
            'authentication': self.test_authentication(),
            'single_assessment': bool(self.test_single_assessment()),
            'detailed_assessment': bool(self.test_detailed_assessment()),
            'batch_assessment': bool(self.test_batch_assessment()),
            'company_search': bool(self.test_company_search())
        }

        print("\n" + "=" * 50)
        print("📋 Test Results Summary:")

        passed = 0
        total = len(results)

        for test_name, passed_test in results.items():
            status = "✅ PASS" if passed_test else "❌ FAIL"
            print(f"   {test_name}: {status}")
            if passed_test:
                passed += 1

        print(f"\n🏆 Overall: {passed}/{total} tests passed ({passed / total * 100:.1f}%)")

        if passed == total:
            print("🎉 All tests passed! API is ready for Salesforce integration.")
        else:
            print("⚠️  Some tests failed. Check the issues above before deploying.")

        return results


def main():
    """Main test function"""
    print("FET Risk API Tester")
    print("Please ensure your API is running before starting tests.")
    print(f"API URL: {API_BASE_URL}")

    # Check if user wants to continue
    response = input("\nPress Enter to start testing, or Ctrl+C to exit: ")

    tester = FETAPITester(API_BASE_URL, API_KEY)
    results = tester.run_full_test_suite()

    return results


if __name__ == "__main__":
    main()

# Example usage for individual tests:
"""
tester = FETAPITester("http://localhost:8000", "your-api-key")

# Test individual endpoints
tester.test_health_check()
tester.test_single_assessment("BP plc")
tester.test_batch_assessment(["Shell", "BP", "Tesla"])
tester.test_company_search("Shell")

# Or run full suite
results = tester.run_full_test_suite()
"""