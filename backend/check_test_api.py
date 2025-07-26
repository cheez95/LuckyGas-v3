"""
Check test API endpoints
"""
import asyncio
import httpx

API_BASE_URL = "http://localhost:8001/api/v1"

async def check_api():
    """Check API endpoints"""
    
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        print("=== API Check ===\n")
        
        # 1. Check health
        print("1. Checking API health...")
        try:
            response = await client.get("/health")
            print(f"   Health endpoint status: {response.status_code}")
        except Exception as e:
            print(f"   Health check failed: {e}")
        
        # 2. Check docs
        print("\n2. Checking API docs...")
        try:
            response = await client.get("/docs")
            print(f"   Docs endpoint status: {response.status_code}")
            print(f"   API docs available at: http://localhost:8001/api/v1/docs")
        except Exception as e:
            print(f"   Docs check failed: {e}")
        
        # 3. Try test endpoints
        print("\n3. Checking test endpoints...")
        try:
            response = await client.get("/test/users")
            print(f"   Test users endpoint status: {response.status_code}")
            if response.status_code == 200:
                users = response.json()
                print(f"   Available test users:")
                for user in users:
                    print(f"     - {user['username']} ({user['role']})")
        except Exception as e:
            print(f"   Test endpoint check failed: {e}")
        
        print("\n=== Check Complete ===")

if __name__ == "__main__":
    asyncio.run(check_api())