"""
from dataclasses import dataclass
from typing import Any, Dict, List, Type
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from typing import Type

Base factory classes for test data generation
"""

import random
import string
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta
from typing import TypeVar

# Initialize Faker with Traditional Chinese locale
fake = Faker("zh_TW")

T = TypeVar("T", bound=DeclarativeMeta)


class BaseFactory:
    """Base factory class for creating test data"""

    model: Type[T] = None

    def __init__(self, session: AsyncSession):
        self.session = session
        self.fake = fake

    async def create(self, **kwargs) -> T:
        """Create a single instance"""
        data = await self.build(**kwargs)
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def create_batch(self, count: int, **kwargs) -> List[T]:
        """Create multiple instances"""
        instances = []
        for _ in range(count):
            instance = await self.create(**kwargs)
            instances.append(instance)
        return instances

    async def build(self, **kwargs) -> Dict[str, Any]:
        """Build instance data without saving"""
        data = await self.get_default_data()
        data.update(kwargs)
        return data

    async def get_default_data(self) -> Dict[str, Any]:
        """Get default data for the model"""
        raise NotImplementedError("Subclasses must implement get_default_data")

    @staticmethod
    def random_string(
        length: int = 10, chars: str = string.ascii_letters + string.digits
    ) -> str:
        """Generate a random string"""
        return "".join(random.choice(chars) for _ in range(length))

    @staticmethod
    def random_phone() -> str:
        """Generate a random Taiwan phone number"""
        mobile_prefixes = [
            "0910",
            "0911",
            "0912",
            "0919",
            "0921",
            "0922",
            "0928",
            "0932",
            "0933",
            "0934",
            "0935",
            "0937",
            "0958",
            "0960",
            "0963",
            "0968",
            "0970",
            "0972",
            "0975",
            "0978",
            "0987",
            "0988",
        ]
        return f"{random.choice(mobile_prefixes)}-{random.randint(100, 999)}-{random.randint(100, 999)}"

    @staticmethod
    def random_landline() -> str:
        """Generate a random Taiwan landline number"""
        area_codes = ["02", "03", "04", "05", "06", "07", "08"]
        area_code = random.choice(area_codes)
        if area_code == "02":
            return (
                f"{area_code}-{random.randint(2000, 9999)}-{random.randint(1000, 9999)}"
            )
        else:
            return (
                f"{area_code}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"
            )

    @staticmethod
    def random_tax_id() -> str:
        """Generate a valid Taiwan business tax ID (統一編號)"""
        # Taiwan business tax ID is 8 digits with checksum
        # For testing, we'll generate valid - looking IDs
        base = [random.randint(0, 9) for _ in range(7)]
        weights = [1, 2, 1, 2, 1, 2, 4]

        total = 0
        for i, digit in enumerate(base):
            product = digit * weights[i]
            total += product // 10 + product % 10

        checksum = (10 - (total % 10)) % 10
        base.append(checksum)

        return "".join(str(d) for d in base)

    @staticmethod
    def random_address() -> str:
        """Generate a random Taiwan address"""
        cities = [
            "台北市",
            "新北市",
            "桃園市",
            "台中市",
            "台南市",
            "高雄市",
            "新竹市",
            "基隆市",
        ]
        districts = {
            "台北市": [
                "中正區",
                "大同區",
                "中山區",
                "松山區",
                "大安區",
                "萬華區",
                "信義區",
                "士林區",
                "北投區",
                "內湖區",
                "南港區",
                "文山區",
            ],
            "新北市": [
                "板橋區",
                "三重區",
                "中和區",
                "永和區",
                "新莊區",
                "新店區",
                "土城區",
                "蘆洲區",
                "汐止區",
                "樹林區",
                "鶯歌區",
                "三峽區",
            ],
            "桃園市": [
                "桃園區",
                "中壢區",
                "平鎮區",
                "八德區",
                "楊梅區",
                "蘆竹區",
                "龜山區",
                "龍潭區",
                "大溪區",
                "大園區",
                "觀音區",
                "新屋區",
            ],
            "台中市": [
                "中區",
                "東區",
                "南區",
                "西區",
                "北區",
                "北屯區",
                "西屯區",
                "南屯區",
                "太平區",
                "大里區",
                "霧峰區",
                "烏日區",
            ],
            "台南市": [
                "中西區",
                "東區",
                "南區",
                "北區",
                "安平區",
                "安南區",
                "永康區",
                "歸仁區",
                "新化區",
                "左鎮區",
                "玉井區",
                "楠西區",
            ],
            "高雄市": [
                "楠梓區",
                "左營區",
                "鼓山區",
                "三民區",
                "鹽埕區",
                "前金區",
                "新興區",
                "苓雅區",
                "前鎮區",
                "旗津區",
                "小港區",
                "鳳山區",
            ],
            "新竹市": ["東區", "北區", "香山區"],
            "基隆市": [
                "仁愛區",
                "信義區",
                "中正區",
                "中山區",
                "安樂區",
                "暖暖區",
                "七堵區",
            ],
        }

        city = random.choice(cities)
        district = random.choice(districts.get(city, ["區"]))
        road_types = ["路", "街", "大道", "巷"]
        road_names = [
            "中山",
            "中正",
            "民生",
            "民權",
            "民族",
            "復興",
            "忠孝",
            "仁愛",
            "信義",
            "和平",
            "光復",
            "敦化",
            "建國",
            "承德",
            "重慶",
        ]

        road = f"{random.choice(road_names)}{random.choice(road_types)}"
        if random.random() > 0.5:
            road += f"{random.randint(1, 5)}段"

        number = f"{random.randint(1, 500)}號"
        if random.random() > 0.7:
            number += f"{random.randint(1, 20)}樓"

        return f"{city}{district}{road}{number}"

    @staticmethod
    def random_datetime(
        start_date: datetime = None, end_date: datetime = None
    ) -> datetime:
        """Generate a random datetime between start and end dates"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now() + timedelta(days=365)

        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        random_datetime = start_date + timedelta(days=random_days)

        # Add random hours, minutes, seconds
        random_datetime = random_datetime.replace(
            hour=random.randint(0, 23),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
        )

        return random_datetime

    @staticmethod
    def random_amount(min_amount: float = 100.0, max_amount: float = 10000.0) -> float:
        """Generate a random monetary amount"""
        return round(random.uniform(min_amount, max_amount), 2)

    @staticmethod
    def random_percentage(min_pct: float = 0.0, max_pct: float = 100.0) -> float:
        """Generate a random percentage"""
        return round(random.uniform(min_pct, max_pct), 2)
