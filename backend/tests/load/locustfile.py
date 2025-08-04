"""
Load test scenarios for Lucky Gas API using Locust.

Run with:
    locust -f tests/load/locustfile.py --host http://localhost:8000
"""

import json
import random
from datetime import datetime, timedelta

from locust import HttpUser, SequentialTaskSet, TaskSet, between, task
from locust.exception import RescueTaskSet


class AuthenticatedUser:
    """Mixin for authenticated API requests."""

    def on_start(self):
        """Login and get access token."""
        response = self.client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
        )

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            self.headers = {}

    def on_stop(self):
        """Logout when stopping."""
        if hasattr(self, "headers") and self.headers:
            self.client.post("/api/v1/auth/logout", headers=self.headers)


class CustomerManagementTasks(TaskSet, AuthenticatedUser):
    """Customer management load test tasks."""

    def on_start(self):
        """Initialize with auth."""
        super().on_start()
        self.customer_ids = []

    @task(3)
    def list_customers(self):
        """List customers with pagination."""
        skip = random.randint(0, 100)
        limit = random.choice([10, 20, 50])

        with self.client.get(
            f"/api/v1/customers?skip={skip}&limit={limit}",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "items" in data:
                    self.customer_ids = [c["id"] for c in data["items"][:5]]
                    response.success()
                else:
                    response.failure("Invalid response format")
            else:
                response.failure(f"Status {response.status_code}")

    @task(2)
    def get_customer_detail(self):
        """Get specific customer details."""
        if not self.customer_ids:
            self.list_customers()
            return

        customer_id = random.choice(self.customer_ids)
        self.client.get(
            f"/api/v1/customers/{customer_id}",
            headers=self.headers,
            name="/api/v1/customers/[id]",
        )

    @task(1)
    def search_customers(self):
        """Search customers by query."""
        queries = ["張", "李", "王", "測試", "A-", "B-"]
        query = random.choice(queries)

        self.client.get(f"/api/v1/customers/search?q={query}", headers=self.headers)

    @task(1)
    def create_customer(self):
        """Create a new customer."""
        customer_data = {
            "customer_code": f"LOAD{random.randint(10000, 99999)}",
            "short_name": f"負載測試客戶{random.randint(1, 999)}",
            "full_name": f"負載測試有限公司{random.randint(1, 999)}",
            "invoice_title": f"負載測試公司{random.randint(1, 999)}",
            "unified_number": f"2{random.randint(1000000, 9999999)}",
            "phone": f"02-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            "mobile": f"09{random.randint(10000000, 99999999)}",
            "address": f"台北市測試區負載路{random.randint(1, 999)}號",
            "delivery_address": f"台北市測試區配送路{random.randint(1, 999)}號",
            "area": random.choice(["A-瑞光", "B-內湖", "C-南港", "D-信義"]),
            "delivery_time_start": "09:00",
            "delivery_time_end": "18:00",
            "contact_person": f"測試員{random.randint(1, 99)}",
            "avg_daily_usage": random.randint(5, 50),
            "max_cycle_days": random.randint(20, 40),
            "min_cycle_days": random.randint(10, 20),
            "can_delay_days": random.randint(1, 7),
            "credit_limit": random.randint(50000, 200000),
            "payment_method": random.choice(["cash", "transfer", "credit"]),
        }

        response = self.client.post(
            "/api/v1/customers", json=customer_data, headers=self.headers
        )

        if response.status_code == 201:
            new_customer = response.json()
            self.customer_ids.append(new_customer["id"])


class OrderManagementTasks(TaskSet, AuthenticatedUser):
    """Order management load test tasks."""

    def on_start(self):
        """Initialize with auth and get some customers."""
        super().on_start()
        # Get customer list
        response = self.client.get("/api/v1/customers?limit=50", headers=self.headers)
        if response.status_code == 200:
            self.customers = response.json()["items"]
        else:
            self.customers = []

    @task(3)
    def list_orders(self):
        """List orders with various filters."""
        params = {}

        # Random filters
        if random.random() > 0.5:
            params["status"] = random.choice(
                ["pending", "confirmed", "assigned", "delivering", "completed"]
            )

        if random.random() > 0.7:
            params["scheduled_date"] = datetime.now().date().isoformat()

        if random.random() > 0.8 and self.customers:
            params["customer_id"] = random.choice(self.customers)["id"]

        response = self.client.get(
            "/api/v1/orders", params=params, headers=self.headers
        )

    @task(2)
    def create_order(self):
        """Create a new order."""
        if not self.customers:
            return

        customer = random.choice(self.customers)

        # Random products
        products = []
        num_products = random.randint(1, 3)
        for _ in range(num_products):
            products.append(
                {
                    "gas_product_id": random.randint(1, 10),
                    "quantity": random.randint(1, 5),
                    "unit_price": random.randint(500, 2000),
                    "is_exchange": random.choice([True, False]),
                    "empty_received": (
                        random.randint(0, 5) if random.random() > 0.5 else 0
                    ),
                }
            )

        order_data = {
            "customer_id": customer["id"],
            "scheduled_date": (
                datetime.now() + timedelta(days=random.randint(1, 7))
            ).isoformat(),
            "priority": random.choice(["normal", "urgent", "scheduled"]),
            "payment_method": random.choice(["cash", "transfer", "credit"]),
            "products": products,
            "delivery_notes": "負載測試訂單" if random.random() > 0.7 else None,
        }

        self.client.post("/api/v1/orders", json=order_data, headers=self.headers)

    @task(1)
    def get_order_statistics(self):
        """Get order statistics."""
        self.client.get("/api/v1/orders/statistics/summary", headers=self.headers)


class RouteOptimizationTasks(TaskSet, AuthenticatedUser):
    """Route optimization load test tasks."""

    @task(2)
    def list_routes(self):
        """List routes for today."""
        self.client.get(
            f"/api/v1/routes?date={datetime.now().date().isoformat()}",
            headers=self.headers,
        )

    @task(1)
    def optimize_routes(self):
        """Request route optimization."""
        self.client.post(
            "/api/v1/routes/optimize",
            json={"date": datetime.now().date().isoformat(), "algorithm": "balanced"},
            headers=self.headers,
        )

    @task(1)
    def get_driver_routes(self):
        """Get routes for a specific driver."""
        driver_id = random.randint(1, 10)
        self.client.get(
            f"/api/v1/routes/driver/{driver_id}",
            headers=self.headers,
            name="/api/v1/routes/driver/[id]",
        )


class WebSocketTasks(TaskSet):
    """WebSocket connection tasks."""

    @task
    def connect_websocket(self):
        """Simulate WebSocket connection (placeholder)."""
        # Note: Locust doesn't natively support WebSocket
        # This is a placeholder for HTTP-based real-time endpoints
        self.client.get("/api/v1/notifications/stream", stream=True)


class MixedWorkloadUser(HttpUser):
    """User that performs mixed workload."""

    wait_time = between(1, 3)
    tasks = {
        CustomerManagementTasks: 3,
        OrderManagementTasks: 4,
        RouteOptimizationTasks: 2,
    }

    @task(1)
    def health_check(self):
        """Periodic health check."""
        self.client.get("/health")


class MobileDriverUser(HttpUser):
    """Mobile driver app user."""

    wait_time = between(2, 5)

    def on_start(self):
        """Login as driver."""
        response = self.client.post(
            "/api/v1/auth/login", json={"username": "driver1", "password": "driver123"}
        )

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

    @task(3)
    def get_my_routes(self):
        """Get driver's assigned routes."""
        self.client.get("/api/v1/driver/routes/today", headers=self.headers)

    @task(2)
    def update_delivery_status(self):
        """Update delivery status."""
        order_id = random.randint(1, 1000)
        status_update = {
            "status": random.choice(["delivering", "completed", "failed"]),
            "notes": "負載測試更新",
            "gps_lat": 25.0330 + random.uniform(-0.01, 0.01),
            "gps_lng": 121.5654 + random.uniform(-0.01, 0.01),
        }

        self.client.put(
            f"/api/v1/orders/{order_id}/status",
            json=status_update,
            headers=self.headers,
            name="/api/v1/orders/[id]/status",
        )

    @task(1)
    def upload_signature(self):
        """Upload delivery signature."""
        order_id = random.randint(1, 1000)
        # Simulate signature upload (would be base64 in real scenario)
        signature_data = {
            "signature": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            "recipient_name": f"收件人{random.randint(1, 99)}",
        }

        self.client.post(
            f"/api/v1/orders/{order_id}/signature",
            json=signature_data,
            headers=self.headers,
            name="/api/v1/orders/[id]/signature",
        )


class AdminDashboardUser(HttpUser):
    """Admin dashboard user."""

    wait_time = between(5, 10)

    def on_start(self):
        """Login as admin."""
        response = self.client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
        )

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

    @task(2)
    def view_dashboard_stats(self):
        """View dashboard statistics."""
        # Multiple parallel requests like a real dashboard
        self.client.get("/api/v1/orders/statistics/summary", headers=self.headers)
        self.client.get("/api/v1/customers/statistics", headers=self.headers)
        self.client.get("/api/v1/routes/statistics", headers=self.headers)

    @task(1)
    def generate_report(self):
        """Generate various reports."""
        report_type = random.choice(["daily", "weekly", "monthly"])
        start_date = (datetime.now() - timedelta(days=30)).date().isoformat()
        end_date = datetime.now().date().isoformat()

        self.client.get(
            f"/api/v1/reports/{report_type}",
            params={"start_date": start_date, "end_date": end_date},
            headers=self.headers,
            name=f"/api/v1/reports/[type]",
        )

    @task(1)
    def export_data(self):
        """Export data in various formats."""
        export_type = random.choice(["customers", "orders", "routes"])
        format_type = random.choice(["csv", "excel"])

        self.client.get(
            f"/api/v1/export/{export_type}",
            params={"format": format_type},
            headers=self.headers,
            name=f"/api/v1/export/[type]",
        )
