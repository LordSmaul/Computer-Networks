import argparse
import socket
import struct
import random
import time
import re
from datetime import datetime
import RPi.GPIO as GPIO

HEADER_FORMAT = '>III'

# for message logging
def message_log(logfile, message):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    with open(logfile, 'a') as log_file:
        log_file.write(f"[{timestamp}] {message}")
        
# create packet from parameters
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
    args.add_argument("-p", "--port", type=int, default=12345, help='Server port')
    args.add_argument("-l", "--logfile", type=str, default='server_log.txt', help='Log file location')
    args = args.parse_args()
    
    host = 'localhost'
    port = args.port
    logfile = args.logfile
    SEQ_NUM = random.randint(0, 100)
    
    # GPIO code
    PIN = 16
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PIN,GPIO.OUT, initial=GPIO.LOW)
    
    while True: # keep server running
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.bind((host, port))
                message_log(logfile, f"Server listening on {host}:{port}\n")
                print('Server listening on', host, ':', port, '\n')
                
                while True:
                    try:
                        # receive SYN
                        header_data, payload_data, ADDRESS = receive_packet(s)
                        if ADDRESS[1] < 1024 or ADDRESS[1] > 65535:
                            raise Exception(f'ERROR: wrong port number: {ADDRESS[1]}... Exiting')
                        cl_seq_num, cl_ack_num, cl_ack, cl_syn, cl_fin, payload = unpack_packet(header_data, payload_data)
                        print("SYN Recieved")
                        
                        # send ACK|SYN
                        header_data, payload_data = create_packet(sequence_number=SEQ_NUM, ack_number=cl_seq_num+1, syn=1, ack=1)
                        s.sendto(header_data, ADDRESS)
                        s.sendto(payload_data, ADDRESS)
                        print("Sending ACK|SYN")
                        
                        # receive ACK
                        header_data, payload_data, _ = receive_packet(s)
                        cl_seq_num, cl_ack_num, cl_ack, cl_syn, cl_fin, payload = unpack_packet(header_data, payload_data)
                        print("ACK Received")
                        
                        # receive duration and number of blinks
                        header_data, payload_data, _ = receive_packet(s)
                        cl_seq_num, cl_ack_num, cl_ack, cl_syn, cl_fin, payload = unpack_packet(header_data, payload_data)
                        duration, blinks = [int(match.group()) for match in re.finditer(r'\b\d+\b', payload)]
                        message_log(logfile, f'Duration: {duration}, Blinks: {blinks}\n')
                        print(f'Duration: {duration}, Blinks: {blinks}')
                        
                        # send ACK for duration and blinks
                        header_data, payload_data = create_packet(sequence_number=SEQ_NUM, ack_number=cl_seq_num + 1, ack=1, payload=f'Duration: {duration} Blinks: {blinks}')
                        s.sendto(header_data, ADDRESS)
                        s.sendto(payload_data, ADDRESS)
                        print("Sent ACK")
                        
                        # get payload for when motion is detected
                        header_data, payload_data, _ = receive_packet(s)
                        cl_seq_num, cl_ack_num, cl_ack, cl_syn, cl_fin, payload = unpack_packet(header_data, payload_data)
                        
                        # process payload for detected motion
                        if payload == ':MotionDetected':
                            message_log(logfile, f"Payload: {payload}\n")
                            i = 0
                            while i < blinks: # blink LED
                                time.sleep(0.1)
                                print('Blinking')
                                GPIO.output(PIN, GPIO.HIGH)
                                time.sleep(duration)
                                GPIO.output(PIN, GPIO.LOW)
                                time.sleep(1)
                                
                                # send ACK
                                header_data, payload_data = create_packet(sequence_number=SEQ_NUM, ack_number=cl_seq_num + 1, ack=1)
                                s.sendto(header_data, ADDRESS)
                                s.sendto(payload_data, ADDRESS)
                                print("Sent ACK")
                                
                                i += 1
                                
                        # receive FIN
                        header_data, payload_data, _ = receive_packet(s)
                        cl_seq, cl_ack, cl_ack, cl_syn, cl_fin, payload = unpack_packet(header_data, payload_data)
                        message_log(logfile, f":Interaction with server ({host}:{port}) completed\n")
                        print("FIN Received\n")
                    # if socket is closed, just keep listening for connections without closing server
                    except socket.error as e:
                        continue
                    except Exception as x:
                        print(f"Error: {x}")
                        message_log(logfile, f"Error: {x}\n")
                        continue
                     
        except Exception as fatal_error:
            print(f"Critical error: {fatal_error}")
            message_log(logfile, f"Critical error: {fatal_error}\n")
            exit(1)