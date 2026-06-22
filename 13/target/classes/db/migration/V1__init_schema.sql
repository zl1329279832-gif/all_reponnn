CREATE TABLE IF NOT EXISTS meeting_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    floor INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    equipment TEXT NOT NULL DEFAULT '',
    available_slots TEXT NOT NULL DEFAULT '[{"start":"09:00","end":"18:00"}]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    employee_id TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    series_id TEXT,
    recurring_type TEXT NOT NULL DEFAULT 'NONE',
    cancelled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (room_id) REFERENCES meeting_rooms(id)
);

CREATE INDEX IF NOT EXISTS idx_reservations_room_time ON reservations(room_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_reservations_series ON reservations(series_id);
CREATE INDEX IF NOT EXISTS idx_reservations_cancelled ON reservations(cancelled);
CREATE INDEX IF NOT EXISTS idx_meeting_rooms_floor ON meeting_rooms(floor);

INSERT INTO meeting_rooms (name, floor, capacity, equipment, available_slots) VALUES
('凤凰厅', 1, 10, '投影仪,白板,视频会议', '[{"start":"09:00","end":"18:00"}]'),
('麒麟厅', 1, 6, '投影仪,白板', '[{"start":"09:00","end":"18:00"}]'),
('玄武厅', 2, 20, '投影仪,白板,视频会议,音响系统', '[{"start":"09:00","end":"20:00"}]'),
('青龙厅', 2, 4, '白板', '[{"start":"09:00","end":"18:00"}]'),
('朱雀厅', 3, 15, '投影仪,白板,视频会议', '[{"start":"09:00","end":"18:00"}]'),
('白虎厅', 3, 8, '投影仪,白板', '[{"start":"09:00","end":"18:00"}]');
