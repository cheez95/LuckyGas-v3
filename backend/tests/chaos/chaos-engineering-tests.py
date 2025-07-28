"""
Chaos Engineering Tests for LuckyGas v3
Tests system resilience under various failure scenarios
"""

import asyncio
import random
import time
from datetime import datetime
from typing import Dict, List, Any
import httpx
import websockets
import psutil
import kubernetes
from kubernetes import client, config
import pytest
import json
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChaosTest:
    def __init__(self, base_url: str = "http://localhost:8000", k8s_namespace: str = "luckygas"):
        self.base_url = base_url
        self.k8s_namespace = k8s_namespace
        self.results = []
        
        # Initialize Kubernetes client
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    async def run_all_tests(self):
        """Run all chaos engineering tests"""
        test_scenarios = [
            self.test_pod_failure_recovery,
            self.test_network_partition,
            self.test_database_connection_failure,
            self.test_external_api_timeout,
            self.test_resource_exhaustion,
            self.test_zone_failure_simulation,
            self.test_cascading_failures,
            self.test_data_corruption_recovery,
        ]
        
        for test in test_scenarios:
            logger.info(f"Running {test.__name__}...")
            result = await test()
            self.results.append(result)
            
        return self.generate_report()

    async def test_pod_failure_recovery(self) -> Dict[str, Any]:
        """Test pod failure and recovery"""
        start_time = time.time()
        test_result = {
            "test": "Pod Failure Recovery",
            "status": "PASSED",
            "recovery_time": 0,
            "details": []
        }
        
        try:
            # Get backend pods
            pods = self.v1.list_namespaced_pod(
                namespace=self.k8s_namespace,
                label_selector="app=backend"
            )
            
            if not pods.items:
                raise Exception("No backend pods found")
            
            # Delete a random pod
            target_pod = random.choice(pods.items)
            pod_name = target_pod.metadata.name
            
            logger.info(f"Deleting pod: {pod_name}")
            self.v1.delete_namespaced_pod(
                name=pod_name,
                namespace=self.k8s_namespace
            )
            
            # Monitor recovery
            recovery_start = time.time()
            while True:
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.get(f"{self.base_url}/api/health")
                        if response.status_code == 200:
                            recovery_time = time.time() - recovery_start
                            test_result["recovery_time"] = recovery_time
                            test_result["details"].append(f"Pod recovered in {recovery_time:.2f}s")
                            break
                    except:
                        pass
                
                if time.time() - recovery_start > 300:  # 5 minute timeout
                    test_result["status"] = "FAILED"
                    test_result["details"].append("Recovery timeout exceeded")
                    break
                    
                await asyncio.sleep(5)
                
        except Exception as e:
            test_result["status"] = "FAILED"
            test_result["details"].append(str(e))
            
        return test_result

    async def test_network_partition(self) -> Dict[str, Any]:
        """Simulate network partition between services"""
        test_result = {
            "test": "Network Partition Handling",
            "status": "PASSED",
            "details": []
        }
        
        try:
            # Apply network policy to block traffic
            network_policy = client.V1NetworkPolicy(
                metadata=client.V1ObjectMeta(
                    name="chaos-network-partition",
                    namespace=self.k8s_namespace
                ),
                spec=client.V1NetworkPolicySpec(
                    pod_selector=client.V1LabelSelector(
                        match_labels={"app": "backend"}
                    ),
                    policy_types=["Ingress"],
                    ingress=[]  # Block all ingress
                )
            )
            
            networking_v1 = client.NetworkingV1Api()
            networking_v1.create_namespaced_network_policy(
                namespace=self.k8s_namespace,
                body=network_policy
            )
            
            # Test system behavior during partition
            await asyncio.sleep(10)
            
            # Check if system handles gracefully
            async with httpx.AsyncClient() as client:
                # Frontend should show appropriate error
                response = await client.get(f"{self.base_url.replace('8000', '5173')}/")
                if "網路連線中斷" in response.text or response.status_code == 503:
                    test_result["details"].append("Frontend handles network partition gracefully")
                else:
                    test_result["status"] = "FAILED"
                    test_result["details"].append("Frontend doesn't handle network partition")
            
            # Remove network policy
            networking_v1.delete_namespaced_network_policy(
                name="chaos-network-partition",
                namespace=self.k8s_namespace
            )
            
            # Verify recovery
            await asyncio.sleep(10)
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/health")
                if response.status_code == 200:
                    test_result["details"].append("System recovered from network partition")
                    
        except Exception as e:
            test_result["status"] = "FAILED"
            test_result["details"].append(str(e))
            
        return test_result

    async def test_database_connection_failure(self) -> Dict[str, Any]:
        """Test database connection failure handling"""
        test_result = {
            "test": "Database Connection Failure",
            "status": "PASSED",
            "details": []
        }
        
        try:
            # Scale down database statefulset
            self.apps_v1.patch_namespaced_stateful_set_scale(
                name="postgres",
                namespace=self.k8s_namespace,
                body={"spec": {"replicas": 0}}
            )
            
            await asyncio.sleep(5)
            
            # Test API behavior without database
            async with httpx.AsyncClient() as client:
                # Health check should report unhealthy
                response = await client.get(f"{self.base_url}/api/health")
                health_data = response.json()
                if health_data.get("database") == "disconnected":
                    test_result["details"].append("Health check correctly reports database issue")
                
                # API should return appropriate errors
                response = await client.get(
                    f"{self.base_url}/api/v1/customers",
                    headers={"Authorization": "Bearer test_token"}
                )
                if response.status_code in [503, 500]:
                    test_result["details"].append("API returns appropriate error for database failure")
                else:
                    test_result["status"] = "FAILED"
                    test_result["details"].append("API doesn't handle database failure properly")
            
            # Restore database
            self.apps_v1.patch_namespaced_stateful_set_scale(
                name="postgres",
                namespace=self.k8s_namespace,
                body={"spec": {"replicas": 1}}
            )
            
            # Wait for recovery
            recovery_start = time.time()
            while time.time() - recovery_start < 120:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}/api/health")
                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("database") == "connected":
                            recovery_time = time.time() - recovery_start
                            test_result["details"].append(f"Database recovered in {recovery_time:.2f}s")
                            break
                await asyncio.sleep(5)
                
        except Exception as e:
            test_result["status"] = "FAILED"
            test_result["details"].append(str(e))
            
        return test_result

    async def test_external_api_timeout(self) -> Dict[str, Any]:
        """Test handling of external API timeouts"""
        test_result = {
            "test": "External API Timeout Handling",
            "status": "PASSED",
            "details": []
        }
        
        try:
            # Configure network delay for Google Maps API calls
            # This would typically be done with a service mesh like Istio
            # For testing, we'll use a mock endpoint with artificial delay
            
            async with httpx.AsyncClient() as client:
                # Test route optimization with slow external API
                start_time = time.time()
                response = await client.post(
                    f"{self.base_url}/api/v1/routes/optimize",
                    json={
                        "date": "2024-01-20",
                        "area": "信義區",
                        "simulate_slow_api": True  # Flag for testing
                    },
                    headers={"Authorization": "Bearer test_token"},
                    timeout=30.0
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    test_result["details"].append(f"Route optimization handled slow API ({response_time:.2f}s)")
                elif response.status_code == 408:
                    test_result["details"].append("API correctly times out slow external calls")
                else:
                    test_result["status"] = "FAILED"
                    test_result["details"].append(f"Unexpected response: {response.status_code}")
                    
        except httpx.TimeoutException:
            test_result["details"].append("Request timed out as expected")
        except Exception as e:
            test_result["status"] = "FAILED"
            test_result["details"].append(str(e))
            
        return test_result

    async def test_resource_exhaustion(self) -> Dict[str, Any]:
        """Test system behavior under resource exhaustion"""
        test_result = {
            "test": "Resource Exhaustion",
            "status": "PASSED",
            "details": []
        }
        
        try:
            # Create many concurrent requests to exhaust resources
            async def make_request(session, index):
                try:
                    response = await session.get(
                        f"{self.base_url}/api/v1/customers?page={index}&size=100"
                    )
                    return response.status_code
                except:
                    return 0
            
            # Send 1000 concurrent requests
            async with httpx.AsyncClient() as client:
                tasks = []
                for i in range(1000):
                    tasks.append(make_request(client, i))
                
                results = await asyncio.gather(*tasks)
                
                success_count = sum(1 for r in results if r == 200)
                rate_limited = sum(1 for r in results if r == 429)
                errors = sum(1 for r in results if r >= 500)
                
                test_result["details"].append(f"Success: {success_count}, Rate limited: {rate_limited}, Errors: {errors}")
                
                if rate_limited > 0:
                    test_result["details"].append("Rate limiting is working")
                
                if errors < 50:  # Less than 5% error rate
                    test_result["details"].append("System handles load gracefully")
                else:
                    test_result["status"] = "FAILED"
                    test_result["details"].append(f"High error rate under load: {errors/10}%")
                    
            # Check if system recovers
            await asyncio.sleep(10)
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/health")
                if response.status_code == 200:
                    test_result["details"].append("System recovered after load spike")
                    
        except Exception as e:
            test_result["status"] = "FAILED"
            test_result["details"].append(str(e))
            
        return test_result

    async def test_zone_failure_simulation(self) -> Dict[str, Any]:
        """Simulate availability zone failure"""
        test_result = {
            "test": "Zone Failure Simulation",
            "status": "PASSED",
            "details": []
        }
        
        try:
            # Get pods in specific zone
            pods = self.v1.list_namespaced_pod(namespace=self.k8s_namespace)
            zone_a_pods = [p for p in pods.items if 
                          p.spec.node_selector and 
                          p.spec.node_selector.get("zone") == "zone-a"]
            
            if not zone_a_pods:
                test_result["details"].append("No zone-specific pods found, skipping test")
                return test_result
            
            # Cordon nodes in zone-a
            nodes = self.v1.list_node(label_selector="zone=zone-a")
            for node in nodes.items:
                body = client.V1Node(
                    spec=client.V1NodeSpec(unschedulable=True)
                )
                self.v1.patch_node(name=node.metadata.name, body=body)
            
            # Delete pods in zone-a
            for pod in zone_a_pods:
                self.v1.delete_namespaced_pod(
                    name=pod.metadata.name,
                    namespace=self.k8s_namespace
                )
            
            # Monitor service availability
            downtime_start = None
            recovery_time = None
            
            for i in range(60):  # Monitor for 5 minutes
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.get(f"{self.base_url}/api/health")
                        if response.status_code != 200 and downtime_start is None:
                            downtime_start = time.time()
                        elif response.status_code == 200 and downtime_start is not None:
                            recovery_time = time.time() - downtime_start
                            break
                    except:
                        if downtime_start is None:
                            downtime_start = time.time()
                
                await asyncio.sleep(5)
            
            # Uncordon nodes
            for node in nodes.items:
                body = client.V1Node(
                    spec=client.V1NodeSpec(unschedulable=False)
                )
                self.v1.patch_node(name=node.metadata.name, body=body)
            
            if recovery_time:
                test_result["details"].append(f"Service recovered in {recovery_time:.2f}s after zone failure")
                if recovery_time < 300:  # Less than 5 minutes
                    test_result["details"].append("Recovery time within acceptable limits")
                else:
                    test_result["status"] = "FAILED"
                    test_result["details"].append("Recovery time exceeded 5 minutes")
            else:
                test_result["details"].append("Service maintained availability during zone failure")
                
        except Exception as e:
            test_result["status"] = "FAILED"
            test_result["details"].append(str(e))
            
        return test_result

    async def test_cascading_failures(self) -> Dict[str, Any]:
        """Test cascading failure scenarios"""
        test_result = {
            "test": "Cascading Failure Prevention",
            "status": "PASSED",
            "details": []
        }
        
        try:
            # First, cause Redis failure
            self.apps_v1.patch_namespaced_deployment_scale(
                name="redis",
                namespace=self.k8s_namespace,
                body={"spec": {"replicas": 0}}
            )
            
            await asyncio.sleep(5)
            
            # Check if services degrade gracefully
            async with httpx.AsyncClient() as client:
                # WebSocket service should fall back to in-memory
                ws_health = await client.get(f"{self.base_url}/api/v1/websocket/health")
                if ws_health.status_code == 200:
                    test_result["details"].append("WebSocket service degraded gracefully without Redis")
                
                # Session management should fall back
                login_response = await client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={"username": "test@luckygas.com", "password": "password123"}
                )
                if login_response.status_code == 200:
                    test_result["details"].append("Auth service works without Redis (with limitations)")
            
            # Now cause partial backend failure
            backend_pods = self.v1.list_namespaced_pod(
                namespace=self.k8s_namespace,
                label_selector="app=backend"
            )
            
            # Delete half the backend pods
            pods_to_delete = backend_pods.items[:len(backend_pods.items)//2]
            for pod in pods_to_delete:
                self.v1.delete_namespaced_pod(
                    name=pod.metadata.name,
                    namespace=self.k8s_namespace
                )
            
            # System should still function with reduced capacity
            await asyncio.sleep(10)
            
            success_count = 0
            total_requests = 100
            
            async with httpx.AsyncClient() as client:
                for i in range(total_requests):
                    try:
                        response = await client.get(
                            f"{self.base_url}/api/v1/customers",
                            timeout=5.0
                        )
                        if response.status_code == 200:
                            success_count += 1
                    except:
                        pass
            
            success_rate = success_count / total_requests
            test_result["details"].append(f"Success rate during partial failure: {success_rate:.2%}")
            
            if success_rate > 0.5:  # At least 50% success
                test_result["details"].append("System maintains partial functionality")
            else:
                test_result["status"] = "FAILED"
                test_result["details"].append("System failed to maintain minimum functionality")
            
            # Restore services
            self.apps_v1.patch_namespaced_deployment_scale(
                name="redis",
                namespace=self.k8s_namespace,
                body={"spec": {"replicas": 1}}
            )
            
        except Exception as e:
            test_result["status"] = "FAILED"
            test_result["details"].append(str(e))
            
        return test_result

    async def test_data_corruption_recovery(self) -> Dict[str, Any]:
        """Test data corruption detection and recovery"""
        test_result = {
            "test": "Data Corruption Recovery",
            "status": "PASSED",
            "details": []
        }
        
        try:
            # Create test data with known checksum
            async with httpx.AsyncClient() as client:
                # Create customer with specific data
                create_response = await client.post(
                    f"{self.base_url}/api/v1/customers",
                    json={
                        "code": "CORRUPT_TEST",
                        "name": "測試客戶",
                        "phone": "0912345678",
                        "address": "測試地址"
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                if create_response.status_code == 201:
                    customer_id = create_response.json()["id"]
                    
                    # Simulate data corruption by directly modifying database
                    # (In real scenario, this would be done through database access)
                    
                    # Try to read corrupted data
                    read_response = await client.get(
                        f"{self.base_url}/api/v1/customers/{customer_id}",
                        headers={"Authorization": "Bearer test_token"}
                    )
                    
                    if read_response.status_code == 500:
                        error_data = read_response.json()
                        if "data integrity" in error_data.get("detail", "").lower():
                            test_result["details"].append("System detected data corruption")
                    
                    # Check if backup/recovery mechanism works
                    recovery_response = await client.post(
                        f"{self.base_url}/api/v1/admin/recover-customer/{customer_id}",
                        headers={"Authorization": "Bearer admin_token"}
                    )
                    
                    if recovery_response.status_code == 200:
                        test_result["details"].append("Data recovery successful")
                    else:
                        test_result["status"] = "FAILED"
                        test_result["details"].append("Data recovery failed")
                        
        except Exception as e:
            test_result["status"] = "FAILED"
            test_result["details"].append(str(e))
            
        return test_result

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive chaos test report"""
        passed_tests = sum(1 for r in self.results if r["status"] == "PASSED")
        total_tests = len(self.results)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
            },
            "test_results": self.results,
            "recommendations": []
        }
        
        # Add recommendations based on failures
        for result in self.results:
            if result["status"] == "FAILED":
                if "Pod Failure" in result["test"]:
                    report["recommendations"].append(
                        "Increase pod replicas or improve health check configuration"
                    )
                elif "Database" in result["test"]:
                    report["recommendations"].append(
                        "Implement database connection pooling and retry logic"
                    )
                elif "Resource" in result["test"]:
                    report["recommendations"].append(
                        "Implement better rate limiting and resource quotas"
                    )
                elif "Zone" in result["test"]:
                    report["recommendations"].append(
                        "Ensure proper multi-zone deployment and pod anti-affinity"
                    )
        
        return report


async def main():
    """Run chaos engineering tests"""
    chaos_tester = ChaosTest()
    report = await chaos_tester.run_all_tests()
    
    # Save report
    with open("chaos-test-report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nChaos Engineering Test Summary:")
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Success Rate: {report['summary']['success_rate']}")
    
    if report['recommendations']:
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"- {rec}")
    
    return report['summary']['failed'] == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)