# Gunicorn configuration file
import multiprocessing

# Server socket
bind = "0.0.0.0:${PORT:-5000}"

# Worker processes
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)  # Max 4 workers to avoid excessive memory usage
worker_class = "gthread"
threads = 2
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
preload_app = True  # Load application code before forking worker processes
reload = False  # Disable auto-reload in production

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log errors to stderr
loglevel = "info"

# Process naming
proc_name = "restaurant_app"
