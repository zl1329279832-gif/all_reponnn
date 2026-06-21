import csv
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any, Set

from core.models import Customer, FollowUpRecord


class CustomerStorage:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    contact_name TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    address TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    next_follow_up TEXT,
                    created_at TEXT NOT NULL,
                    last_contact TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS follow_ups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    contact_time TEXT NOT NULL,
                    channel TEXT DEFAULT '电话',
                    content TEXT DEFAULT '',
                    result TEXT DEFAULT '',
                    next_step TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
                )
                """
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_cust_company ON customers(company)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_fu_customer ON follow_ups(customer_id)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_fu_time ON follow_ups(contact_time)"
            )
            conn.commit()

    # -------- Customers --------

    def _row_to_customer(self, row: sqlite3.Row) -> Customer:
        return Customer(
            id=row["id"],
            company=row["company"],
            contact_name=row["contact_name"] or "",
            phone=row["phone"] or "",
            email=row["email"] or "",
            tags=row["tags"] or "",
            address=row["address"] or "",
            notes=row["notes"] or "",
            next_follow_up=row["next_follow_up"],
            created_at=row["created_at"],
            last_contact=row["last_contact"],
        )

    def list_customers(
        self,
        search: str = "",
        tag: str = "",
        last_contact_from: Optional[str] = None,
        last_contact_to: Optional[str] = None,
        sort_by: str = "next_follow_up",
        sort_asc: bool = True,
    ) -> List[Customer]:
        sql = "SELECT * FROM customers WHERE 1=1"
        params: List[Any] = []
        if search:
            sql += " AND (company LIKE ? OR contact_name LIKE ? OR phone LIKE ?)"
            p = f"%{search}%"
            params.extend([p, p, p])
        if tag:
            sql += " AND (',' || REPLACE(REPLACE(tags, '，', ','), ' ', '') || ',' LIKE ?)"
            params.append(f"%,{tag},%")
        if last_contact_from:
            sql += " AND (last_contact IS NOT NULL AND date(last_contact) >= date(?))"
            params.append(last_contact_from)
        if last_contact_to:
            sql += " AND (last_contact IS NOT NULL AND date(last_contact) <= date(?))"
            params.append(last_contact_to)

        order_col = {
            "company": "company",
            "created_at": "created_at",
            "last_contact": "last_contact",
            "next_follow_up": "next_follow_up",
        }.get(sort_by, "next_follow_up")
        null_last = f"CASE WHEN {order_col} IS NULL THEN 1 ELSE 0 END,"
        sql += f" ORDER BY {null_last} {order_col} {'ASC' if sort_asc else 'DESC'}, id DESC"

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_customer(r) for r in rows]

    def get_customer(self, customer_id: int) -> Optional[Customer]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE id=?", (customer_id,)
            ).fetchone()
            return self._row_to_customer(row) if row else None

    def find_by_company(self, company: str) -> Optional[Customer]:
        if not company:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE company=? COLLATE NOCASE LIMIT 1",
                (company.strip(),),
            ).fetchone()
            return self._row_to_customer(row) if row else None

    def add_customer(self, customer: Customer) -> int:
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO customers
                (company, contact_name, phone, email, tags, address, notes,
                 next_follow_up, created_at, last_contact)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer.company.strip(),
                    customer.contact_name,
                    customer.phone,
                    customer.email,
                    customer.tags,
                    customer.address,
                    customer.notes,
                    customer.next_follow_up,
                    customer.created_at,
                    customer.last_contact,
                ),
            )
            conn.commit()
            return c.lastrowid

    def update_customer(self, customer: Customer) -> None:
        if customer.id is None:
            raise ValueError("customer.id required for update")
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE customers SET company=?, contact_name=?, phone=?, email=?,
                tags=?, address=?, notes=?, next_follow_up=?, last_contact=?
                WHERE id=?
                """,
                (
                    customer.company.strip(),
                    customer.contact_name,
                    customer.phone,
                    customer.email,
                    customer.tags,
                    customer.address,
                    customer.notes,
                    customer.next_follow_up,
                    customer.last_contact,
                    customer.id,
                ),
            )
            conn.commit()

    def merge_customer(self, existing: Customer, incoming: Customer) -> Customer:
        merged = Customer(
            id=existing.id,
            company=existing.company,
            contact_name=incoming.contact_name or existing.contact_name,
            phone=incoming.phone or existing.phone,
            email=incoming.email or existing.email,
            tags=self._merge_tags(existing.tags, incoming.tags),
            address=incoming.address or existing.address,
            notes=self._merge_blobs(existing.notes, incoming.notes),
            next_follow_up=self._later_date(existing.next_follow_up, incoming.next_follow_up),
            created_at=existing.created_at,
            last_contact=self._later_date(existing.last_contact, incoming.last_contact),
        )
        self.update_customer(merged)
        return merged

    @staticmethod
    def _merge_tags(a: str, b: str) -> str:
        tag_set: Set[str] = set()
        for src in (a, b):
            if not src:
                continue
            for t in src.replace("，", ",").split(","):
                t = t.strip()
                if t:
                    tag_set.add(t)
        return ",".join(sorted(tag_set))

    @staticmethod
    def _merge_blobs(a: str, b: str) -> str:
        parts = [p for p in [a.strip() if a else "", b.strip() if b else ""] if p]
        return "\n\n".join(parts)

    @staticmethod
    def _later_date(a: Optional[str], b: Optional[str]) -> Optional[str]:
        def _p(s):
            try:
                return datetime.fromisoformat(s[:19])
            except Exception:
                return None
        da, db = _p(a or ""), _p(b or "")
        if da and db:
            return max(a, b, key=lambda s: _p(s) or datetime.min)
        return a or b

    def delete_customer(self, customer_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
            conn.commit()

    def all_tags(self) -> List[str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT tags FROM customers WHERE tags IS NOT NULL AND tags <> ''").fetchall()
        s: Set[str] = set()
        for r in rows:
            for t in r["tags"].replace("，", ",").split(","):
                t = t.strip()
                if t:
                    s.add(t)
        return sorted(s)

    # -------- FollowUps --------

    def _row_to_fu(self, r: sqlite3.Row) -> FollowUpRecord:
        return FollowUpRecord(
            id=r["id"],
            customer_id=r["customer_id"],
            contact_time=r["contact_time"],
            channel=r["channel"] or "",
            content=r["content"] or "",
            result=r["result"] or "",
            next_step=r["next_step"] or "",
            created_at=r["created_at"],
        )

    def list_follow_ups(self, customer_id: int) -> List[FollowUpRecord]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM follow_ups WHERE customer_id=? ORDER BY contact_time DESC, id DESC",
                (customer_id,),
            ).fetchall()
            return [self._row_to_fu(r) for r in rows]

    def add_follow_up(self, fu: FollowUpRecord) -> int:
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO follow_ups
                (customer_id, contact_time, channel, content, result, next_step, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fu.customer_id,
                    fu.contact_time,
                    fu.channel,
                    fu.content,
                    fu.result,
                    fu.next_step,
                    fu.created_at,
                ),
            )
            conn.commit()
            last_id = c.lastrowid
            customer = self.get_customer(fu.customer_id)
            if customer:
                new_last = self._later_date(customer.last_contact, fu.contact_time)
                conn.execute(
                    "UPDATE customers SET last_contact=? WHERE id=?",
                    (new_last, customer.id),
                )
                conn.commit()
            return last_id

    # -------- Today & Overdue --------

    def list_today_follow_ups(self, today: Optional[date] = None) -> List[Customer]:
        if today is None:
            today = date.today()
        iso = today.isoformat()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM customers WHERE date(next_follow_up) <= date(?) AND next_follow_up IS NOT NULL ORDER BY next_follow_up ASC, id DESC",
                (iso,),
            ).fetchall()
            return [self._row_to_customer(r) for r in rows]

    # -------- CSV --------

    def import_csv(
        self, csv_path: str | Path, merge_same_company: bool = True
    ) -> Tuple[int, int, List[str]]:
        created = 0
        merged = 0
        messages: List[str] = []
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = {n.strip().lower(): n for n in (reader.fieldnames or [])}
            if not fieldnames:
                raise ValueError("CSV 文件为空或无表头")

            def _get(key_alt: List[str]) -> str:
                for alt in key_alt:
                    if alt in fieldnames:
                        return row[fieldnames[alt]] or ""
                return ""

            for i, row in enumerate(reader, start=1):
                company = _get(["company", "公司", "公司名称"]).strip()
                if not company:
                    messages.append(f"第 {i} 行：缺少公司名称，已跳过")
                    continue
                incoming = Customer(
                    company=company,
                    contact_name=_get(["contact_name", "联系人", "姓名"]),
                    phone=_get(["phone", "电话", "手机"]),
                    email=_get(["email", "邮箱", "邮件"]),
                    tags=_get(["tags", "标签"]),
                    address=_get(["address", "地址"]),
                    notes=_get(["notes", "备注"]),
                    next_follow_up=_get(["next_follow_up", "下次跟进"]),
                )
                existing = self.find_by_company(company)
                if existing and merge_same_company:
                    self.merge_customer(existing, incoming)
                    merged += 1
                elif existing:
                    messages.append(f"第 {i} 行：公司「{company}」已存在，已跳过（未开启合并）")
                else:
                    self.add_customer(incoming)
                    created += 1
        return created, merged, messages

    def export_csv(self, csv_path: str | Path) -> int:
        rows = self.list_customers(sort_by="company")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["公司", "联系人", "电话", "邮箱", "标签", "地址", "备注", "下次跟进", "最后联系"]
            )
            for c in rows:
                writer.writerow(
                    [
                        c.company,
                        c.contact_name,
                        c.phone,
                        c.email,
                        c.tags,
                        c.address,
                        c.notes,
                        c.next_follow_up or "",
                        c.last_contact or "",
                    ]
                )
        return len(rows)
