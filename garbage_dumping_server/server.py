#!/usr/bin/env python3

import os
import json
import uuid
import socket
import threading
import logging
import fcntl
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_next_query_id():
    """
    Get the next sequential query ID from last-query.txt.
    Creates the file with initial value 0 if it doesn't exist.
    Uses file locking to ensure thread safety.
    """
    last_query_path = os.path.join('db', 'last-query.txt')
    
    # Create db directory if it doesn't exist
    os.makedirs('db', exist_ok=True)
    
    # Create the file if it doesn't exist
    if not os.path.exists(last_query_path):
        with open(last_query_path, 'w') as f:
            f.write('0')
    
    # Open the file for reading and writing
    with open(last_query_path, 'r+') as f:
        # Acquire an exclusive lock
        fcntl.flock(f, fcntl.LOCK_EX)
        
        try:
            # Read the current value
            current_id = int(f.read().strip() or '0')
            
            # Increment the value
            next_id = current_id + 1
            
            # Seek to the beginning of the file and write the new value
            f.seek(0)
            f.truncate()
            f.write(str(next_id))
            
            # Release the lock
            fcntl.flock(f, fcntl.LOCK_UN)
            
            return current_id
        except Exception as e:
            # Release the lock in case of error
            fcntl.flock(f, fcntl.LOCK_UN)
            logger.error(f"Error getting next query ID: {e}")
            return 0

