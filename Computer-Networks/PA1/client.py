import argparse
import socket
import struct

def create_packet(version, header_length, service_type, payload):
    # Checking service type for proper payload encoding
    if service_type == 1:
        payload_data = struct.pack('!I', int(payload))
    elif service_type == 2:
        payload_data = struct.pack('!f', float(payload))
    elif service_type == 3:
        payload_data = payload.encode('utf-8')
    else:
        raise ValueError('Incorrect Value Type')
    
    # Creating header
    header_format = 'BBBH'
    payload_length = len(payload_data)
    header_data = struct.pack(header_format, version, header_length, service_type, payload_length)
    # Attaching payload
    packet = header_data + payload_data

    return packet

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Client for packet creation and sending.")
    parser.add_argument('--version', type=int, required=True, help='Packet version')
    parser.add_argument('--header_length', type=int, required=True, help='Length of the packet header')
    parser.add_argument('--service_type', type=int, required=True, help='Service type of the payload (1 for int, 2 for float, 3 for string)')
    parser.add_argument('--payload', type=str, required=True, help='Payload to be packed into the packet')
    parser.add_argument('--host', type=str, default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=12345, help='Server port')

    args = parser.parse_args()

    # Create and send packet using the create_packet function
    packet = create_packet(args.version, args.header_length, args.service_type, args.payload)

    # Connect to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((args.host, args.port))

        while True:
            # Send the packet
            s.send(packet)
            
            # Receive the packet
            response = s.recv(1024)

            header_format = 'BBBH'
            header_size = struct.calcsize(header_format)
            header_data = response[:header_size]
            payload_data = response[header_size:]

            version, header_length, service_type, payload_length = struct.unpack(header_format, header_data)
            
            # Print header
            print(f"Received Header - Version: {version}, Header Length: {header_length}, Service Type: {service_type}, Payload Length: {payload_length}")
            
            # Checking service type for proper payload decoding and printing payload
            if service_type == 1:
                payload = struct.unpack('!I', payload_data)[0]
            elif service_type == 2:
                payload = struct.unpack('!f', payload_data)[0]
            elif service_type == 3:
                payload = payload_data.decode('utf-8')
            else:
                raise ValueError('Incorrect Value Type')

            print(f"Received Payload: {payload}")
            break