package storage

import (
	"database/sql"
	"fmt"
	"time"

	"alert-hub/model"

	"github.com/google/uuid"
	_ "modernc.org/sqlite"
)

type Store struct {
	db *sql.DB
}

func NewStore(dbPath string) (*Store, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	db.SetMaxOpenConns(1)
	s := &Store{db: db}
	if err := s.initSchema(); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) DB() *sql.DB {
	return s.db
}

func (s *Store) initSchema() error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS alerts (
			id TEXT PRIMARY KEY,
			fingerprint TEXT NOT NULL,
			summary TEXT NOT NULL,
			description TEXT,
			severity TEXT NOT NULL,
			service TEXT,
			env TEXT,
			labels TEXT,
			source TEXT,
			dedupe_count INTEGER NOT NULL DEFAULT 1,
			first_seen_at DATETIME NOT NULL,
			last_seen_at DATETIME NOT NULL,
			assigned_team TEXT
		)`,
		`CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint)`,
		`CREATE INDEX IF NOT EXISTS idx_alerts_last_seen ON alerts(last_seen_at)`,
		`CREATE INDEX IF NOT EXISTS idx_alerts_service_env_severity ON alerts(service, env, severity)`,
		`CREATE TABLE IF NOT EXISTS policies (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			match_labels TEXT,
			team TEXT NOT NULL,
			priority INTEGER NOT NULL DEFAULT 0,
			created_at DATETIME NOT NULL
		)`,
		`CREATE INDEX IF NOT EXISTS idx_policies_priority ON policies(priority)`,
		`CREATE TABLE IF NOT EXISTS audit_logs (
			id TEXT PRIMARY KEY,
			alert_id TEXT NOT NULL,
			action TEXT NOT NULL,
			team TEXT,
			detail TEXT,
			created_at DATETIME NOT NULL
		)`,
		`CREATE INDEX IF NOT EXISTS idx_audit_alert ON audit_logs(alert_id)`,
	}
	for _, st := range stmts {
		if _, err := s.db.Exec(st); err != nil {
			return fmt.Errorf("exec schema %s: %w", st[:50], err)
		}
	}
	return nil
}

func (s *Store) FindAlertByFingerprintWithin(fp string, window time.Duration) (*model.Alert, error) {
	cutoff := time.Now().UTC().Add(-window)
	row := s.db.QueryRow(`
		SELECT id, fingerprint, summary, description, severity, service, env, labels, source,
		       dedupe_count, first_seen_at, last_seen_at, assigned_team
		FROM alerts
		WHERE fingerprint = ? AND last_seen_at >= ?
		ORDER BY last_seen_at DESC
		LIMIT 1`, fp, cutoff)
	return scanAlert(row)
}

func scanAlert(row interface {
	Scan(dest ...interface{}) error
}) (*model.Alert, error) {
	var a model.Alert
	var labelsJSON sql.NullString
	var assignedTeam sql.NullString
	var service, env, source sql.NullString
	var description sql.NullString
	err := row.Scan(
		&a.ID, &a.Fingerprint, &a.Summary, &description, &a.Severity,
		&service, &env, &labelsJSON, &source,
		&a.DedupeCount, &a.FirstSeenAt, &a.LastSeenAt, &assignedTeam,
	)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if description.Valid {
		a.Description = description.String
	}
	if service.Valid {
		a.Service = service.String
	}
	if env.Valid {
		a.Env = env.String
	}
	if source.Valid {
		a.Source = source.String
	}
	if assignedTeam.Valid {
		a.AssignedTeam = assignedTeam.String
	}
	a.Labels = model.JSONToLabels(labelsJSON.String)
	return &a, nil
}

func (s *Store) CreateAlert(a *model.Alert) error {
	if a.ID == "" {
		a.ID = uuid.NewString()
	}
	_, err := s.db.Exec(`
		INSERT INTO alerts (id, fingerprint, summary, description, severity, service, env, labels, source, dedupe_count, first_seen_at, last_seen_at, assigned_team)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		a.ID, a.Fingerprint, a.Summary, nullStr(a.Description), a.Severity,
		nullStr(a.Service), nullStr(a.Env), model.LabelsToJSON(a.Labels), nullStr(a.Source),
		a.DedupeCount, a.FirstSeenAt, a.LastSeenAt, nullStr(a.AssignedTeam),
	)
	return err
}

func (s *Store) UpdateAlert(a *model.Alert) error {
	_, err := s.db.Exec(`
		UPDATE alerts SET
			severity = ?,
			dedupe_count = ?,
			last_seen_at = ?,
			assigned_team = ?,
			summary = ?,
			description = ?,
			labels = ?
		WHERE id = ?`,
		a.Severity, a.DedupeCount, a.LastSeenAt, nullStr(a.AssignedTeam),
		a.Summary, nullStr(a.Description), model.LabelsToJSON(a.Labels), a.ID,
	)
	return err
}

type AlertQuery struct {
	Service  string
	Env      string
	Severity string
	Team     string
	Page     int
	PageSize int
}

func (q AlertQuery) Limit() int {
	if q.PageSize <= 0 {
		return 20
	}
	return q.PageSize
}

