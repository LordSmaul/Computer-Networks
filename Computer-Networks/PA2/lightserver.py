import argparse
import socket
import struct

def unpack_packet(conn, header_format):
    # unpack header
    header_data = conn.recv(struct.calcsize(header_format))
    version, type, message_length = struct.unpack(header_format, header_data)
    # decode message
    payload_data = conn.recv(message_length)
    message = payload_data.decode('utf-8')
    
    if version != 17: # version mismatch
        return None
    else: # return values in tuple
        return (version, type, message_length, message)

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
    parser.add_argument('-p', '--port', type=int, default=12345, help='Sever port')
    parser.add_argument('-l', '--logfile', type=str, required=True, help='Log file location')
    
    args = parser.parse_args()
    
    # parsed arguments
    host = 'localhost'
    port = args.port
    logfile = args.logfile
    
    # Fixed header length -> Version (4 bytes), Message type (4 bytes), Message Length (4 bytes)
    header_format = 'III'
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        while True: # Keep server running
            conn, addr = s.accept()
            with open(logfile, 'a') as server_file:
                server_file.write(f'Received connection from (IP, PORT): ({host}, {port})\n')
                with conn:
                    while True:
                        try:
                            payload = unpack_packet(conn, header_format)
                            
                            if payload is None: # Version mismatch
                                server_file.write('VERSION MISMATCH\n')
                                break
                            elif payload[3] == 'HELLO': # Initial hello response from client
                                server_file.write(f'Received Data: version: {payload[0]} message_type: {payload[1]} length: {payload[2]}\nVERSION ACCEPTED\n')
                                # sending hello response back to client
                                hello_packet = create_packet(17, 1, 'HELLO')
                                conn.send(hello_packet)
                            else: # support command and sending success
                                server_file.write(f'Received Data: version: {payload[0]} message_type: {payload[1]} length: {payload[2]}\nVERSION ACCEPTED\n')
                                if (payload[1] == 1 and payload[3] == 'LIGHTON') or (payload[1] == 2 and payload[3] == 'LIGHTOFF'): # supported message types
                                    server_file.write(f'EXECUTING SUPPORTED COMMAND: {payload[3]}\n')
                                     # sending success message back to client
                                    server_file.write('Returning SUCCESS\n')
                                    success_packet = create_packet(17, 1, 'SUCCESS')
                                    conn.send(success_packet)
                                else: # unsupported message types
                                    server_file.write(f'IGNORING UNKNOWN COMMAND: {payload[3]}\n')
                                    unsuccess_packet = create_packet(17, 1, 'UNSUCCESS')
                                    conn.send(unsuccess_packet)
                        except:
                            print('Error occurred or Connection closed')
                            break