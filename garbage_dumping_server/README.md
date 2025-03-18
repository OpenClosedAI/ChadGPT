# HTTP Request Logger Server

A simple HTTP server that logs all request details and returns a formatted response.

## Features

- Responds to any HTTP endpoint and method (GET, POST, PUT, DELETE, etc.)
- Logs all request details to a structured file system
- Captures and stores raw HTTP requests
- Assigns sequential query IDs to each request
- Prints user agent, request, and response details to console
- Returns a response in the format `42: {BASE64REQUEST}:{RANDOMEMOJIS}`
- Serves a permissive robots.txt file

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

Using Python directly:
```bash
python server.py
```

Using Poetry:
```bash
poetry run server
```

This will start the HTTP server on port 8080.

### Making Requests

You can make any HTTP request to the server:

```
http://localhost:8080/any/path?in=hello
```

If you include the "in" parameter, its value will be:
1. Printed to the console
2. Base64 encoded in the response

### Response Format

The server responds with a string in the format:
```
42: {BASE64REQUEST}:{RANDOMEMOJIS}
```

Where:
- `BASE64REQUEST` is the base64-encoded value of the "in" parameter (or empty if not provided)
- `RANDOMEMOJIS` is a random selection of 3 emojis

### Console Output

For each request, the server prints:
```
=== REQUEST {QUERY_ID} ===
User-Agent: {USER_AGENT}
Request: {METHOD} {PATH}
In parameter: {IN_PARAMETER}  # Only if provided
Response: {RESPONSE}
====================
```

### Stopping the Server

Press `Ctrl+C` in the terminal to stop the server or use:

```bash
pkill -f "python server.py" || true
```

Or if running with Poetry:

```bash
pkill -f "poetry run server" || true
```

## Example Requests

```bash
curl "http://localhost:8080/test/endpoint?in=hello&param2=world"
```

```bash
curl -X POST -d "content=🦄" "http://localhost:8080/unicorn?in=magic"
```

## Robots.txt

The server provides a permissive robots.txt file that allows all web crawlers to access all paths:
```
User-agent: *
Disallow:
```

## Query ID System

Each request is assigned a sequential query ID that is stored in `db/last-query.txt`. The system:

1. Reads the current value from the file
2. Increments it for the next request
3. Uses file locking to ensure thread safety in concurrent environments
4. Creates directory names in the format `{QUERY_ID}:{UUID}`

This allows for easy chronological tracking of requests while maintaining unique identifiers.
