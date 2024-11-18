import argparse
import socket
import struct

def create_packet(version, type, payload):
    header_format = 'III'
    message = payload.encode('utf-8')
    message_length = len(message)
        
    # build packet from header data and payload
    header_data = struct.pack(header_format, version, type, message_length)
    packet = header_data + message
    return packet

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Client for packet creation and sending.")
    parser.add_argument('-s', '--server', type=str, required=True, help='Server host')
    parser.add_argument('-p', '--port', type=int, default=12345, help='Sever port')
    parser.add_argument('-l', '--logfile', type=str, required=True, help='Log file location')

    args = parser.parse_args()
    logfile = args.logfile
    
    # 'globals' for header formatting
    # Fixed header length -> Version (4 bytes), Message type (4 bytes), Message Length (4 bytes)
    header_format = 'III'
    header_size = struct.calcsize(header_format)
    
    # connect to server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((args.server, args.port))
        with open(logfile, 'a') as client_file:
            
            # creating first hello reponse to server
            hello_packet = create_packet(17, 1, 'HELLO')
            
            while True:
                # sending first hello message to server
                client_file.write('Sending HELLO Packet\n')
                s.send(hello_packet)
                
                # receiving first hello response from server
                hello_response = s.recv(1024)
                
                # decoding first hello response from server
                header_data = hello_response[:header_size]
                payload_data = hello_response[header_size:]
                message = payload_data.decode('utf-8')

                version, type, message_length = struct.unpack(header_format, header_data)
                client_file.write(f'Received Data: version: {version} message_type: {type} length: {message_length}\n')
                
                # if version is correct, print message
                if version == 17:
                    client_file.write(f'VERSION ACCEPTED \nReceived Message {message}\n')
                else:
                    client_file.write('VERSION MISMATCH\n') 
                    break
                
                # sending command to server
                command_packet = create_packet(17, 1, 'LIGHTON')
                client_file.write('Sending Command\n')
                s.send(command_packet)
                
                # decoding success message
                success_response = s.recv(1024)
                header_data = success_response[:header_size]
                payload_data = success_response[header_size:]
                message = payload_data.decode('utf-8')
                version, type, message_length = struct.unpack(header_format, header_data)
                if (message == 'UNSUCCESS'): # unsuccessful command
                    client_file.write(f'Received Data: version: {version} message_type: {type} length: {message_length}\n')
                    client_file.write(f'VERSION ACCEPTED\nReceived Message {message} \nCommand Unsuccessful\nClosing Socket\n')
                else: # successful command
                    client_file.write(f'Received Data: version: {version} message_type: {type} length: {message_length}\n')
                    client_file.write(f'VERSION ACCEPTED\nReceived Message {message} \nCommand Successful\nClosing Socket\n')
                break        