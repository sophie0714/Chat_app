import json
import os
import select
import socket
import sys
import signal
import argparse
import ssl
import hashlib

from utils import *

SERVER_HOST = 'localhost'
USER_FILE = 'users.json'

class ChatServer(object):
    def __init__(self, port, backlog=2):
        self.clientmap = {}
        self.outputs = []  # list output sockets

        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.load_cert_chain(certfile="cert.pem", keyfile="cert.pem")
        self.context.load_verify_locations('cert.pem')
        self.context.set_ciphers('AES128-SHA')

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((SERVER_HOST, port))
        self.server.listen(backlog)                
        self.server = self.context.wrap_socket(self.server, server_side=True)

        # Catch keyboard interrupts
        signal.signal(signal.SIGINT, self.sighandler)

        print(f'Server listening to port: {port} ...')

        self.user_data = self.load_user_data()


    def run(self):
        inputs = [self.server]
        self.outputs = []
        running = True
        while running:
            try:
                readable, writeable, exceptional = select.select(
                    inputs, self.outputs, [])
            except select.error as e:
                break
            # Iteratively check all sockets
            for sock in readable:
                
                    sys.stdout.flush()
                    # If it is a server socket, accept clients waiting to be accepted
                    if sock == self.server:
                        client, address = self.server.accept()
                        # Only allow connection if there are less than 2 clients
                        if len(self.outputs) < 2 :
                            print(
                                f'Chat server: got connection {client.fileno()} from {address}')
                            inputs.append(client)

                            self.clientmap[client] = {"loged": False, "username": None}
                            send(client, 'accepted')
                            # More than two clients, reject connection
                        else :
                            print(
                                f'Chat server: rejected {client.fileno()} from {address}')
                            send(client, 'rejected')
                            client.close()
                    else:
                        # handle all other sockets
                        # Only logged in clients can send messages to be sent to other client
                        if self.clientmap[sock]["loged"]:
                                data = receive(sock)
                                try:
                                    if data:
                                        # Send as new client's message...
                                        msg = f'{self.get_client_name(sock)}> {data}'

                                        # Send data to all except ourself
                                        for output in self.outputs:
                                            if output != sock:
                                                send(output, msg)
                                    else:
                                        print(f'Chat server: {sock.fileno()} hung up')
                                        sock.close()
                                        inputs.remove(sock)
                                        self.outputs.remove(sock)

                                        # Sending client leaving information to others
                                        msg = f'(Now hung up: Client from {self.get_client_name(sock)})'

                                        for output in self.outputs:
                                            send(output, msg)
                                # If the error occurs, remove the socket from the server's checking list
                                except socket.error as e:
                                    # Remove
                                    inputs.remove(sock)
                                    self.outputs.remove(sock)
                        else :
                            # Register or login process
                            try:
                                # Get action
                                action = receive(sock)
                                if action == 'register':
                                    username = receive(sock)
                                    password = receive(sock)
                                    # If duplicated username, not saved
                                    if username in self.user_data :
                                        send(sock, 0) # Duplicated username
                                    else :
                                        # Encrypt the password and save into json file
                                        hashed_password = self.hash_password(password)
                                        self.user_data[username] = hashed_password
                                        self.save_user_data()
                                        send(sock, 1)

                                    
                                elif action == 'login' :
                                    username = receive(sock)
                                    password = receive(sock)
                                    # Check if username exists
                                    if username in self.user_data:
                                        hashed_password = self.hash_password(password)
                                        # Check if the hashed password matches the stored password
                                        if self.user_data[username] == hashed_password:
                                            self.clientmap[sock]["loged"] = True  # Mark client as logged in
                                            self.clientmap[sock]["username"] = username  # Store username
                                            self.outputs.append(sock) # outputs are the collection of sockets where the messages to be sent
                                            send(sock, 1)  # Login successful
                                        else:
                                            send(sock, 0)  # Incorrect password
                                    else:
                                        send(sock, 0)  # Username does not exist
                                
                            except socket.error as e:
                                # Remove
                                inputs.remove(sock)
                                
                        

        self.server.close()

    def sighandler(self, signum, frame):
        # Close all sockets
        print('\nShutting down server...')

        # Close existing client sockets
        for output in self.outputs:
            output.close()

        self.server.close()
        self.running = False

    def hash_password(self, password):
        # Hash the password using SHA-256
        sha_signature = hashlib.sha256(password.encode()).hexdigest()
        return sha_signature
    
    def save_user_data(self):
        # Save user data to a JSON file.
        with open(USER_FILE, 'w') as f:
            json.dump(self.user_data, f, indent=4)

    def load_user_data(self):
        # Load user data from a JSON file if it exists
        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r') as f:
                try:
                    return json.load(f) 
                except json.JSONDecodeError:
                    # If file is empty or invalid, return an empty dictionary
                    print("Warning: users.json is empty or invalid. Starting fresh.")
                    return {}
        return {}
    
    def get_client_name(self, sock):
        # Return the username of the client for the given socket.
        if sock in self.clientmap and self.clientmap[sock]["username"]:
            return self.clientmap[sock]["username"]
        else:
            return "Unknown"
    
    
    



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Socket Server Example with Select')
    parser.add_argument('--port', action="store",
                        dest="port", type=int, required=True)
    given_args = parser.parse_args()
    port = given_args.port

    server = ChatServer(port)
    server.run()