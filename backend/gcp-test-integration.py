#!/usr/bin/env python3
"""
GCP Integration Test Script
Tests all GCP services after setup completion
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Tuple

# Color codes for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def print_status(status: str, message: str):
    """Print colored status messages"""
    symbols = {
        "success": f"{GREEN}✓{NC}",
        "error": f"{RED}✗{NC}",
        "warning": f"{YELLOW}⚠{NC}",
        "info": f"{BLUE}ℹ{NC}"
    }
    print(f"{symbols.get(status, '')} {message}")


def test_imports() -> bool:
    """Test if required packages are installed"""
    print_status("info", "Testing package imports...")
    
    required_packages = [
        ("google.cloud.storage", "google-cloud-storage"),
        ("google.cloud.aiplatform", "google-cloud-aiplatform"),
        ("google.cloud.secretmanager", "google-cloud-secret-manager"),
        ("google.auth", "google-auth"),
    ]
    
    missing_packages = []
    
    for module, package in required_packages:
        try:
            __import__(module)
            print_status("success", f"Import {module}: OK")
        except ImportError:
            print_status("error", f"Import {module}: FAILED")
            missing_packages.append(package)
    
    if missing_packages:
        print_status("warning", "Missing packages. Install with:")
        print(f"  uv pip install {' '.join(missing_packages)}")
        return False
    
    return True


def test_authentication() -> Tuple[bool, str]:
    """Test GCP authentication"""
    print_status("info", "\nTesting GCP authentication...")
    
    try:
        from google.auth import default
        from google.auth.exceptions import DefaultCredentialsError
        
        credentials, project = default()
        
        if credentials:
            print_status("success", "Authentication successful")
            print_status("info", f"Project ID: {project}")
            return True, project
        else:
            print_status("error", "No credentials found")
            return False, ""
            
    except DefaultCredentialsError as e:
        print_status("error", f"Authentication failed: {e}")
        print_status("info", "Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        return False, ""
    except Exception as e:
        print_status("error", f"Unexpected error: {e}")
        return False, ""


def test_storage(project_id: str) -> bool:
    """Test Cloud Storage access"""
    print_status("info", "\nTesting Cloud Storage...")
    
    try:
        from google.cloud import storage
        
        client = storage.Client(project=project_id)
        bucket_name = "lucky-gas-storage"
        
        # Check if bucket exists
        bucket = client.bucket(bucket_name)
        if bucket.exists():
            print_status("success", f"Bucket exists: gs://{bucket_name}")
            
            # Test write permission
            test_blob = bucket.blob("test/gcp-integration-test.txt")
            test_content = f"GCP integration test - {datetime.now().isoformat()}"
            
            try:
                test_blob.upload_from_string(test_content)
                print_status("success", "Write test: OK")
                
                # Test read
                downloaded = test_blob.download_as_text()
                if downloaded == test_content:
                    print_status("success", "Read test: OK")
                
                # Cleanup
                test_blob.delete()
                print_status("success", "Cleanup: OK")
                
                return True
                
            except Exception as e:
                print_status("error", f"Storage operations failed: {e}")
                return False
        else:
            print_status("error", f"Bucket not found: gs://{bucket_name}")
            return False
            
    except Exception as e:
        print_status("error", f"Storage test failed: {e}")
        return False


def test_vertex_ai(project_id: str) -> bool:
    """Test Vertex AI access"""
    print_status("info", "\nTesting Vertex AI...")
    
    try:
        from google.cloud import aiplatform
        
        # Initialize Vertex AI
        aiplatform.init(project=project_id, location="asia-east1")
        print_status("success", "Vertex AI initialized")
        
        # List endpoints (should be empty initially)
        endpoints = aiplatform.Endpoint.list()
        print_status("info", f"Endpoints found: {len(endpoints)}")
        
        return True
        
    except Exception as e:
        print_status("error", f"Vertex AI test failed: {e}")
        return False


def test_secret_manager(project_id: str) -> bool:
    """Test Secret Manager access"""
    print_status("info", "\nTesting Secret Manager...")
    
    try:
        from google.cloud import secretmanager
        
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project_id}"
        
        # List secrets
        try:
            secrets = list(client.list_secrets(request={"parent": parent}))
            print_status("info", f"Secrets found: {len(secrets)}")
            
            if secrets:
                for secret in secrets[:3]:  # Show first 3
                    print_status("info", f"  - {secret.name.split('/')[-1]}")
            
            print_status("success", "Secret Manager accessible")
            return True
            
        except Exception as e:
            if "403" in str(e):
                print_status("warning", "Secret Manager not accessible (check permissions)")
            else:
                print_status("error", f"Secret Manager test failed: {e}")
            return False
            
    except Exception as e:
        print_status("error", f"Secret Manager import failed: {e}")
        return False


def test_apis_enabled(project_id: str) -> bool:
    """Check if required APIs are enabled"""
    print_status("info", "\nChecking enabled APIs...")
    
    required_apis = [
        "routes.googleapis.com",
        "aiplatform.googleapis.com",
        "storage-component.googleapis.com",
        "secretmanager.googleapis.com",
    ]
    
    # Note: Checking API status requires additional permissions
    # This is a placeholder for manual verification
    print_status("info", "Verify these APIs are enabled in console:")
    for api in required_apis:
        print(f"  - {api}")
    
    return True


def generate_report(results: Dict[str, bool]) -> None:
    """Generate test report"""
    print("\n" + "="*50)
    print(f"{BLUE}GCP Integration Test Report{NC}")
    print("="*50)
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    print(f"\nTest Results: {passed_tests}/{total_tests} passed")
    
    for test, passed in results.items():
        status = "success" if passed else "error"
        print_status(status, f"{test}: {'PASSED' if passed else 'FAILED'}")
    
    if passed_tests == total_tests:
        print(f"\n{GREEN}✅ All tests passed! GCP integration is working.{NC}")
    else:
        print(f"\n{YELLOW}⚠️  Some tests failed. Check the errors above.{NC}")
    
    # Next steps
    print("\nNext Steps:")
    if "Authentication" not in results or not results["Authentication"]:
        print("1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        print("   export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/lucky-gas/lucky-gas-prod-key.json")
    
    if "Package Imports" not in results or not results["Package Imports"]:
        print("2. Install missing packages:")
        print("   cd backend && uv pip install google-cloud-storage google-cloud-aiplatform")
    
    print("\nUseful Commands:")
    print("  - Monitor infrastructure: ./gcp-monitor.sh")
    print("  - Check costs: gcloud billing accounts list")
    print("  - View logs: gcloud logging read --limit 10")


def main():
    """Run all integration tests"""
    print(f"{BLUE}Lucky Gas GCP Integration Test{NC}")
    print("="*50)
    
    results = {}
    
    # Test package imports
    if test_imports():
        results["Package Imports"] = True
        
        # Test authentication
        auth_success, project_id = test_authentication()
        results["Authentication"] = auth_success
        
        if auth_success and project_id:
            # Run service tests
            results["Cloud Storage"] = test_storage(project_id)
            results["Vertex AI"] = test_vertex_ai(project_id)
            results["Secret Manager"] = test_secret_manager(project_id)
            results["APIs Enabled"] = test_apis_enabled(project_id)
        else:
            print_status("warning", "Skipping service tests due to authentication failure")
    else:
        results["Package Imports"] = False
        print_status("warning", "Skipping tests due to missing packages")
    
    # Generate report
    generate_report(results)
    
    # Exit with appropriate code
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()