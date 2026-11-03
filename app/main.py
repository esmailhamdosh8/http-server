import socket  # noqa: F401
import threading
import time
import gzip
import sys
import os

def parse_request(request: bytes):
    head, _, body = request.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    request_line = lines[0]
    method, request_target, version = request_line.decode().split(" ")
    headers = {}
    for header in lines[1:]:
        key, _, value = header.decode().partition(":")
        headers[key.strip()] = value.strip()
    return method, request_target, version, headers, body

def build_response(method, request_target: str, version, request_headers: dict[str, str], request_body):
    close_the_connection = False
    headers = {}
    if request_target == '/':
        body = b""
        response_line = "HTTP/1.1 200 OK"
    elif request_target.startswith('/echo/'):
        body = request_target.split("/")[2].encode()
        headers['Content-Type'] = 'text/plain'
        response_line = "HTTP/1.1 200 OK"
    elif request_target.startswith('/files/'):
        file = request_target.split("/")[2]
        root_dir = os.environ["root-dir"]
        file_path = os.path.join(root_dir, file)
        if method == "GET":
            if os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    body = f.read()
                headers['Content-Type'] = 'application/octet-stream'
                response_line = "HTTP/1.1 200 OK"
            else:
                body = b""
                response_line = "HTTP/1.1 404 Not Found"
        elif method == "POST":
            with open(file_path, "wb") as f:
                f.write(request_body)
            body = b""
            response_line = "HTTP/1.1 201 Created\r\n\r\n"
    elif request_target == '/user-agent':
        body = request_headers["User-Agent"].encode()
        headers['Content-Type'] = 'text/plain'
        response_line = "HTTP/1.1 200 OK"
    else:
        body = b""
        response_line = "HTTP/1.1 404 Not Found"
    if 'Accept-Encoding' in request_headers:
        client_accepted_encodings = [encoding.strip() for encoding in request_headers['Accept-Encoding'].split(',')]
        for client_encoding in client_accepted_encodings:   
            if client_encoding in os.environ['Accepted-Encodings']:
                if client_encoding == 'gzip':
                    body = gzip.compress(body)
                headers['Content-Encoding'] = client_encoding
                break
    headers['Content-Length'] = len(body)
    if 'Connection' in request_headers and request_headers['Connection'] == 'close':
        headers['Connection'] = 'close'
        close_the_connection = True
    response_headers = "\r\n".join(f"{key}: {value}" for key, value in headers.items())
    response = f"{response_line}\r\n{response_headers}\r\n\r\n".encode() + body
        
    return response, close_the_connection


def handle_client(conn):
    while True:
        request = conn.recv(1024)
        response, close_the_connection = build_response(*parse_request(request))
        conn.sendall(response)
        if close_the_connection:
            conn.close()

def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")
    os.environ["Accepted-Encodings"] = "gzip"
    cli_args = sys.argv
    n = len(cli_args)
    for i in range(n):
        if cli_args[i] == "--directory" and i != n - 1:
            os.environ["root-dir"] = cli_args[i + 1]
            break
    # TODO: Uncomment the code below to pass the first stage
    #
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    while True:
        conn, addr = server_socket.accept() # wait for client
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()



if __name__ == "__main__":
    main()