class RequestHandler(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
    def _handle_request(self):
        # Get current date for directory structure
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        
        # Get the next sequential query ID
        query_id = get_next_query_id()
        
        # Generate UUID
        request_id = str(uuid.uuid4())
        
        # Create directory name with sequential ID and UUID
        dir_name = f"{query_id}:{request_id}"
        
        # Parse URL and query parameters
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        # Extract 'in' parameter if it exists
        in_param = query_params.get('in', [''])[0]
        if in_param:
            print(f"in parameter: {in_param}")
        
        # Collect request data
        request_data = {
            'query_id': query_id,
            'timestamp': now.isoformat(),
            'method': self.command,
            'path': self.path,
            'headers': dict(self.headers),
            'query_params': query_params,
            'client_address': self.client_address[0],
            'client_port': self.client_address[1]
        }
        
        # Get request body if it exists
        content_length = int(self.headers.get('Content-Length', 0))
        body = b''
        if content_length > 0:
            body = self.rfile.read(content_length)
            request_data['body'] = body.decode('utf-8', errors='replace')
            try:
                # Try to parse as JSON
                request_data['body_json'] = json.loads(request_data['body'])
            except json.JSONDecodeError:
                pass
        
        # Create directory structure
        storage_dir = os.path.join('db', year, month, day, dir_name)
        os.makedirs(storage_dir, exist_ok=True)
        
        # Save structured request data to file
        json_file_path = os.path.join(storage_dir, 'request.json')
        with open(json_file_path, 'w') as f:
            json.dump(request_data, f, indent=2)
        
        # Capture and save raw HTTP request
        raw_request = f"{self.command} {self.path} {self.request_version}\r\n"
        for header, value in self.headers.items():
            raw_request += f"{header}: {value}\r\n"
        raw_request += "\r\n"
        
        if body:
            raw_request += body.decode('utf-8', errors='replace')
        
        # Save raw HTTP request to file
        raw_file_path = os.path.join(storage_dir, 'raw_request.txt')
        with open(raw_file_path, 'w') as f:
            f.write(raw_request)
            
        logger.info(f"Request logged to {storage_dir}")
        
        # Always return 42
        self._set_response()
        self.wfile.write("42".encode('utf-8'))
    
    def do_GET(self):
        self._handle_request()
        
    def do_POST(self):
        self._handle_request()
        
    def do_PUT(self):
        self._handle_request()
        
    def do_DELETE(self):
        self._handle_request()
        
    def do_PATCH(self):
        self._handle_request()
        
    def do_HEAD(self):
        self._handle_request()
        
    def do_OPTIONS(self):
        self._handle_request()

def run_http_server(host='0.0.0.0', port=8080):
    """
    Run the HTTP server that logs both structured and raw HTTP requests.
    """
    server_address = (host, port)
    httpd = HTTPServer(server_address, RequestHandler)
    logger.info(f'HTTP server listening on {host}:{port}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
    httpd.server_close()
    logger.info('Server stopped')

def handle_raw_client(client_socket, client_address):
    """
    Handle a client connection by reading the raw HTTP request
    and saving it to a file.
    """
    # Get current date for directory structure
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    
    # Get the next sequential query ID
    query_id = get_next_query_id()
    
    # Generate UUID
    request_id = str(uuid.uuid4())
    
    # Create directory name with sequential ID and UUID
    dir_name = f"{query_id}:{request_id}"
    
    # Create storage directory
    storage_dir = os.path.join('db', year, month, day, dir_name)
    os.makedirs(storage_dir, exist_ok=True)
    
    # Receive data from client (raw HTTP request)
    raw_data = b""
    while True:
        try:
            # Set a timeout to detect end of request
            client_socket.settimeout(0.5)
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            raw_data += chunk
            
            # Check if we've received the end of the HTTP headers and body
            if b"\r\n\r\n" in raw_data:
                headers_end = raw_data.find(b"\r\n\r\n")
                headers = raw_data[:headers_end].decode('utf-8', errors='replace')
                
                # Try to find Content-Length header
                content_length = 0
                for line in headers.split('\r\n'):
                    if line.lower().startswith('content-length:'):
                        content_length = int(line.split(':', 1)[1].strip())
                        break
                
                # Check if we've received the complete body
                if len(raw_data) >= headers_end + 4 + content_length:
                    break
                    
        except socket.timeout:
            # Timeout means we've probably received all data
            break
    
    # Convert bytes to string for storage
    raw_request = raw_data.decode('utf-8', errors='replace')
    
    # Extract 'in' parameter if it exists
    in_param = None
    if "?in=" in raw_request:
        in_param = raw_request.split("?in=", 1)[1].split("&", 1)[0].split(" ", 1)[0]
    elif "in=" in raw_request:
        in_param = raw_request.split("in=", 1)[1].split("&", 1)[0].split("\r\n", 1)[0]
    
    if in_param:
        print(f"in parameter: {in_param}")
    
    # Save raw HTTP request to file
    raw_file_path = os.path.join(storage_dir, 'raw_request.txt')
    with open(raw_file_path, 'w') as f:
        f.write(raw_request)
    
    # Try to parse the request to extract structured data
    try:
        # Parse the first line to get method, path, and version
        request_lines = raw_request.split('\r\n')
        first_line = request_lines[0].split(' ')
        method = first_line[0] if len(first_line) > 0 else "UNKNOWN"
        path = first_line[1] if len(first_line) > 1 else "/"
        version = first_line[2] if len(first_line) > 2 else "HTTP/1.1"
        
        # Parse headers
        headers = {}
        header_end = 0
        for i, line in enumerate(request_lines[1:], 1):
            if not line:
                header_end = i
                break
            if ': ' in line:
                key, value = line.split(': ', 1)
                headers[key] = value
        
        # Parse query parameters
        query_params = {}
        if '?' in path:
            path_part, query_part = path.split('?', 1)
            for param in query_part.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    if key in query_params:
                        if isinstance(query_params[key], list):
                            query_params[key].append(value)
                        else:
                            query_params[key] = [query_params[key], value]
                    else:
                        query_params[key] = [value]
        
        # Extract body
        body = '\r\n'.join(request_lines[header_end+1:]) if header_end < len(request_lines) else ""
        
        # Create structured data
        structured_data = {
            'query_id': query_id,
            'timestamp': now.isoformat(),
            'method': method,
            'path': path,
            'version': version,
            'headers': headers,
            'query_params': query_params,
            'client_address': client_address[0],
            'client_port': client_address[1]
        }
        
        if body:
            structured_data['body'] = body
            try:
                # Try to parse as JSON
                structured_data['body_json'] = json.loads(body)
            except json.JSONDecodeError:
                pass
        
        # Save structured data to file
        json_file_path = os.path.join(storage_dir, 'request.json')
        with open(json_file_path, 'w') as f:
            json.dump(structured_data, f, indent=2)
    
    except Exception as e:
        # If parsing fails, save a simple metadata file
        metadata = {
            'query_id': query_id,
            'timestamp': now.isoformat(),
            'client_address': client_address[0],
            'client_port': client_address[1],
            'raw_request_size': len(raw_data),
            'parse_error': str(e)
        }
        
        # Save metadata to file
        meta_file_path = os.path.join(storage_dir, 'metadata.json')
        with open(meta_file_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    logger.info(f"Raw request logged to {storage_dir}")
    
    # Always respond with 42
    response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\n42"
    client_socket.send(response.encode('utf-8'))
    client_socket.close()

def run_raw_server(host='0.0.0.0', port=8081):
    """
    Run a socket-based HTTP server that captures raw HTTP requests.
    """
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        logger.info(f'Raw HTTP server listening on {host}:{port}')
        
        while True:
            client_socket, client_address = server_socket.accept()
            logger.info(f'Accepted connection from {client_address[0]}:{client_address[1]}')
            
            # Handle client in a new thread
            client_thread = threading.Thread(
                target=handle_raw_client,
                args=(client_socket, client_address)
            )
            client_thread.daemon = True
            client_thread.start()
            
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
    except Exception as e:
        logger.error(f'Error: {e}')
    finally:
        server_socket.close()
        logger.info('Server stopped')

def run_both_servers():
    """
    Run both the HTTP server and the raw socket server in separate threads.
    """
    # Create db directory if it doesn't exist
    os.makedirs('db', exist_ok=True)
    
    # Start HTTP server in a thread
    http_thread = threading.Thread(target=run_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    # Start raw server in the main thread
    run_raw_server()

if __name__ == '__main__':
    run_both_servers()