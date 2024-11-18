import argparse
import socket
import struct
import time
import random
from datetime import datetime
import RPi.GPIO as GPIO

HEADER_FORMAT = '>III'

# for message logging
def message_log(logfile, message):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    with open(logfile, 'a') as log_file:
        log_file.write(f"[{timestamp}] {message}")
        
# create packet from from parameters
def create_packet(**kwargs):
    # get values from parameters
    sequence_number = kwargs.get('sequence_number', 0)
    ack_number = kwargs.get('ack_number', 0)
    payload = kwargs.get('payload', '\x00')
    ack = kwargs.get('ack', 0)
    syn = kwargs.get('syn', 0)
    fin = kwargs.get('fin', 0)

    # get flag values
    flags = 0
    flags |= (ack << 2)
    flags |= (syn << 1)
    flags |= fin

    # pack header and payload
    header_data = struct.pack(HEADER_FORMAT, sequence_number, ack_number, flags)
    payload_data = payload.encode('utf-8').ljust(32, b'\x00')
        
    message_log(logfile, f"\"SEND\" <{sequence_number}> <{ack_number}> [{ack}] [{syn}] [{fin}]\n")

    return header_data, payload_data

# unpack packet information
def unpack_packet(header_data, payload_data):
    # unpack header
    sequence_number, ack_number, flags = struct.unpack(HEADER_FORMAT, header_data)
    # extract flag bits
    flags = flags & 0b111
    ack = (flags >> 2) & 0b1
    syn = (flags >> 1) & 0b1
    fin = flags & 0b1
    # receive and decode payload
    payload = payload_data.decode('utf-8').rstrip('\x00')
    message_log(logfile, f"\"RECV\" <{sequence_number}> <{ack_number}> [{ack}] [{syn}] [{fin}]\n")

    return sequence_number, ack_number, ack, syn, fin, payload

# receive packet
def receive_packet(s):
    # receive header and payload
    header_data, addr = s.recvfrom(12)
    payload_data, _ = s.recvfrom(32)

    return header_data, payload_data, addr


if __name__ == '__main__':
    # parse arguments
    args = argparse.ArgumentParser(description="Server for receiving packets")
    args.add_argument("-s", "--server", type=str, default='localhost', help='Server IP')
    args.add_argument("-p", "--port", type=int, default=12345, help='Server port')
    args.add_argument("-l", "--logfile", type=str, default='client_log.txt', help='Log file location')
    args = args.parse_args()
    
    logfile = args.logfile
    
    # GPIO code
    PIN = 32
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PIN,GPIO.IN)
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # connect to server
            s.connect((args.server, args.port))
            SEQ_NUM = random.randint(0, 100)
            
            # send SYN
            header_data, payload_data = create_packet(sequence_number=SEQ_NUM, syn=1)
            s.send(header_data)
            s.send(payload_data)
            print('Sent SYN')
            
            # receive SYN|ACK
            header_data, payload_data, _ = receive_packet(s)
            ser_seq_num, ser_ack_num, ser_ack, ser_syn, ser_fin, payload = unpack_packet(header_data, payload_data)
            print('SYN|ACK Received')
            
            # send ACK
            header_data, payload_data = create_packet(sequence_number=ser_ack_num, ack_number=ser_seq_num + 1, ack=1)
            s.send(header_data)
            s.send(payload_data)
            print('Sent ACK')
            
            # Send duration and blinks
            header_data, payload_data = create_packet(sequence_number=ser_ack_num, ack_number=ser_seq_num + 1, payload='Duration: 1, Blinks: 5')
            s.send(header_data)
            s.send(payload_data)
            print('Sent Duration and Blinks')
            
            # receive ACK for duration and blinks - logs payload
            header_data, payload_data, _ = receive_packet(s)
            ser_seq_num, ser_ack_num, ser_ack, ser_syn, ser_fin, payload = unpack_packet(header_data, payload_data)
            message_log(logfile, payload + '\n')
            print(payload)
            print('ACK Received')
            
            # listen for motion detected
            listening = 1
            while listening:
                time.sleep(0.1)
                current_state = GPIO.input(PIN)
                if current_state == 1:
                    
                    # create packet for detected motion
                    header_data, payload_data = create_packet(sequence_number=ser_ack_num, ack_number=ser_seq_num + 1, payload=':MotionDetected')
                    s.send(header_data)
                    s.send(payload_data)
                    print("Sending motion update")

                    # receive ACK for duration and number of blinks
                    header_data, payload_data, _ = receive_packet(s)
                    ser_seq_num, ser_ack_num, ser_ack, ser_syn, ser_fin, payload = unpack_packet(header_data, payload_data)
                    print('ACK Received')
                    listening = 0
                    
            # send FIN
            header_data, payload_data = create_packet(sequence_number=ser_ack_num, ack_number=ser_seq_num + 1, fin=1)
            s.send(header_data)
            s.send(payload_data)
            print("Send FIN")
           
    except KeyboardInterrupt:
        print("\nExiting program.")
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)
    finally:
        GPIO.cleanup()
        print('Connection closed')