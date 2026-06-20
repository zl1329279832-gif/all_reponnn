package model

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sort"
	"time"
)

type Alert struct {
	ID           int64             `json:"id"`
	Fingerprint  string            `json:"fingerprint"`
	Severity     string            `json:"severity"`
	Service      string            `json:"service"`
	Env          string            `json:"env"`
	Summary      string            `json:"summary"`
	Description  string            `json:"description"`
	Labels       map[string]string `json:"labels"`
	Annotations  map[string]string `json:"annotations"`
	DedupeCount  int               `json:"dedupe_count"`
	Source       string            `json:"source"`
	RawPayload   string            `json:"-"`
	StartsAt     time.Time         `json:"starts_at"`
	UpdatedAt    time.Time         `json:"updated_at"`
	OnCallGroup  string            `json:"on_call_group"`
}

type Policy struct {
	ID           int64             `json:"id"`
	Name         string            `json:"name"`
	Service      string            `json:"service"`
	Env          string            `json:"env"`
	Severity     string            `json:"severity"`
	OnCallGroup  string            `json:"on_call_group"`
	CreatedAt    time.Time         `json:"created_at"`
	UpdatedAt    time.Time         `json:"updated_at"`
}

type AuditLog struct {
	ID           int64     `json:"id"`
	AlertID      int64     `json:"alert_id"`
	Fingerprint  string    `json:"fingerprint"`
	Action       string    `json:"action"`
	OnCallGroup  string    `json:"on_call_group"`
	Severity     string    `json:"severity"`
	CreatedAt    time.Time `json:"created_at"`
	Details      string    `json:"details"`
}

type PrometheusWebhook struct {
	Version  string             `json:"version"`
	GroupKey string             `json:"groupKey"`
	Status   string             `json:"status"`
	Receiver string             `json:"receiver"`
	Alerts   []PrometheusAlert  `json:"alerts"`
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

type CustomAlert struct {
	Severity    string            `json:"severity"`
	Service     string            `json:"service"`
	Env         string            `json:"env"`
	Summary     string            `json:"summary"`
	Description string            `json:"description"`
	Labels      map[string]string `json:"labels"`
	Annotations map[string]string `json:"annotations"`
	Timestamp   time.Time         `json:"timestamp"`
}

func ComputeFingerprint(labels map[string]string) string {
	keys := make([]string, 0, len(labels))
	for k := range labels {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	h := sha256.New()
	for _, k := range keys {
		h.Write([]byte(k))
		h.Write([]byte("="))
		h.Write([]byte(labels[k]))
		h.Write([]byte("|"))
	}
	return hex.EncodeToString(h.Sum(nil))[:16]
}

func (a *Alert) ToJSON() string {
	b, _ := json.Marshal(a)
	return string(b)
}
