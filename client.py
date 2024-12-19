import select
import signal
import socket
import sys
import argparse
import threading
import ssl

from utils import *

SERVER_HOST = 'localhost'

class ChatClient():
    def __init__(self, port, host=SERVER_HOST):
        self.name = 'unknown user'
        self.connected = False
        self.host = host
        self.port = port
        self.loged = False
        self.stop_thread = threading.Event()  # Use an Event for thread signaling

        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.load_verify_locations('cert.pem')
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.set_ciphers('AES128-SHA')
    

        # Connect to server at port
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock = self.context.wrap_socket(self.sock, server_hostname=host)
            self.sock.connect((host, self.port))
            # Check if the server has less than 2 clients
            # If less than two, client is accpted
            if receive(self.sock) == "accepted" :
                print(f'Now connected to chat server@ port {self.port}')
                self.connected = True
            # If not, client is rejected and socket is closed
            else :
                print(f'Already two users joined the server')
                self.sock.close()
        # Error happens in the connection, exit the program
        except socket.error as e:
            print(f'Failed to connect to chat server @ port {self.port}: {e}')
            sys.exit(1)

    def run(self):
        try :
            while self.connected:
                # If a client is not loged in, prompt login
                if not self.loged:
                    self.registerOrLogin()

                # Display prompt
                sys.stdout.write(f'{self.name} (Me)> ')
                sys.stdout.flush()

                # Wait for input from stdin and socket
                readable, writeable, exceptional = select.select([self.sock, sys.stdin], [], [])

                for sock in readable:
                    # Receive message from the server and display
                    if sock == self.sock:
                        data = receive(self.sock)
                        if not data:
                            print('\nServer closed the connection.')
                            self.connected = False
                            break
                        else:
                            sys.stdout.write('\r' + ' ' * len(f'{self.name} (Me)> ') + '\r')
                            sys.stdout.write(f'{data}\n')
                            sys.stdout.flush()

                    # Send message to the server
                    elif sock == sys.stdin:
                        data = sys.stdin.readline().strip()
                        if data:
                            send(self.sock, data)
                            
        except KeyboardInterrupt:
            # Handle Ctrl+C 
            print("\nShutting down client...")
    
        finally:
            # Ensure cleanup is always called
            self.cleanup(None, None)

    def registerOrLogin(self):
        # Iteratively run until the user is loged in
        while True:  
            sys.stdout.write(f'Do you want to register or log in? (Type register or login) > ')
            sys.stdout.flush()

            # Get what action the user wants to do 
            answer = sys.stdin.readline().strip()
            send(self.sock, answer)

            if answer == 'register':
                sys.stdout.write(f'Type your username > ')
                sys.stdout.flush()
                username = sys.stdin.readline().strip()
                send(self.sock, username)

                sys.stdout.write(f'Type your password > ')
                sys.stdout.flush()
                password = sys.stdin.readline().strip()
                send(self.sock, password)

                # Check if the server successfully executed action
                registered = receive(self.sock)
                if registered == 1:
                    sys.stdout.write(f'Successfully registered\n')
                    sys.stdout.flush()
                    
                else:
                    sys.stdout.write(f'Username already exists\n')
                    sys.stdout.flush()

            elif answer == 'login':
                sys.stdout.write(f'Type your username > ')
                sys.stdout.flush()
                username = sys.stdin.readline().strip()
                send(self.sock, username)

                sys.stdout.write(f'Type your password > ')
                sys.stdout.flush()
                password = sys.stdin.readline().strip()
                send(self.sock, password)

                logedin = receive(self.sock)
                if logedin == 1:
                    sys.stdout.write(f'Successfully logged in\n')
                    sys.stdout.flush()
                    # Save the username so that it can be displayed in the promp
                    self.name = username
                    self.loged = True
                    return  # Exit the loop on successful login
                else:
                    sys.stdout.write(f'Incorrect details\n')
                    sys.stdout.flush()
            else:
                # the user enters somthing incorrect (not register or login)
                sys.stdout.write(f'Enter register or login\n')
                sys.stdout.flush()

    def cleanup(self, signum, frame):
        # Cleanup resources before shutting down.
        self.connected = False
        if self.sock:
            self.sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', action="store", dest="port", type=int, required=True)
    given_args = parser.parse_args()

    port = given_args.port
    client = ChatClient(port=port)
    client.run()
