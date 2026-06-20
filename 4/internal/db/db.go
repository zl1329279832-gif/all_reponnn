package db

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"alert-aggregator/internal/model"

	_ "modernc.org/sqlite"
)

type Store struct {
	db *sql.DB
}

func New(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("ping db: %w", err)
	}

	s := &Store{db: db}
	if err := s.init(); err != nil {
		return nil, fmt.Errorf("init db: %w", err)
	}

	return s, nil
}

func (s *Store) init() error {
	if err := s.migrate(); err != nil {
		return fmt.Errorf("migrate: %w", err)
	}

	indexes := []string{
		`CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint)`,
		`CREATE INDEX IF NOT EXISTS idx_alerts_updated_at ON alerts(updated_at)`,
		`CREATE INDEX IF NOT EXISTS idx_alerts_service ON alerts(service)`,
		`CREATE INDEX IF NOT EXISTS idx_alerts_env ON alerts(env)`,
		`CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)`,
		`CREATE INDEX IF NOT EXISTS idx_audit_fingerprint ON audit_logs(fingerprint)`,
		`CREATE INDEX IF NOT EXISTS idx_policies_match ON policies(service, env, severity)`,
	}

	for _, idx := range indexes {
		if _, err := s.db.Exec(idx); err != nil {
			return fmt.Errorf("create index: %w", err)
		}
	}

	return nil
}

func (s *Store) migrate() error {
	_, err := s.db.Exec(`CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)`)
	if err != nil {
		return err
	}

	var version int
	err = s.db.QueryRow(`SELECT COALESCE(MAX(version), 0) FROM schema_version`).Scan(&version)
	if err != nil {
		return err
	}

	if version >= 1 {
		return nil
	}

	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	_, err = tx.Exec(`CREATE TABLE IF NOT EXISTS policies (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT NOT NULL,
		service TEXT,
		env TEXT,
		severity TEXT,
		on_call_group TEXT NOT NULL,
		created_at DATETIME,
		updated_at DATETIME
	)`)
	if err != nil {
		return err
	}

	_, err = tx.Exec(`CREATE TABLE IF NOT EXISTS audit_logs (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		alert_id INTEGER,
		fingerprint TEXT,
		action TEXT,
		on_call_group TEXT,
		severity TEXT,
		created_at DATETIME,
		details TEXT
	)`)
	if err != nil {
		return err
	}

	var alertsExists bool
	tx.QueryRow(`SELECT 1 FROM sqlite_master WHERE type='table' AND name='alerts'`).Scan(&alertsExists)

	if alertsExists {
		var sqlText string
		err = tx.QueryRow(`SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'`).Scan(&sqlText)
		if err != nil {
			return err
		}

		hasUniqueConstraint := false
		for i := 0; i <= len(sqlText)-len("UNIQUE"); i++ {
			if sqlText[i:i+len("UNIQUE")] == "UNIQUE" {
				hasUniqueConstraint = true
				break
			}
		}

		if hasUniqueConstraint {
			_, err = tx.Exec(`
				CREATE TABLE alerts_new (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					fingerprint TEXT NOT NULL,
					severity TEXT NOT NULL,
					service TEXT,
					env TEXT,
					summary TEXT,
					description TEXT,
					labels TEXT,
					annotations TEXT,
					dedupe_count INTEGER DEFAULT 1,
					source TEXT,
					raw_payload TEXT,
					starts_at DATETIME,
					updated_at DATETIME,
					on_call_group TEXT
				)
			`)
			if err != nil {
				return fmt.Errorf("create alerts_new: %w", err)
			}

			_, err = tx.Exec(`
				INSERT INTO alerts_new 
				SELECT id, fingerprint, severity, service, env, summary, description, 
				       labels, annotations, dedupe_count, source, raw_payload, 
				       starts_at, updated_at, on_call_group 
				FROM alerts
			`)
			if err != nil {
				return fmt.Errorf("copy alerts data: %w", err)
			}

			_, err = tx.Exec(`DROP TABLE alerts`)
			if err != nil {
				return fmt.Errorf("drop old alerts: %w", err)
			}

			_, err = tx.Exec(`ALTER TABLE alerts_new RENAME TO alerts`)
			if err != nil {
				return fmt.Errorf("rename alerts_new: %w", err)
			}
		}
	} else {
		_, err = tx.Exec(`
			CREATE TABLE alerts (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				fingerprint TEXT NOT NULL,
				severity TEXT NOT NULL,
				service TEXT,
				env TEXT,
				summary TEXT,
				description TEXT,
				labels TEXT,
				annotations TEXT,
				dedupe_count INTEGER DEFAULT 1,
				source TEXT,
				raw_payload TEXT,
				starts_at DATETIME,
				updated_at DATETIME,
				on_call_group TEXT
			)
		`)
		if err != nil {
			return err
		}
	}

	_, err = tx.Exec(`INSERT INTO schema_version (version) VALUES (1)`)
	if err != nil {
		return err
	}

	return tx.Commit()
}

