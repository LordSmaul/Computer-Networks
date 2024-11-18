import socket
import struct

def unpack_packet(conn, header_format):
    # Receiving header data
    header_data = conn.recv(struct.calcsize(header_format))
    if not header_data:
        return None
    # Unpacking header information
    version, header_length, service_type, payload_length = struct.unpack(header_format, header_data)
    # Recieving Payload
    payload_data = conn.recv(payload_length)
    if not payload_data:
        return None
    # Checking service type for proper payload unpacking
    if service_type == 1:
        payload = struct.unpack('!I', payload_data)[0]
    elif service_type == 2:
        payload = struct.unpack('!f', payload_data)[0]
    elif service_type == 3:
        payload = payload_data.decode('utf-8')
    else:
        raise ValueError('Incorrect Service Type')

    # Return header string
    packet_header_as_string = (f"Version: {version}, Header Length: {header_length}, Service Type: {service_type}, Payload_length: {payload_length}\nPayload: {payload}")
    return packet_header_as_string

if __name__ == '__main__':
    host = 'localhost'
    port = 12345

    # Fixed length header -> Version (1 byte), Header Length (1 byte), Service Type (1 byte), Payload Length (2 bytes)
    header_format = 'BBBH'

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        while True: # Keep server running
            conn, addr = s.accept()
            with conn:
                print(f"Connected by: {addr}")
                while True:
                    try:
                        # Receive/unpack packet using the unpack_packet function
                        payload_string = unpack_packet(conn, header_format)
                        if payload_string is None:
                            print('No Payload has been received')
                            break
                        else:
                            print(payload_string)

                        # Creating header
                        version = 1
                        header_length = 4
                        service_type = 3
                        payload = 'Message Recieved'
                        payload_length = len(payload)

                        header_data = struct.pack(header_format, version, header_length, service_type, payload_length)

                        # Add payload
                        client_string = header_data + payload.encode('utf-8')

                        # Send to client
                        conn.send(client_string)
                          
                    except ValueError as e:
                        print('ValueError:', e)
                    except:
                        print("Connection closed or an error occurred")
                        break