func (q AlertQuery) Offset() int {
	p := q.Page
	if p <= 0 {
		p = 1
	}
	return (p - 1) * q.Limit()
}

type AlertListResult struct {
	Total  int64         `json:"total"`
	Page   int           `json:"page"`
	Size   int           `json:"size"`
	Alerts []*model.Alert `json:"alerts"`
}

func (s *Store) ListAlerts(q AlertQuery) (*AlertListResult, error) {
	where := []string{"1=1"}
	args := []interface{}{}
	if q.Service != "" {
		where = append(where, "service = ?")
		args = append(args, q.Service)
	}
	if q.Env != "" {
		where = append(where, "env = ?")
		args = append(args, q.Env)
	}
	if q.Severity != "" {
		where = append(where, "severity = ?")
		args = append(args, q.Severity)
	}
	if q.Team != "" {
		where = append(where, "assigned_team = ?")
		args = append(args, q.Team)
	}
	whereSQL := ""
	for i, w := range where {
		if i == 0 {
			whereSQL = w
		} else {
			whereSQL += " AND " + w
		}
	}

	var total int64
	if err := s.db.QueryRow("SELECT COUNT(*) FROM alerts WHERE "+whereSQL, args...).Scan(&total); err != nil {
		return nil, err
	}

	rows, err := s.db.Query(`
		SELECT id, fingerprint, summary, description, severity, service, env, labels, source,
		       dedupe_count, first_seen_at, last_seen_at, assigned_team
		FROM alerts WHERE `+whereSQL+`
		ORDER BY last_seen_at DESC
		LIMIT ? OFFSET ?`, append(args, q.Limit(), q.Offset())...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	alerts := []*model.Alert{}
	for rows.Next() {
		a, err := scanAlert(rows)
		if err != nil {
			return nil, err
		}
		alerts = append(alerts, a)
	}
	return &AlertListResult{
		Total:  total,
		Page:   q.Page,
		Size:   q.Limit(),
		Alerts: alerts,
	}, nil
}

func (s *Store) GetAlert(id string) (*model.Alert, error) {
	row := s.db.QueryRow(`
		SELECT id, fingerprint, summary, description, severity, service, env, labels, source,
		       dedupe_count, first_seen_at, last_seen_at, assigned_team
		FROM alerts WHERE id = ?`, id)
	return scanAlert(row)
}

func (s *Store) ListPolicies() ([]*model.Policy, error) {
	rows, err := s.db.Query(`
		SELECT id, name, match_labels, team, priority, created_at
		FROM policies ORDER BY priority DESC, created_at ASC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	res := []*model.Policy{}
	for rows.Next() {
		var p model.Policy
		var labelsJSON sql.NullString
		if err := rows.Scan(&p.ID, &p.Name, &labelsJSON, &p.Team, &p.Priority, &p.CreatedAt); err != nil {
			return nil, err
		}
		p.MatchLabels = model.JSONToLabels(labelsJSON.String)
		res = append(res, &p)
	}
	return res, nil
}

func (s *Store) GetPolicy(id string) (*model.Policy, error) {
	var p model.Policy
	var labelsJSON sql.NullString
	err := s.db.QueryRow(`
		SELECT id, name, match_labels, team, priority, created_at
		FROM policies WHERE id = ?`, id).Scan(
		&p.ID, &p.Name, &labelsJSON, &p.Team, &p.Priority, &p.CreatedAt,
	)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	p.MatchLabels = model.JSONToLabels(labelsJSON.String)
	return &p, nil
}

func (s *Store) CreatePolicy(p *model.Policy) error {
	if p.ID == "" {
		p.ID = uuid.NewString()
	}
	if p.CreatedAt.IsZero() {
		p.CreatedAt = time.Now().UTC()
	}
	_, err := s.db.Exec(`
		INSERT INTO policies (id, name, match_labels, team, priority, created_at)
		VALUES (?, ?, ?, ?, ?, ?)`,
		p.ID, p.Name, model.LabelsToJSON(p.MatchLabels), p.Team, p.Priority, p.CreatedAt,
	)
	return err
}

func (s *Store) UpdatePolicy(p *model.Policy) error {
	_, err := s.db.Exec(`
		UPDATE policies SET name=?, match_labels=?, team=?, priority=? WHERE id=?`,
		p.Name, model.LabelsToJSON(p.MatchLabels), p.Team, p.Priority, p.ID,
	)
	return err
}

func (s *Store) DeletePolicy(id string) error {
	_, err := s.db.Exec("DELETE FROM policies WHERE id = ?", id)
	return err
}

func (s *Store) CreateAuditLog(al *model.AuditLog) error {
	if al.ID == "" {
		al.ID = uuid.NewString()
	}
	if al.CreatedAt.IsZero() {
		al.CreatedAt = time.Now().UTC()
	}
	_, err := s.db.Exec(`
		INSERT INTO audit_logs (id, alert_id, action, team, detail, created_at)
		VALUES (?, ?, ?, ?, ?, ?)`,
		al.ID, al.AlertID, al.Action, nullStr(al.Team), nullStr(al.Detail), al.CreatedAt,
	)
	return err
}

func nullStr(s string) interface{} {
	if s == "" {
		return nil
	}
	return s
}