func (s *Store) Close() error {
	return s.db.Close()
}

func mapToJSON(m map[string]string) string {
	if m == nil {
		return "{}"
	}
	b, _ := json.Marshal(m)
	return string(b)
}

func jsonToMap(s string) map[string]string {
	if s == "" || s == "{}" {
		return map[string]string{}
	}
	var m map[string]string
	json.Unmarshal([]byte(s), &m)
	return m
}

func (s *Store) UpsertAlert(alert *model.Alert, dedupeWindow time.Duration) (bool, error) {
	now := time.Now()
	alert.UpdatedAt = now

	tx, err := s.db.Begin()
	if err != nil {
		return false, err
	}
	defer tx.Rollback()

	var existingID int64
	var existingSeverity string
	var existingDedupeCount int
	var existingUpdatedAt time.Time
	var existingStartsAt time.Time

	windowStart := now.Add(-dedupeWindow)
	err = tx.QueryRow(`
		SELECT id, severity, dedupe_count, updated_at, starts_at 
		FROM alerts 
		WHERE fingerprint = ? AND updated_at >= ?
		ORDER BY updated_at DESC LIMIT 1
	`, alert.Fingerprint, windowStart).Scan(&existingID, &existingSeverity, &existingDedupeCount, &existingUpdatedAt, &existingStartsAt)

	if err == nil {
		alert.ID = existingID
		alert.DedupeCount = existingDedupeCount + 1
		alert.StartsAt = existingStartsAt
		mergedSeverity := maxSeverity(existingSeverity, alert.Severity)
		alert.Severity = mergedSeverity

		if alert.Labels == nil {
			alert.Labels = make(map[string]string)
		}
		alert.Labels["severity"] = mergedSeverity

		onCallGroup, err := s.matchPolicyTx(tx, alert.Service, alert.Env, mergedSeverity)
		if err != nil {
			return false, fmt.Errorf("match policy: %w", err)
		}
		alert.OnCallGroup = onCallGroup

		_, err = tx.Exec(`
			UPDATE alerts 
			SET severity = ?, service = ?, env = ?, summary = ?, description = ?,
				labels = ?, annotations = ?, dedupe_count = ?, source = ?, 
				raw_payload = ?, updated_at = ?, on_call_group = ?
			WHERE id = ?
		`,
			alert.Severity, alert.Service, alert.Env, alert.Summary, alert.Description,
			mapToJSON(alert.Labels), mapToJSON(alert.Annotations), alert.DedupeCount, alert.Source,
			alert.RawPayload, alert.UpdatedAt, alert.OnCallGroup, alert.ID,
		)
		if err != nil {
			return false, err
		}

		if err := tx.Commit(); err != nil {
			return false, err
		}
		return true, nil
	}

	if !errors.Is(err, sql.ErrNoRows) {
		return false, err
	}

	if alert.StartsAt.IsZero() {
		alert.StartsAt = now
	}

	if alert.Labels == nil {
		alert.Labels = make(map[string]string)
	}
	alert.Labels["severity"] = alert.Severity

	onCallGroup, err := s.matchPolicyTx(tx, alert.Service, alert.Env, alert.Severity)
	if err != nil {
		return false, fmt.Errorf("match policy: %w", err)
	}
	alert.OnCallGroup = onCallGroup

	result, err := tx.Exec(`
		INSERT INTO alerts 
		(fingerprint, severity, service, env, summary, description, labels, annotations,
		 dedupe_count, source, raw_payload, starts_at, updated_at, on_call_group)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`,
		alert.Fingerprint, alert.Severity, alert.Service, alert.Env, alert.Summary, alert.Description,
		mapToJSON(alert.Labels), mapToJSON(alert.Annotations), 1, alert.Source,
		alert.RawPayload, alert.StartsAt, alert.UpdatedAt, alert.OnCallGroup,
	)
	if err != nil {
		return false, err
	}

	alert.ID, _ = result.LastInsertId()
	alert.DedupeCount = 1

	if err := tx.Commit(); err != nil {
		return false, err
	}
	return false, nil
}

