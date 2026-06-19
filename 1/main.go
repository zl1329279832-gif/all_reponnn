package main

import (
	"log"
	"net/http"
	"strings"

	"alert-hub/handler"
	"alert-hub/service"
	"alert-hub/storage"
)

func main() {
	store, err := storage.NewStore("alert-hub.db")
	if err != nil {
		log.Fatalf("failed to init storage: %v", err)
	}
	defer store.Close()

	svc := service.New(store)
	h := handler.New(store, svc)

	mux := http.NewServeMux()

	mux.HandleFunc("/healthz", h.HandleHealth)

	api := "/api/v1"

	mux.HandleFunc(api+"/alerts/custom", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		h.HandleCustomIngest(w, r)
	})

	mux.HandleFunc(api+"/alerts/prometheus", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		h.HandlePrometheusIngest(w, r)
	})

	mux.HandleFunc(api+"/alerts", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		h.HandleListAlerts(w, r)
	})

	mux.HandleFunc(api+"/alerts/", func(w http.ResponseWriter, r *http.Request) {
		rest, err := handler.StripPrefix(api+"/alerts", r.URL.Path)
		if err != nil {
			http.NotFound(w, r)
			return
		}
		id := strings.TrimSuffix(rest, "/")
		if id == "" {
			http.NotFound(w, r)
			return
		}
		switch r.Method {
		case http.MethodGet:
			h.HandleGetAlert(w, r, id)
		default:
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc(api+"/policies", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			h.HandleListPolicies(w, r)
		case http.MethodPost:
			h.HandleCreatePolicy(w, r)
		default:
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc(api+"/policies/", func(w http.ResponseWriter, r *http.Request) {
		rest, err := handler.StripPrefix(api+"/policies", r.URL.Path)
		if err != nil {
			http.NotFound(w, r)
			return
		}
		id := strings.TrimSuffix(rest, "/")
		if id == "" {
			http.NotFound(w, r)
			return
		}
		switch r.Method {
		case http.MethodGet:
			h.HandleGetPolicy(w, r, id)
		case http.MethodPut, http.MethodPatch:
			h.HandleUpdatePolicy(w, r, id)
		case http.MethodDelete:
			h.HandleDeletePolicy(w, r, id)
		default:
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		}
	})

	addr := ":8080"
	log.Printf("alert-hub starting on %s ...", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
