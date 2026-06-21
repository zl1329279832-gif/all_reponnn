import sqlite3
import os
import csv
from datetime import datetime, date
from typing import List, Optional, Dict, Tuple
from models import Customer, FollowUp


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "customers.db")


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_schema()
        if self._is_empty():
            self._seed_sample_data()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                contact TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                stage TEXT DEFAULT '初步接触',
                tags TEXT DEFAULT '',
                next_follow_up TEXT,
                last_contacted TEXT,
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS follow_ups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                summary TEXT NOT NULL,
                contacted_at TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_followups_customer ON follow_ups(customer_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_company ON customers(company)")
        self.conn.commit()

    def _is_empty(self) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM customers")
        return cur.fetchone()[0] == 0

    def _seed_sample_data(self):
        samples = [
            Customer(
                company="星辰科技有限公司",
                contact="张伟",
                phone="13800138001",
                stage="需求沟通",
                tags="制造业,大客户",
                next_follow_up=date.today().isoformat(),
                last_contacted="2026-06-15 14:30:00",
            ),
            Customer(
                company="蓝海文化传媒",
                contact="李娜",
                phone="13900139002",
                stage="方案报价",
                tags="传媒,老客户",
                next_follow_up="2026-06-10",
                last_contacted="2026-06-05 10:00:00",
            ),
            Customer(
                company="云端网络科技",
                contact="王强",
                phone="13700137003",
                stage="初步接触",
                tags="互联网",
                next_follow_up=date.today().isoformat(),
                last_contacted="2026-06-18 16:20:00",
            ),
            Customer(
                company="绿野农业发展",
                contact="赵敏",
                phone="13600136004",
                stage="商务谈判",
                tags="农业,潜在",
                next_follow_up="2026-06-25",
                last_contacted="2026-06-19 09:15:00",
            ),
            Customer(
                company="智联教育咨询",
                contact="孙磊",
                phone="13500135005",
                stage="合同签署",
                tags="教育,优质",
                next_follow_up="2026-06-22",
                last_contacted="2026-06-20 11:00:00",
            ),
        ]
        for c in samples:
            cid = self.add_customer(c)
            if c.company == "星辰科技有限公司":
                self.add_follow_up(FollowUp(customer_id=cid, summary="电话沟通，确认项目预算范围约 50 万", contacted_at="2026-06-15 14:30:00"))
                self.add_follow_up(FollowUp(customer_id=cid, summary="初次拜访，介绍公司案例与服务范围", contacted_at="2026-06-10 10:00:00"))
            elif c.company == "蓝海文化传媒":
                self.add_follow_up(FollowUp(customer_id=cid, summary="发送定制方案 PDF，等待反馈", contacted_at="2026-06-05 10:00:00"))

    def _row_to_customer(self, row: sqlite3.Row) -> Customer:
        return Customer(
            id=row["id"],
            company=row["company"],
            contact=row["contact"],
            phone=row["phone"],
            stage=row["stage"],
            tags=row["tags"],
            next_follow_up=row["next_follow_up"],
            last_contacted=row["last_contacted"],
            created_at=row["created_at"],
        )

    def _row_to_followup(self, row: sqlite3.Row) -> FollowUp:
        return FollowUp(
            id=row["id"],
            customer_id=row["customer_id"],
            summary=row["summary"],
            contacted_at=row["contacted_at"],
        )

    def add_customer(self, customer: Customer) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO customers (company, contact, phone, stage, tags, next_follow_up, last_contacted, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer.company, customer.contact, customer.phone, customer.stage,
            customer.tags, customer.next_follow_up, customer.last_contacted, customer.created_at,
        ))
        self.conn.commit()
        return cur.lastrowid

    def update_customer(self, customer: Customer) -> bool:
        if not customer.id:
            return False
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE customers SET company=?, contact=?, phone=?, stage=?, tags=?, next_follow_up=?, last_contacted=?
            WHERE id=?
        """, (
            customer.company, customer.contact, customer.phone, customer.stage,
            customer.tags, customer.next_follow_up, customer.last_contacted, customer.id,
        ))
        self.conn.commit()
        return cur.rowcount > 0

    def delete_customer(self, customer_id: int) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM customers WHERE id=?", (customer_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def get_customer(self, customer_id: int) -> Optional[Customer]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
        row = cur.fetchone()
        return self._row_to_customer(row) if row else None

    def get_customer_by_company(self, company: str) -> Optional[Customer]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM customers WHERE company=?", (company,))
        row = cur.fetchone()
        return self._row_to_customer(row) if row else None

    def list_customers(
        self,
        keyword: str = "",
        tag: str = "",
        stage: str = "",
        sort_by: str = "last_contacted",
        sort_desc: bool = True,
    ) -> List[Customer]:
        sql = "SELECT * FROM customers WHERE 1=1"
        params: list = []
        if keyword:
            sql += " AND (company LIKE ? OR contact LIKE ? OR phone LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        if tag:
            sql += " AND (tags LIKE ?)"
            params.append(f"%{tag}%")
        if stage:
            sql += " AND stage=?"
            params.append(stage)
        order_map = {
            "company": "company",
            "last_contacted": "COALESCE(last_contacted, '')",
            "next_follow_up": "COALESCE(next_follow_up, '')",
            "created_at": "created_at",
        }
        order_col = order_map.get(sort_by, order_map["last_contacted"])
        sql += f" ORDER BY {order_col} {'DESC' if sort_desc else 'ASC'}"
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return [self._row_to_customer(r) for r in cur.fetchall()]

    def list_all_tags(self) -> List[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT tags FROM customers WHERE tags IS NOT NULL AND tags <> ''")
        tags_set = set()
        for row in cur.fetchall():
            for t in row["tags"].split(","):
                t = t.strip()
                if t:
                    tags_set.add(t)
        return sorted(tags_set)

    def add_follow_up(self, fu: FollowUp) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO follow_ups (customer_id, summary, contacted_at)
            VALUES (?, ?, ?)
        """, (fu.customer_id, fu.summary, fu.contacted_at))
        cur.execute("""
            UPDATE customers SET last_contacted=? WHERE id=?
        """, (fu.contacted_at, fu.customer_id))
        self.conn.commit()
        return cur.lastrowid

    def list_follow_ups(self, customer_id: int) -> List[FollowUp]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM follow_ups WHERE customer_id=? ORDER BY contacted_at DESC
        """, (customer_id,))
        return [self._row_to_followup(r) for r in cur.fetchall()]

    def get_today_follow_ups(self) -> List[Customer]:
        today = date.today().isoformat()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM customers
            WHERE next_follow_up IS NOT NULL AND next_follow_up <= ?
            ORDER BY next_follow_up ASC
        """, (today,))
        return [self._row_to_customer(r) for r in cur.fetchall()]

    def export_csv(self, file_path: str):
        customers = self.list_customers(sort_by="company", sort_desc=False)
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["公司名称", "联系人", "电话", "阶段", "标签", "下次跟进日期", "最后联系时间", "创建时间"])
            for c in customers:
                writer.writerow([
                    c.company, c.contact, c.phone, c.stage, c.tags,
                    c.next_follow_up or "", c.last_contacted or "", c.created_at,
                ])

    def import_csv(self, file_path: str) -> Tuple[int, int]:
        added = 0
        updated = 0
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                company = (row.get("公司名称") or row.get("company") or "").strip()
                if not company:
                    continue
                contact = (row.get("联系人") or row.get("contact") or "").strip()
                phone = (row.get("电话") or row.get("phone") or "").strip()
                stage = (row.get("阶段") or row.get("stage") or "初步接触").strip()
                tags = (row.get("标签") or row.get("tags") or "").strip()
                next_fu = (row.get("下次跟进日期") or row.get("next_follow_up") or "").strip() or None
                last_c = (row.get("最后联系时间") or row.get("last_contacted") or "").strip() or None

                existing = self.get_customer_by_company(company)
                if existing:
                    if contact:
                        existing.contact = contact
                    if phone:
                        existing.phone = phone
                    if stage:
                        existing.stage = stage
                    if tags:
                        existing_tags = set(existing.tag_list())
                        for t in tags.split(","):
                            t = t.strip()
                            if t:
                                existing_tags.add(t)
                        existing.tags = ",".join(sorted(existing_tags))
                    if next_fu:
                        existing.next_follow_up = next_fu
                    if last_c:
                        existing.last_contacted = last_c
                    self.update_customer(existing)
                    updated += 1
                else:
                    c = Customer(
                        company=company,
                        contact=contact,
                        phone=phone,
                        stage=stage,
                        tags=tags,
                        next_follow_up=next_fu,
                        last_contacted=last_c,
                    )
                    self.add_customer(c)
                    added += 1
        return added, updated
