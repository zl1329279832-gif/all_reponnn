package main

import (
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"alert-aggregator/internal/db"
	"alert-aggregator/internal/handler"
	"alert-aggregator/internal/ingest"
)

func main() {
	store, err := db.New("./alerts.db")
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer store.Close()
	log.Println("Database initialized successfully")

	dedupeWindow := 5 * time.Minute
	if v := os.Getenv("DEDUPE_WINDOW_SECONDS"); v != "" {
		if secs, err := strconv.Atoi(v); err == nil && secs > 0 {
			dedupeWindow = time.Duration(secs) * time.Second
		}
	}
	log.Printf("Dedupe window: %v", dedupeWindow)

	ingestSvc := ingest.NewService(store, dedupeWindow)
	h := handler.New(store, ingestSvc)

	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", h.Health)

	mux.HandleFunc("POST /api/v1/ingest/prometheus", h.IngestPrometheus)
	mux.HandleFunc("POST /api/v1/ingest/custom", h.IngestCustom)

	mux.HandleFunc("GET /api/v1/alerts", h.ListAlerts)
	mux.HandleFunc("GET /api/v1/alerts/{id}", h.GetAlert)

	mux.HandleFunc("POST /api/v1/policies", h.CreatePolicy)
	mux.HandleFunc("GET /api/v1/policies", h.ListPolicies)
	mux.HandleFunc("GET /api/v1/policies/{id}", h.GetPolicy)
	mux.HandleFunc("PUT /api/v1/policies/{id}", h.UpdatePolicy)
	mux.HandleFunc("DELETE /api/v1/policies/{id}", h.DeletePolicy)

	mux.HandleFunc("GET /api/v1/audit", h.ListAuditLogs)

	log.Println("Server starting on :8080")
	if err := http.ListenAndServe(":8080", mux); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
