package ingest

import (
	"encoding/json"
	"fmt"
	"time"

	"alert-aggregator/internal/db"
	"alert-aggregator/internal/model"
)

type Service struct {
	store        *db.Store
	dedupeWindow time.Duration
}

func NewService(store *db.Store, dedupeWindow time.Duration) *Service {
	return &Service{
		store:        store,
		dedupeWindow: dedupeWindow,
	}
}

func (s *Service) IngestPrometheus(body []byte) ([]*model.Alert, error) {
	var webhook model.PrometheusWebhook
	if err := json.Unmarshal(body, &webhook); err != nil {
		return nil, fmt.Errorf("parse prometheus webhook: %w", err)
	}

	var alerts []*model.Alert
	rawBody := string(body)

	for _, pa := range webhook.Alerts {
		labels := make(map[string]string)
		for k, v := range pa.Labels {
			labels[k] = v
		}

		annotations := make(map[string]string)
		for k, v := range pa.Annotations {
			annotations[k] = v
		}

		severity := labels["severity"]
		if severity == "" {
			severity = "warning"
		}

		service := labels["service"]
		env := labels["env"]

		fingerprint := model.ComputeFingerprint(labels)

		onCallGroup, err := s.store.MatchPolicy(service, env, severity)
		if err != nil {
			return nil, fmt.Errorf("match policy: %w", err)
		}

		alert := &model.Alert{
			Fingerprint: fingerprint,
			Severity:    severity,
			Service:     service,
			Env:         env,
			Summary:     annotations["summary"],
			Description: annotations["description"],
			Labels:      labels,
			Annotations: annotations,
			Source:      "prometheus",
			RawPayload:  rawBody,
			StartsAt:    pa.StartsAt,
			OnCallGroup: onCallGroup,
		}

		merged, err := s.store.UpsertAlert(alert, s.dedupeWindow)
		if err != nil {
			return nil, fmt.Errorf("upsert alert: %w", err)
		}

		action := "created"
		if merged {
			action = "merged"
		}

		audit := &model.AuditLog{
			AlertID:     alert.ID,
			Fingerprint: alert.Fingerprint,
			Action:      action,
			OnCallGroup: alert.OnCallGroup,
			Severity:    alert.Severity,
			Details:     fmt.Sprintf("source=prometheus, dedupe_count=%d, merged=%v", alert.DedupeCount, merged),
		}
		if err := s.store.CreateAuditLog(audit); err != nil {
			return nil, fmt.Errorf("create audit log: %w", err)
		}

		alerts = append(alerts, alert)
	}

	return alerts, nil
}

func (s *Service) IngestCustom(body []byte) (*model.Alert, error) {
	var custom model.CustomAlert
	if err := json.Unmarshal(body, &custom); err != nil {
		return nil, fmt.Errorf("parse custom alert: %w", err)
	}

	labels := make(map[string]string)
	for k, v := range custom.Labels {
		labels[k] = v
	}
	labels["service"] = custom.Service
	labels["env"] = custom.Env
	labels["severity"] = custom.Severity

	annotations := make(map[string]string)
	for k, v := range custom.Annotations {
		annotations[k] = v
	}
	if custom.Summary != "" {
		annotations["summary"] = custom.Summary
	}
	if custom.Description != "" {
		annotations["description"] = custom.Description
	}

	fingerprint := model.ComputeFingerprint(labels)

	onCallGroup, err := s.store.MatchPolicy(custom.Service, custom.Env, custom.Severity)
	if err != nil {
		return nil, fmt.Errorf("match policy: %w", err)
	}

	startsAt := custom.Timestamp
	if startsAt.IsZero() {
		startsAt = time.Now()
	}

	alert := &model.Alert{
		Fingerprint: fingerprint,
		Severity:    custom.Severity,
		Service:     custom.Service,
		Env:         custom.Env,
		Summary:     custom.Summary,
		Description: custom.Description,
		Labels:      labels,
		Annotations: annotations,
		Source:      "custom",
		RawPayload:  string(body),
		StartsAt:    startsAt,
		OnCallGroup: onCallGroup,
	}

	merged, err := s.store.UpsertAlert(alert, s.dedupeWindow)
	if err != nil {
		return nil, fmt.Errorf("upsert alert: %w", err)
	}

	action := "created"
	if merged {
		action = "merged"
	}

	audit := &model.AuditLog{
		AlertID:     alert.ID,
		Fingerprint: alert.Fingerprint,
		Action:      action,
		OnCallGroup: alert.OnCallGroup,
		Severity:    alert.Severity,
		Details:     fmt.Sprintf("source=custom, dedupe_count=%d, merged=%v", alert.DedupeCount, merged),
	}
	if err := s.store.CreateAuditLog(audit); err != nil {
		return nil, fmt.Errorf("create audit log: %w", err)
	}

	return alert, nil
}
