# How to run the chat program
1. Navigate into the chat directory in terminal
2. Make a new key with the following command
   openssl req -x509 -newkey rsa:2048 -keyout cert.pem -out cert.pem -days 365 -nodes
3. Start the server using the following command in a terminal  
   python3 server.py --port=9988
4. Start a client using the following command in a new terminal  
   python3 client.py --port=9988
5. Start another client using the same command in a new terminal(following)  
   python3 client.py --port=9988
6. If you want to terminate server of clients press   
   'control + c' on mac
   'ctrl + c' on windows and linux


Note python 3 higher than 3.7 must be installed on the device in order to run this program

