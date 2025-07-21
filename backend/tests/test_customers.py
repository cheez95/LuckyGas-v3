"""
Tests for customer endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.gas_product import GasProduct, CylinderType
from app.models.customer_inventory import CustomerInventory


class TestCustomers:
    """Test customer endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_customer(self, client: AsyncClient, auth_headers: dict, sample_customer_data: dict):
        """Test creating a new customer"""
        response = await client.post(
            "/api/v1/customers",
            json=sample_customer_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["customer_code"] == sample_customer_data["customer_code"]
        assert data["short_name"] == sample_customer_data["short_name"]
        assert data["address"] == sample_customer_data["address"]
        assert data["area"] == sample_customer_data["area"]
    
    @pytest.mark.asyncio
    async def test_create_duplicate_customer(self, client: AsyncClient, auth_headers: dict, sample_customer_data: dict):
        """Test creating a customer with existing code"""
        # Create first customer
        await client.post(
            "/api/v1/customers",
            json=sample_customer_data,
            headers=auth_headers
        )
        
        # Try to create duplicate
        response = await client.post(
            "/api/v1/customers",
            json=sample_customer_data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "客戶代碼已存在" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_list_customers(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
        """Test listing customers with filters"""
        # Create test customers
        customers = [
            Customer(
                customer_code=f"C00{i}",
                short_name=f"客戶{i}",
                invoice_title=f"公司{i}",
                address=f"台北市信義區路{i}號",
                area="信義區" if i % 2 == 0 else "大安區",
                is_terminated=False
            )
            for i in range(1, 6)
        ]
        db_session.add_all(customers)
        await db_session.commit()
        
        # Test listing all customers
        response = await client.get("/api/v1/customers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 5
        assert len(data["items"]) >= 5
        
        # Test with area filter
        response = await client.get(
            "/api/v1/customers",
            params={"area": "信義區"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(item["area"] == "信義區" for item in data["items"])
        
        # Test with search
        response = await client.get(
            "/api/v1/customers",
            params={"search": "C001"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["items"][0]["customer_code"] == "C001"
        
        # Test pagination
        response = await client.get(
            "/api/v1/customers",
            params={"skip": 2, "limit": 2},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["skip"] == 2
        assert data["limit"] == 2
    
    @pytest.mark.asyncio
    async def test_get_customer(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
        """Test getting a specific customer"""
        # Create customer
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區"
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)
        
        response = await client.get(
            f"/api/v1/customers/{customer.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == customer.id
        assert data["customer_code"] == customer.customer_code
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_customer(self, client: AsyncClient, auth_headers: dict):
        """Test getting a non-existent customer"""
        response = await client.get(
            "/api/v1/customers/99999",
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "客戶不存在" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_customer(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
        """Test updating a customer"""
        # Create customer
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區"
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)
        
        update_data = {
            "short_name": "更新後的客戶",
            "phone1": "0912-345-678",
            "delivery_notes": "請按門鈴"
        }
        
        response = await client.put(
            f"/api/v1/customers/{customer.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["short_name"] == update_data["short_name"]
        assert data["phone1"] == update_data["phone1"]
        assert data["delivery_notes"] == update_data["delivery_notes"]
    
    @pytest.mark.asyncio
    async def test_delete_customer(self, client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession):
        """Test deleting (soft delete) a customer"""
        # Create customer
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區"
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)
        
        response = await client.delete(
            f"/api/v1/customers/{customer.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert "客戶已停用" in response.json()["message"]
        
        # Verify customer is soft deleted
        await db_session.refresh(customer)
        assert customer.is_terminated is True
    
    @pytest.mark.asyncio
    async def test_delete_customer_forbidden(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
        """Test deleting a customer without admin permission"""
        # Create customer
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區"
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)
        
        response = await client.delete(
            f"/api/v1/customers/{customer.id}",
            headers=auth_headers
        )
        assert response.status_code == 403
        assert "權限不足" in response.json()["detail"]


class TestCustomerInventory:
    """Test customer inventory endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_customer_inventory(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession
    ):
        """Test getting customer inventory"""
        # Create customer
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區"
        )
        db_session.add(customer)
        await db_session.flush()
        
        # Create gas products
        product_50kg = GasProduct(
            display_name="50公斤桶裝瓦斯",
            cylinder_type=CylinderType.KG_50,
            unit_price=2500,
            is_available=True
        )
        product_20kg = GasProduct(
            display_name="20公斤桶裝瓦斯",
            cylinder_type=CylinderType.KG_20,
            unit_price=1200,
            is_available=True
        )
        db_session.add(product_50kg)
        db_session.add(product_20kg)
        await db_session.flush()
        
        # Create inventory
        inventory1 = CustomerInventory(
            customer_id=customer.id,
            gas_product_id=product_50kg.id,
            quantity_owned=5,
            quantity_rented=2,
            is_active=True
        )
        inventory1.update_total()
        
        inventory2 = CustomerInventory(
            customer_id=customer.id,
            gas_product_id=product_20kg.id,
            quantity_owned=10,
            quantity_rented=0,
            is_active=True
        )
        inventory2.update_total()
        
        db_session.add(inventory1)
        db_session.add(inventory2)
        await db_session.commit()
        
        response = await client.get(
            f"/api/v1/customers/{customer.id}/inventory",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        
        # Check inventory data
        items = data["items"]
        assert any(item["quantity_owned"] == 5 and item["quantity_rented"] == 2 for item in items)
        assert any(item["quantity_owned"] == 10 and item["quantity_rented"] == 0 for item in items)
    
    @pytest.mark.asyncio
    async def test_update_customer_inventory(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession
    ):
        """Test updating customer inventory"""
        # Create customer and product
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區"
        )
        db_session.add(customer)
        
        product = GasProduct(
            display_name="50公斤桶裝瓦斯",
            cylinder_type=CylinderType.KG_50,
            unit_price=2500,
            is_available=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(customer)
        await db_session.refresh(product)
        
        # Update inventory (will create if not exists)
        update_data = {
            "quantity_owned": 10,
            "quantity_rented": 5,
            "is_active": True
        }
        
        response = await client.put(
            f"/api/v1/customers/{customer.id}/inventory/{product.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity_owned"] == 10
        assert data["quantity_rented"] == 5
        assert data["quantity_total"] == 15
        assert data["is_active"] is True