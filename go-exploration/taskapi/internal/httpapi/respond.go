package httpapi

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"

	"platformlab/taskapi/internal/task"
)

const maxBodyBytes = 1 << 20 // 1 MiB

// errorBody is the single error shape every endpoint returns.
type errorBody struct {
	Error     string            `json:"error"`
	Fields    map[string]string `json:"fields,omitempty"`
	RequestID string            `json:"request_id,omitempty"`
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// writeError maps domain errors to HTTP status codes. This is the ONLY place
// that knows about that mapping -- handlers just return the error here.
func writeError(w http.ResponseWriter, r *http.Request, log *slog.Logger, err error) {
	reqID := RequestIDFrom(r.Context())

	var ve *task.ValidationError
	var he *httpError
	switch {
	case errors.As(err, &ve):
		writeJSON(w, http.StatusUnprocessableEntity, errorBody{Error: "validation failed", Fields: ve.Fields, RequestID: reqID})
	case errors.As(err, &he):
		writeJSON(w, he.status, errorBody{Error: he.msg, RequestID: reqID})
	case errors.Is(err, task.ErrNotFound):
		writeJSON(w, http.StatusNotFound, errorBody{Error: err.Error(), RequestID: reqID})
	default:
		// Unexpected: log the details, show the client nothing internal.
		log.ErrorContext(r.Context(), "internal error", "err", err, "request_id", reqID)
		writeJSON(w, http.StatusInternalServerError, errorBody{Error: "internal server error", RequestID: reqID})
	}
}

// httpError is for problems detected in the HTTP layer itself (bad JSON, bad path param).
type httpError struct {
	status int
	msg    string
}

func (e *httpError) Error() string { return e.msg }

func badRequest(format string, args ...any) error {
	return &httpError{status: http.StatusBadRequest, msg: fmt.Sprintf(format, args...)}
}

// decodeJSON reads exactly one JSON object, rejecting unknown fields and
// oversized bodies.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) error {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(dst); err != nil {
		var mbe *http.MaxBytesError
		switch {
		case errors.Is(err, io.EOF):
			return badRequest("request body is empty")
		case errors.As(err, &mbe):
			return &httpError{status: http.StatusRequestEntityTooLarge, msg: "request body too large"}
		default:
			return badRequest("invalid JSON: %v", err)
		}
	}
	if dec.More() {
		return badRequest("request body must contain a single JSON object")
	}
	return nil
}
