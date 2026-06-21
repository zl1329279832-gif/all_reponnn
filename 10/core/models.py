from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional


@dataclass
class Customer:
    id: Optional[int] = None
    company: str = ""
    contact_name: str = ""
    phone: str = ""
    email: str = ""
    tags: str = ""
    address: str = ""
    notes: str = ""
    next_follow_up: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    last_contact: Optional[str] = None

    @property
    def tag_list(self) -> List[str]:
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.replace("，", ",").split(",") if t.strip()]

    def is_overdue(self, today: Optional[date] = None) -> bool:
        if not self.next_follow_up:
            return False
        try:
            d = date.fromisoformat(self.next_follow_up[:10])
        except ValueError:
            return False
        if today is None:
            today = date.today()
        return d < today

    def is_today(self, today: Optional[date] = None) -> bool:
        if not self.next_follow_up:
            return False
        try:
            d = date.fromisoformat(self.next_follow_up[:10])
        except ValueError:
            return False
        if today is None:
            today = date.today()
        return d == today


@dataclass
class FollowUpRecord:
    id: Optional[int] = None
    customer_id: int = 0
    contact_time: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    channel: str = "电话"
    content: str = ""
    result: str = ""
    next_step: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
