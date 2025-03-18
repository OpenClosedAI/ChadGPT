# HTTP Request Logger Server

A simple HTTP server that logs all request details and always returns "42" as a response.

## Features

- Responds to any HTTP endpoint and method (GET, POST, PUT, DELETE, etc.)
- Logs all request details to a structured file system
- Captures and stores raw HTTP requests
- Assigns sequential query IDs to each request
- Prints the "in" parameter to console if provided
- Always returns "42" as the response
- Runs both a high-level HTTP server (port 8080) and a low-level socket-based server (port 8081)

## Directory Structure

Logs are stored in the following structure:
```
db/
  last-query.txt           # Stores the last used query ID
  YEAR/
    MONTH/
      DAY/
        QUERY_ID:UUID/     # Directory name includes sequential ID and UUID
          request.json     # Structured request data
          raw_request.txt  # Raw HTTP request
```

## Usage

### Starting the Server

```bash
python server.py
```

This will start both servers:
- High-level HTTP server on port 8080
- Low-level socket-based server on port 8081

### Making Requests

You can make any HTTP request to either server:

```
http://localhost:8080/any/path?in=hello  # High-level server
http://localhost:8081/any/path?in=hello  # Low-level server
```

If you include the "in" parameter, its value will be printed to the console.

### Stopping the Server

Press `Ctrl+C` in the terminal to stop the server or use:

```bash
pkill -f "python server.py" || true
```

## Example Requests

### High-Level Server
```bash
curl "http://localhost:8080/test/endpoint?in=hello&param2=world"
```

### Low-Level Socket Server
```bash
curl -X POST -d "content=🦄" "http://localhost:8081/unicorn?in=magic"
```

This will:
1. Print "in parameter: hello" or "in parameter: magic" to the console
2. Assign a sequential query ID to the request
3. Save both structured JSON data and raw HTTP request to files
4. Return "42" as the response

## Query ID System

Each request is assigned a sequential query ID that is stored in `db/last-query.txt`. The system:

1. Reads the current value from the file
2. Increments it for the next request
3. Uses file locking to ensure thread safety in concurrent environments
4. Creates directory names in the format `{QUERY_ID}:{UUID}`

This allows for easy chronological tracking of requests while maintaining unique identifiers.