func (s *Store) GetAlertByID(id int64) (*model.Alert, error) {
	var a model.Alert
	var labelsStr, annosStr string

	err := s.db.QueryRow(`
		SELECT id, fingerprint, severity, service, env, summary, description,
		       labels, annotations, dedupe_count, source, starts_at, updated_at, on_call_group
		FROM alerts WHERE id = ?
	`, id).Scan(&a.ID, &a.Fingerprint, &a.Severity, &a.Service, &a.Env, &a.Summary, &a.Description,
		&labelsStr, &annosStr, &a.DedupeCount, &a.Source, &a.StartsAt, &a.UpdatedAt, &a.OnCallGroup)

	if err != nil {
		return nil, err
	}

	a.Labels = jsonToMap(labelsStr)
	a.Annotations = jsonToMap(annosStr)
	return &a, nil
}

type AlertFilter struct {
	Service    string
	Env        string
	Severity   string
	Page       int
	PageSize   int
}

func (s *Store) ListAlerts(filter AlertFilter) ([]model.Alert, int64, error) {
	where := []string{}
	args := []interface{}{}

	if filter.Service != "" {
		where = append(where, "service = ?")
		args = append(args, filter.Service)
	}
	if filter.Env != "" {
		where = append(where, "env = ?")
		args = append(args, filter.Env)
	}
	if filter.Severity != "" {
		where = append(where, "severity = ?")
		args = append(args, filter.Severity)
	}

	whereClause := ""
	if len(where) > 0 {
		whereClause = " WHERE " + join(where, " AND ")
	}

	var total int64
	err := s.db.QueryRow(`SELECT COUNT(*) FROM alerts` + whereClause, args...).Scan(&total)
	if err != nil {
		return nil, 0, err
	}

	if filter.Page <= 0 {
		filter.Page = 1
	}
	if filter.PageSize <= 0 {
		filter.PageSize = 20
	}

	offset := (filter.Page - 1) * filter.PageSize
	args = append(args, filter.PageSize, offset)

	rows, err := s.db.Query(`
		SELECT id, fingerprint, severity, service, env, summary, description,
		       labels, annotations, dedupe_count, source, starts_at, updated_at, on_call_group
		FROM alerts` + whereClause + ` ORDER BY updated_at DESC LIMIT ? OFFSET ?
	`, args...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	alerts := []model.Alert{}
	for rows.Next() {
		var a model.Alert
		var labelsStr, annosStr string
		err := rows.Scan(&a.ID, &a.Fingerprint, &a.Severity, &a.Service, &a.Env, &a.Summary, &a.Description,
			&labelsStr, &annosStr, &a.DedupeCount, &a.Source, &a.StartsAt, &a.UpdatedAt, &a.OnCallGroup)
		if err != nil {
			return nil, 0, err
		}
		a.Labels = jsonToMap(labelsStr)
		a.Annotations = jsonToMap(annosStr)
		alerts = append(alerts, a)
	}

	return alerts, total, nil
}

func (s *Store) CreatePolicy(p *model.Policy) error {
	now := time.Now()
	p.CreatedAt = now
	p.UpdatedAt = now

	result, err := s.db.Exec(`
		INSERT INTO policies (name, service, env, severity, on_call_group, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?)
	`, p.Name, p.Service, p.Env, p.Severity, p.OnCallGroup, p.CreatedAt, p.UpdatedAt)
	if err != nil {
		return err
	}
	p.ID, _ = result.LastInsertId()
	return nil
}

func (s *Store) GetPolicy(id int64) (*model.Policy, error) {
	var p model.Policy
	err := s.db.QueryRow(`
		SELECT id, name, service, env, severity, on_call_group, created_at, updated_at
		FROM policies WHERE id = ?
	`, id).Scan(&p.ID, &p.Name, &p.Service, &p.Env, &p.Severity, &p.OnCallGroup, &p.CreatedAt, &p.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return &p, nil
}

func (s *Store) ListPolicies() ([]model.Policy, error) {
	rows, err := s.db.Query(`
		SELECT id, name, service, env, severity, on_call_group, created_at, updated_at
		FROM policies ORDER BY created_at DESC
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	policies := []model.Policy{}
	for rows.Next() {
		var p model.Policy
		err := rows.Scan(&p.ID, &p.Name, &p.Service, &p.Env, &p.Severity, &p.OnCallGroup, &p.CreatedAt, &p.UpdatedAt)
		if err != nil {
			return nil, err
		}
		policies = append(policies, p)
	}
	return policies, nil
}

func (s *Store) UpdatePolicy(p *model.Policy) error {
	p.UpdatedAt = time.Now()
	_, err := s.db.Exec(`
		UPDATE policies 
		SET name = ?, service = ?, env = ?, severity = ?, on_call_group = ?, updated_at = ?
		WHERE id = ?
	`, p.Name, p.Service, p.Env, p.Severity, p.OnCallGroup, p.UpdatedAt, p.ID)
	return err
}

func (s *Store) DeletePolicy(id int64) error {
	_, err := s.db.Exec(`DELETE FROM policies WHERE id = ?`, id)
	return err
}

type queryRunner interface {
	Query(query string, args ...interface{}) (*sql.Rows, error)
}

func (s *Store) MatchPolicy(service, env, severity string) (string, error) {
	return s.matchPolicyRunner(s.db, service, env, severity)
}

func (s *Store) matchPolicyTx(tx *sql.Tx, service, env, severity string) (string, error) {
	return s.matchPolicyRunner(tx, service, env, severity)
}

func (s *Store) matchPolicyRunner(q queryRunner, service, env, severity string) (string, error) {
	rows, err := q.Query(`
		SELECT service, env, severity, on_call_group 
		FROM policies 
		ORDER BY 
			CASE WHEN service = ? THEN 0 ELSE 1 END,
			CASE WHEN env = ? THEN 0 ELSE 1 END,
			CASE WHEN severity = ? THEN 0 ELSE 1 END
	`, service, env, severity)
	if err != nil {
		return "", err
	}
	defer rows.Close()

	type policyMatch struct {
		service     string
		env         string
		severity    string
		onCallGroup string
	}

	var matches []policyMatch
	for rows.Next() {
		var pm policyMatch
		err := rows.Scan(&pm.service, &pm.env, &pm.severity, &pm.onCallGroup)
		if err != nil {
			return "", err
		}
		matches = append(matches, pm)
	}

	for _, pm := range matches {
		if pm.service == service || pm.service == "" || pm.service == "*" {
			if pm.env == env || pm.env == "" || pm.env == "*" {
				if pm.severity == severity || pm.severity == "" || pm.severity == "*" {
					return pm.onCallGroup, nil
				}
			}
		}
	}

	return "default", nil
}

func (s *Store) CreateAuditLog(log *model.AuditLog) error {
	log.CreatedAt = time.Now()
	_, err := s.db.Exec(`
		INSERT INTO audit_logs (alert_id, fingerprint, action, on_call_group, severity, created_at, details)
		VALUES (?, ?, ?, ?, ?, ?, ?)
	`, log.AlertID, log.Fingerprint, log.Action, log.OnCallGroup, log.Severity, log.CreatedAt, log.Details)
	return err
}

func (s *Store) ListAuditLogs(limit, offset int) ([]model.AuditLog, int64, error) {
	var total int64
	err := s.db.QueryRow(`SELECT COUNT(*) FROM audit_logs`).Scan(&total)
	if err != nil {
		return nil, 0, err
	}

	rows, err := s.db.Query(`
		SELECT id, alert_id, fingerprint, action, on_call_group, severity, created_at, details
		FROM audit_logs ORDER BY created_at DESC LIMIT ? OFFSET ?
	`, limit, offset)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	logs := []model.AuditLog{}
	for rows.Next() {
		var l model.AuditLog
		err := rows.Scan(&l.ID, &l.AlertID, &l.Fingerprint, &l.Action, &l.OnCallGroup, &l.Severity, &l.CreatedAt, &l.Details)
		if err != nil {
			return nil, 0, err
		}
		logs = append(logs, l)
	}
	return logs, total, nil
}

var severityRank = map[string]int{
	"critical": 4,
	"error":    3,
	"warning":  2,
	"info":     1,
	"debug":    0,
}

func maxSeverity(a, b string) string {
	ra, okA := severityRank[a]
	rb, okB := severityRank[b]
	if !okA && !okB {
		return a
	}
	if !okA {
		return b
	}
	if !okB {
		return a
	}
	if ra >= rb {
		return a
	}
	return b
}

func join(parts []string, sep string) string {
	if len(parts) == 0 {
		return ""
	}
	result := parts[0]
	for i := 1; i < len(parts); i++ {
		result += sep + parts[i]
	}
	return result
}
