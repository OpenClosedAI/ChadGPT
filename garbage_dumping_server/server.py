#!/usr/bin/env python3

import os
import json
import uuid
import base64
import random
import fcntl
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# List of emojis to choose from for random emoji generation
EMOJIS = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇", 
    "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚", 
    "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🤩", 
    "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣", 
    "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬", 
    "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥", "😓", "🤗", 
    "🤔", "🤭", "🤫", "🤥", "😶", "😐", "😑", "😬", "🙄", "😯", 
    "😦", "😧", "😮", "😲", "🥱", "😴", "🤤", "😪", "😵", "🤐", 
    "🥴", "🤢", "🤮", "🤧", "😷", "🤒", "🤕", "🤑", "🤠", "💩",
    "👻", "💀", "☠️", "👽", "👾", "🤖", "🎃", "😺", "😸", "😹",
    "😻", "😼", "😽", "🙀", "😿", "😾", "🐱", "🐶", "🐭", "🐹",
    "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐸"
]

def get_random_emojis(count=3):
    """Generate a string of random emojis"""
    return ''.join(random.choices(EMOJIS, k=count))

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
            
            return next_id  # Return the new ID, not the current one
        except Exception as e:
            # Release the lock in case of error
            fcntl.flock(f, fcntl.LOCK_UN)
            logger.error(f"Error getting next query ID: {e}")
            return 0

def reset_query_id():
    """Reset the query ID counter to 11 to avoid conflicts with existing directories"""
    last_query_path = os.path.join('db', 'last-query.txt')
    with open(last_query_path, 'w') as f:
        f.write('11')  # Start from 12 for the next request

class RequestHandler(BaseHTTPRequestHandler):
    def _set_response(self, content_type='text/plain'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()
    
    def _handle_robots_txt(self):
        """Handle requests for robots.txt"""
        robots_txt_path = 'robots.txt'
        if os.path.exists(robots_txt_path):
            with open(robots_txt_path, 'r') as f:
                robots_content = f.read()
            self._set_response(content_type='text/plain')
            self.wfile.write(robots_content.encode('utf-8'))
            logger.info("Served robots.txt")
            return True
        return False
        
    def _handle_request(self):
        # Check if this is a request for robots.txt
        if self.path == '/robots.txt':
            if self._handle_robots_txt():
                return
        
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
        
        # Get user agent
        user_agent = self.headers.get('User-Agent', '')
        
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
        
        # Print user agent, request, and in parameter to console
        print(f"\n=== REQUEST {query_id} ===")
        print(f"User-Agent: {user_agent}")
        print(f"Request: {self.command} {self.path}")
        if in_param:
            print(f"In parameter: {in_param}")
        
        # Generate response
        # Base64 encode the 'in' parameter if it exists, otherwise use an empty string
        base64_request = base64.b64encode(in_param.encode('utf-8')).decode('utf-8') if in_param else ""
        random_emojis = get_random_emojis(3)
        response_text = f"42: {base64_request}:{random_emojis}"
        
        # Print response to console
        print(f"Response: {response_text}")
        print("=" * 20)
        
        # Send response
        self._set_response()
        self.wfile.write(response_text.encode('utf-8'))
    
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

def run_server(host='0.0.0.0', port=8080):
    """
    Run the HTTP server that logs both structured and raw HTTP requests.
    This is the main entry point for the server.
    """
    # Create db directory if it doesn't exist
    os.makedirs('db', exist_ok=True)
    
    # Reset the query ID to avoid conflicts with existing directories
    reset_query_id()
    
    server_address = (host, port)
    httpd = HTTPServer(server_address, RequestHandler)
    logger.info(f'HTTP server listening on {host}:{port}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
    httpd.server_close()
    logger.info('Server stopped')

if __name__ == '__main__':
    run_server()