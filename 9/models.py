from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List


STAGE_CHOICES = [
    "初步接触",
    "需求沟通",
    "方案报价",
    "商务谈判",
    "合同签署",
    "项目交付",
    "已流失",
]


@dataclass
class Customer:
    id: Optional[int] = None
    company: str = ""
    contact: str = ""
    phone: str = ""
    stage: str = "初步接触"
    tags: str = ""
    next_follow_up: Optional[str] = None
    last_contacted: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def tag_list(self) -> List[str]:
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]


@dataclass
class FollowUp:
    id: Optional[int] = None
    customer_id: int = 0
    summary: str = ""
    contacted_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
