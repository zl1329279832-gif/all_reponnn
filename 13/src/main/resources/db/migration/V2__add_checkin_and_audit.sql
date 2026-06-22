ALTER TABLE reservations ADD COLUMN check_in_time TEXT;

ALTER TABLE reservations ADD COLUMN status TEXT NOT NULL DEFAULT 'NORMAL';

CREATE TABLE IF NOT EXISTS reservation_audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    operator TEXT NOT NULL,
    remark TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (reservation_id) REFERENCES reservations(id)
);

CREATE INDEX IF NOT EXISTS idx_reservation_audits_reservation_id ON reservation_audits(reservation_id);
CREATE INDEX IF NOT EXISTS idx_reservation_audits_action ON reservation_audits(action);
CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status);
