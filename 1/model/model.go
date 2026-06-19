package model

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sort"
	"strings"
	"time"
)

type Severity string

const (
	SeverityCritical Severity = "critical"
	SeverityWarning  Severity = "warning"
	SeverityInfo     Severity = "info"
)

type Alert struct {
	ID           string            `json:"id"`
	Fingerprint  string            `json:"fingerprint"`
	Summary      string            `json:"summary"`
	Description  string            `json:"description"`
	Severity     Severity          `json:"severity"`
	Service      string            `json:"service"`
	Env          string            `json:"env"`
	Labels       map[string]string `json:"labels"`
	Source       string            `json:"source"`
	DedupeCount  int               `json:"dedupe_count"`
	FirstSeenAt  time.Time         `json:"first_seen_at"`
	LastSeenAt   time.Time         `json:"last_seen_at"`
	AssignedTeam string            `json:"assigned_team"`
}

type Policy struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	MatchLabels map[string]string `json:"match_labels"`
	Team        string            `json:"team"`
	Priority    int               `json:"priority"`
	CreatedAt   time.Time         `json:"created_at"`
}

type AuditLog struct {
	ID        string    `json:"id"`
	AlertID   string    `json:"alert_id"`
	Action    string    `json:"action"`
	Team      string    `json:"team"`
	Detail    string    `json:"detail"`
	CreatedAt time.Time `json:"created_at"`
}

type PrometheusAlert struct {
	Status       string            `json:"status"`
	Labels       map[string]string `json:"labels"`
	Annotations  map[string]string `json:"annotations"`
	StartsAt     time.Time         `json:"startsAt"`
	EndsAt       time.Time         `json:"endsAt"`
	GeneratorURL string            `json:"generatorURL"`
	Fingerprint  string            `json:"fingerprint"`
}

type PrometheusWebhook struct {
	Version           string            `json:"version"`
	GroupKey          string            `json:"groupKey"`
	TruncatedAlerts   int               `json:"truncatedAlerts"`
	Status            string            `json:"status"`
	Receiver          string            `json:"receiver"`
	GroupLabels       map[string]string `json:"groupLabels"`
	CommonLabels      map[string]string `json:"commonLabels"`
	CommonAnnotations map[string]string `json:"commonAnnotations"`
	ExternalURL       string            `json:"externalURL"`
	Alerts            []PrometheusAlert `json:"alerts"`
}

type CustomAlert struct {
	Summary     string            `json:"summary"`
	Description string            `json:"description"`
	Severity    Severity          `json:"severity"`
	Service     string            `json:"service"`
	Env         string            `json:"env"`
	Labels      map[string]string `json:"labels"`
}

func (a *CustomAlert) ComputeFingerprint() string {
	labels := make(map[string]string)
	for k, v := range a.Labels {
		labels[k] = v
	}
	labels["summary"] = a.Summary
	labels["service"] = a.Service
	labels["env"] = a.Env

	keys := make([]string, 0, len(labels))
	for k := range labels {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	var sb strings.Builder
	for _, k := range keys {
		sb.WriteString(k)
		sb.WriteString("=")
		sb.WriteString(labels[k])
		sb.WriteString(";")
	}

	hash := sha256.Sum256([]byte(sb.String()))
	return hex.EncodeToString(hash[:])[:16]
}

func (pa *PrometheusAlert) ComputeFingerprint() string {
	if pa.Fingerprint != "" {
		return pa.Fingerprint
	}
	labels := make(map[string]string)
	for k, v := range pa.Labels {
		labels[k] = v
	}

	keys := make([]string, 0, len(labels))
	for k := range labels {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	var sb strings.Builder
	for _, k := range keys {
		sb.WriteString(k)
		sb.WriteString("=")
		sb.WriteString(labels[k])
		sb.WriteString(";")
	}

	hash := sha256.Sum256([]byte(sb.String()))
	return hex.EncodeToString(hash[:])[:16]
}

func CustomAlertToAlert(ca *CustomAlert, source string) *Alert {
	now := time.Now().UTC()
	fp := ca.ComputeFingerprint()
	labels := make(map[string]string)
	for k, v := range ca.Labels {
		labels[k] = v
	}
	sev := ca.Severity
	if sev == "" {
		sev = SeverityWarning
	}
	return &Alert{
		Fingerprint: fp,
		Summary:     ca.Summary,
		Description: ca.Description,
		Severity:    sev,
		Service:     ca.Service,
		Env:         ca.Env,
		Labels:      labels,
		Source:      source,
		DedupeCount: 1,
		FirstSeenAt: now,
		LastSeenAt:  now,
	}
}

func PrometheusAlertToAlert(pa *PrometheusAlert) *Alert {
	now := time.Now().UTC()
	fp := pa.ComputeFingerprint()

	summary := pa.Annotations["summary"]
	if summary == "" {
		summary = pa.Labels["alertname"]
	}
	description := pa.Annotations["description"]
	if description == "" {
		description = pa.Annotations["message"]
	}

	service := pa.Labels["service"]
	env := pa.Labels["env"]

	sevRaw := strings.ToLower(pa.Labels["severity"])
	var sev Severity
	switch sevRaw {
	case "critical", "fatal", "error":
		sev = SeverityCritical
	case "warning", "warn":
		sev = SeverityWarning
	case "info", "none":
		sev = SeverityInfo
	default:
		sev = SeverityWarning
	}

	labels := make(map[string]string)
	for k, v := range pa.Labels {
		if k != "severity" && k != "service" && k != "env" && k != "alertname" {
			labels[k] = v
		}
	}

	return &Alert{
		Fingerprint: fp,
		Summary:     summary,
		Description: description,
		Severity:    sev,
		Service:     service,
		Env:         env,
		Labels:      labels,
		Source:      "prometheus",
		DedupeCount: 1,
		FirstSeenAt: now,
		LastSeenAt:  now,
	}
}

func LabelsToJSON(labels map[string]string) string {
	if labels == nil {
		return "{}"
	}
	b, _ := json.Marshal(labels)
	return string(b)
}

func JSONToLabels(s string) map[string]string {
	m := make(map[string]string)
	if s == "" || s == "{}" {
		return m
	}
	_ = json.Unmarshal([]byte(s), &m)
	return m
}
