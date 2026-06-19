package handler

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"alert-hub/model"
	"alert-hub/service"
	"alert-hub/storage"

	"github.com/google/uuid"
)

type Handler struct {
	store   *storage.Store
	service *service.Service
}

func New(store *storage.Store, svc *service.Service) *Handler {
	return &Handler{store: store, service: svc}
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

type ingestResponse struct {
	Received int                      `json:"received"`
	Results  []*service.IngestResult  `json:"results"`
}

func (h *Handler) HandleCustomIngest(w http.ResponseWriter, r *http.Request) {
	var req model.CustomAlert
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json: "+err.Error())
		return
	}
	if req.Summary == "" {
		writeError(w, http.StatusBadRequest, "summary is required")
		return
	}
	alert := model.CustomAlertToAlert(&req, "custom")
	res, err := h.service.IngestAlert(alert)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, ingestResponse{Received: 1, Results: []*service.IngestResult{res}})
}

func (h *Handler) HandlePrometheusIngest(w http.ResponseWriter, r *http.Request) {
	var req model.PrometheusWebhook
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json: "+err.Error())
		return
	}
	results := []*service.IngestResult{}
	for i := range req.Alerts {
		pa := req.Alerts[i]
		if strings.EqualFold(pa.Status, "resolved") {
			continue
		}
		alert := model.PrometheusAlertToAlert(&pa)
		res, err := h.service.IngestAlert(alert)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		results = append(results, res)
	}
	writeJSON(w, http.StatusOK, ingestResponse{Received: len(results), Results: results})
}

func (h *Handler) HandleListAlerts(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	page, _ := strconv.Atoi(q.Get("page"))
	size, _ := strconv.Atoi(q.Get("size"))
	query := storage.AlertQuery{
		Service:  q.Get("service"),
		Env:      q.Get("env"),
		Severity: q.Get("severity"),
		Team:     q.Get("team"),
		Page:     page,
		PageSize: size,
	}
	result, err := h.store.ListAlerts(query)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, result)
}

func (h *Handler) HandleGetAlert(w http.ResponseWriter, r *http.Request, id string) {
	a, err := h.store.GetAlert(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if a == nil {
		writeError(w, http.StatusNotFound, "alert not found")
		return
	}
	writeJSON(w, http.StatusOK, a)
}

func (h *Handler) HandleListPolicies(w http.ResponseWriter, r *http.Request) {
	policies, err := h.store.ListPolicies()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, policies)
}

func (h *Handler) HandleGetPolicy(w http.ResponseWriter, r *http.Request, id string) {
	p, err := h.store.GetPolicy(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if p == nil {
		writeError(w, http.StatusNotFound, "policy not found")
		return
	}
	writeJSON(w, http.StatusOK, p)
}

func (h *Handler) HandleCreatePolicy(w http.ResponseWriter, r *http.Request) {
	var p model.Policy
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json: "+err.Error())
		return
	}
	if p.Name == "" {
		writeError(w, http.StatusBadRequest, "name is required")
		return
	}
	if p.Team == "" {
		writeError(w, http.StatusBadRequest, "team is required")
		return
	}
	if p.MatchLabels == nil {
		p.MatchLabels = map[string]string{}
	}
	p.ID = uuid.NewString()
	p.CreatedAt = time.Now().UTC()
	if err := h.store.CreatePolicy(&p); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, p)
}

func (h *Handler) HandleUpdatePolicy(w http.ResponseWriter, r *http.Request, id string) {
	existing, err := h.store.GetPolicy(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if existing == nil {
		writeError(w, http.StatusNotFound, "policy not found")
		return
	}
	var p model.Policy
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json: "+err.Error())
		return
	}
	existing.Name = p.Name
	existing.Team = p.Team
	existing.Priority = p.Priority
	if p.MatchLabels != nil {
		existing.MatchLabels = p.MatchLabels
	}
	if err := h.store.UpdatePolicy(existing); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, existing)
}

func (h *Handler) HandleDeletePolicy(w http.ResponseWriter, r *http.Request, id string) {
	existing, err := h.store.GetPolicy(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if existing == nil {
		writeError(w, http.StatusNotFound, "policy not found")
		return
	}
	if err := h.store.DeletePolicy(id); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (h *Handler) HandleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "time": time.Now().UTC().Format(time.RFC3339)})
}

func StripPrefix(prefix, path string) (string, error) {
	if !strings.HasPrefix(path, prefix) {
		return "", fmt.Errorf("path %s does not have prefix %s", path, prefix)
	}
	rest := strings.TrimPrefix(path, prefix)
	rest = strings.TrimPrefix(rest, "/")
	return rest, nil
}
