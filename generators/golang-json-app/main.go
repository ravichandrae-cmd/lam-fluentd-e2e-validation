package main

import (
	"log/slog"
	"os"
	"time"
)

func main() {
	// Initialize a structured JSON logger
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

	// Output some sample logs matching our test scenarios
	logger.Info("Application started", 
		slog.String("component", "initializer"), 
		slog.String("version", "1.0.0"),
	)
	
	time.Sleep(1 * time.Second)
	
	logger.Info("Processed incoming request", 
		slog.String("path", "/api/v1/health"), 
		slog.String("remote_ip", "192.168.1.10"), 
		slog.String("method", "GET"), 
		slog.Int("status", 200),
	)
	
	time.Sleep(1 * time.Second)
	
	logger.Warn("Database connection delayed", 
		slog.String("component", "db"), 
		slog.Int("latency", 450000000),
	)
	
	time.Sleep(1 * time.Second)
	
	logger.Error("Failed to fetch user profile", 
		slog.String("component", "auth"), 
		slog.String("error", "timeout"), 
		slog.Int("user_id", 4019),
	)
}
