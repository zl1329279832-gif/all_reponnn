package service

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"alert-hub/model"
	"alert-hub/storage"
)

const (
	DedupeWindow   = 5 * time.Minute
	DefaultTeam    = "default"
	ActionIngested = "ingested"
	ActionDeduped  = "deduped"
	ActionDispatched = "dispatched"
)

type Service struct {
	store *storage.Store
}

func New(store *storage.Store) *Service {
	return &Service{store: store}
}

type IngestResult struct {
	Alert       *model.Alert `json:"alert"`
	IsDedupe    bool         `json:"is_dedupe"`
	DedupeCount int          `json:"dedupe_count"`
}

func (svc *Service) IngestAlert(incoming *model.Alert) (*IngestResult, error) {
	tx, err := svc.store.DB().Begin()
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()

	existing, err := svc.findAlertByFingerprintWithinTx(tx, incoming.Fingerprint, DedupeWindow)
	if err != nil {
		return nil, err
	}

	var result *IngestResult
	var saved *model.Alert

	if existing != nil {
		existing.DedupeCount++
		existing.Severity = resolveSeverity(existing.Severity, incoming.Severity)
		existing.LastSeenAt = time.Now().UTC()
		if incoming.Description != "" {
			existing.Description = incoming.Description
		}
		if len(incoming.Labels) > 0 {
			for k, v := range incoming.Labels {
				existing.Labels[k] = v
			}
		}

		team := svc.matchTeam(existing)
		existing.AssignedTeam = team

		if err := updateAlertTx(tx, existing); err != nil {
			return nil, err
		}
		saved = existing
		result = &IngestResult{
			Alert:       existing,
			IsDedupe:    true,
			DedupeCount: existing.DedupeCount,
		}

		if err := createAuditTx(tx, &model.AuditLog{
			AlertID: existing.ID,
			Action:  ActionDeduped,
			Team:    team,
			Detail:  fmt.Sprintf("dedupe_count=%d, severity=%s", existing.DedupeCount, existing.Severity),
		}); err != nil {
			return nil, err
		}
	} else {
		team := svc.matchTeam(incoming)
		incoming.AssignedTeam = team

		if err := createAlertTx(tx, incoming); err != nil {
			return nil, err
		}
		saved = incoming
		result = &IngestResult{
			Alert:       incoming,
			IsDedupe:    false,
			DedupeCount: 1,
		}

		if err := createAuditTx(tx, &model.AuditLog{
			AlertID: incoming.ID,
			Action:  ActionIngested,
			Team:    team,
			Detail:  fmt.Sprintf("source=%s, severity=%s", incoming.Source, incoming.Severity),
		}); err != nil {
			return nil, err
		}
	}

	if err := createAuditTx(tx, &model.AuditLog{
		AlertID: saved.ID,
		Action:  ActionDispatched,
		Team:    saved.AssignedTeam,
		Detail:  fmt.Sprintf("dispatched to team=%s", saved.AssignedTeam),
	}); err != nil {
		return nil, err
	}

	if err := tx.Commit(); err != nil {
		return nil, err
	}
	return result, nil
}

func resolveSeverity(old, new model.Severity) model.Severity {
	rank := func(s model.Severity) int {
		switch s {
		case model.SeverityCritical:
			return 3
		case model.SeverityWarning:
			return 2
		case model.SeverityInfo:
			return 1
		}
		return 0
	}
	if rank(new) >= rank(old) {
		return new
	}
	return old
}

func (svc *Service) matchTeam(a *model.Alert) string {
	policies, err := svc.store.ListPolicies()
	if err != nil {
		return DefaultTeam
	}
	for _, p := range policies {
		if svc.policyMatches(p, a) {
			return p.Team
		}
	}
	return DefaultTeam
}

func (svc *Service) policyMatches(p *model.Policy, a *model.Alert) bool {
	for k, v := range p.MatchLabels {
		switch k {
		case "service":
			if a.Service != v {
				return false
			}
		case "env":
			if a.Env != v {
				return false
			}
		case "severity":
			if string(a.Severity) != v {
				return false
			}
		default:
			if a.Labels[k] != v {
				return false
			}
		}
	}
	return true
}

func (svc *Service) findAlertByFingerprintWithinTx(tx *sql.Tx, fp string, window time.Duration) (*model.Alert, error) {
	cutoff := time.Now().UTC().Add(-window)
	row := tx.QueryRow(`
		SELECT id, fingerprint, summary, description, severity, service, env, labels, source,
		       dedupe_count, first_seen_at, last_seen_at, assigned_team
		FROM alerts
		WHERE fingerprint = ? AND last_seen_at >= ?
		ORDER BY last_seen_at DESC
		LIMIT 1`, fp, cutoff)
	return scanAlertTx(row)
}

func scanAlertTx(row interface {
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

func createAlertTx(tx *sql.Tx, a *model.Alert) error {
	_, err := tx.Exec(`
		INSERT INTO alerts (id, fingerprint, summary, description, severity, service, env, labels, source, dedupe_count, first_seen_at, last_seen_at, assigned_team)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		a.ID, a.Fingerprint, a.Summary, nullStr(a.Description), a.Severity,
		nullStr(a.Service), nullStr(a.Env), model.LabelsToJSON(a.Labels), nullStr(a.Source),
		a.DedupeCount, a.FirstSeenAt, a.LastSeenAt, nullStr(a.AssignedTeam),
	)
	return err
}

func updateAlertTx(tx *sql.Tx, a *model.Alert) error {
	_, err := tx.Exec(`
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

func createAuditTx(tx *sql.Tx, al *model.AuditLog) error {
	_, err := tx.Exec(`
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

func ToJSON(v interface{}) string {
	b, _ := json.Marshal(v)
	return string(b)
}
