"""
CS 425 MP2
Will Hennessy, Stephen Herring

A python command line chat client that communicates via
reliable multicast. List all member IP addresses in config.txt
"""

import socket
import sys
from random import randint, random
from time import sleep
from thread import *
import copy


UNDELIVERED = []    # a list of all messages that have not been delivered
GROUP = []          # a list of addresses of all the group members
ACKS = {}           # a dict of id:bool indicating if the msg has been acknowledged
RECEIVED = {}       # a dict of unique_id:boolean indicating if the message has been received before
TIMESTAMPS = {}     # a dict of process_id:timestamp tracking the vector timestamp of the system
CURR_MSG_ID = 0
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # this process' socket
DELAY_TIME = 0      # average delay time (milliseconds)
DROP_RATE = 0       # probability of dropping a message (between 0 and 1.0)
ACK_MSG = "ack"     # static string



def parse_timestamp_dict(curr_timestamps):
    """ Runs through the TIMESTAMPS dict separating keys and values by commas,
        and separating each (key, value) pair with a # """
    retval = ""
    for key, value in curr_timestamps.items():
        retval += "#" + key + "," + str(value)
    return retval



def read_config_file(config_file_name):
    """ Read every line in the config file and return an array of each ip address """
    with open(config_file_name) as config_file:
        ip_addrs = config_file.readlines()
        ip_addrs = [addr.strip() for addr in ip_addrs] # remove trailing \n chars
    return ip_addrs



def parse_addr(line):
    """ Given a line from the config file, return a pair (host_ip, port) """
    # split the address into host and port
    #    host:port     i.e. localhost:8080
    ip_components = line.split(':')
    host = ip_components[0]
    try:
        host_ip = socket.gethostbyname( host )
    except socket.gaierror:
        print 'Hostname could not be resolved. Exiting'
        sys.exit()
    port = int(float(ip_components[1])) # cast port to integer
    return (host_ip, port)



def unique_id(msg_id, addr):
    """ Given the id of a message and its address, returns a string that uniquely identifies the message """
    return msg_id + str(addr[0]) + str(addr[1])



def random_delay():
    """ Sleep for a random amount of time, based on the command line parameter
        Multiply by 2 because DELAY_TIME is the average delay time - linearity of expectation
        Divide by 1000 because the parameter DELAY_TIME is in milliseconds """
    delay = float(randint(0, 2 * DELAY_TIME)) / 1000.0
    sleep(delay)



def should_drop():
    """ Determine if you should drop the message based on probability parameter """
    return random() < DROP_RATE



def unicast_receive():
    """ Receive a single message from a single client.
        Implement a randomized delay before delivering the message """
    content, addr = SOCK.recvfrom(4096)
    components = content.split("#")     # format is 'msg_id#message#sender_addr#timestamps'
    msg_id = components[0]
    message = components[1]
    sender_addr = ""
    if message != "ack":
        sender_addr = components[2]

    received_timestamps = {}

    # Parse the timestamps
    for i in range(3, len(components)):
        timestamp = components[i]
        timestamp_pair = timestamp.split(",")
        timestamp_key = timestamp_pair[0]
        timestamp_value = int(timestamp_pair[1])

        received_timestamps[timestamp_key] = timestamp_value


    

    if message == ACK_MSG:
        # we received an ack message. update ACK so unicast_send can break out of loop
        ACKS[msg_id] = True

    else:
        # we have received a content message. send ack back to sender.
        # if we have already seen this message, mark it None so we don't deliver it twice
        SOCK.sendto( msg_id + "#" + ACK_MSG, addr ) # send acknowledgement message
        if unique_id(msg_id, addr) in RECEIVED:
            message = None
        RECEIVED[unique_id(msg_id, addr)] = True

    return message, addr, sender_addr, received_timestamps



def deliver(source, message, received_timestamps):
    """ Deliver a received message to the application layer (print it) """
    user = source[0] + ":" + str(source[1])
    print user + " -- " + message
    
    if(message != "ack"):
        # Update timestamps
        for key in received_timestamps.keys():
            if received_timestamps[key] > TIMESTAMPS[key]:
                TIMESTAMPS[key] = received_timestamps[key]

    
    # Check if any other messages can now be delivered
    for (addr, message, sender_addr, received_timestamps) in UNDELIVERED:
        if should_deliver(addr, message, sender_addr, received_timestamps):
            deliver(addr, message, received_timestamps)
            UNDELIVERED.remove( (addr, message, sender_addr, received_timestamps) )




def unicast_send_thread(dest_addr, message, msg_id, curr_timestamps):
    """ Send a single message to a single client.
        Waits indefinitely for an acknowledgement that this message was received.
        (The recv_messages_thread adjusts ACKS upon receipt)
        Repeatedly retransmit the message until it it acknowledged. """
    try :
        while msg_id not in ACKS:
            if not should_drop():               # simulate dropping messages
                random_delay()                  # simulate transmission delay
                SOCK.sendto( msg_id + "#" + message + "#" + PROCESS_ID + parse_timestamp_dict(curr_timestamps), dest_addr )
    except socket.error:
        print 'Send to failed'



def multicast(message):
    """ Send a message to every client in the chat group """
    TIMESTAMPS[PROCESS_ID] += 1
    for addr in GROUP:
        if addr[0] + str(addr[1]) != PROCESS_ID:
            global CURR_MSG_ID
            CURR_MSG_ID += 1
            curr_timestamps = copy.deepcopy(TIMESTAMPS)
            start_new_thread( unicast_send_thread, (addr, message, str(CURR_MSG_ID), curr_timestamps) )
            #unicast_send(addr, message)


def should_deliver(message, addr, sender_addr, received_timestamps):
        received_time = received_timestamps[sender_addr]
        print "received_time: " + str(received_time)
        current_time = TIMESTAMPS[sender_addr]
        print "current_time: " + str(current_time)
        if message != None and message != ACK_MSG and received_time == current_time + 1:
            should_deliver = True
            for key in received_timestamps:
                
                # Vj[k] <= Vi[k] (k != j)
                # Check that all other timestamps in received vector
                # are less than or equal to the timestamps in the current vector
                received_time = received_timestamps[key]
                current_time = TIMESTAMPS[key]
                if key != sender_addr and received_time > current_time:
                     return False
            
            return True 
        else:
            return False


def recv_messages_thread(args):
    """ Thread that repeatedly recv's new messages """
    while True:
        message, addr, sender_addr, received_timestamps = unicast_receive()
        
        if message != ACK_MSG and message != None:
            if should_deliver(message, addr, sender_addr, received_timestamps):
                deliver(addr, message, received_timestamps)
            else:
                UNDELIVERED.append((addr, message, sender_addr, received_timestamps))
                print UNDELIVERED


def main(argv):
    """ Get command line arguments """
    if( len(argv) == 3 ):
        config_file_name = argv[0]
        global DELAY_TIME
        DELAY_TIME = int(float(argv[1]))
        global DROP_RATE
        DROP_RATE = float(argv[2])
    else:
        print 'Usage:  python2 chat.py <configfile> <delay time (ms)> <drop rate (0.0-1.0)>'
        sys.exit(2)



    """ Read in an array of IP addresses from the config file 
        GROUP - an array of addresses to all the other processes """
    ip_addrs = read_config_file(config_file_name)
    for i in range(1, len(ip_addrs)):
        addr = ip_addrs[i]
        group_tuple = parse_addr(addr)
        GROUP.append( group_tuple )
        if i==1:
            global PROCESS_ID
            PROCESS_ID=group_tuple[0] + str(group_tuple[1])

        # Initialize timestamp dict
        TIMESTAMPS[group_tuple[0]+str(group_tuple[1])] = 0



    """ Bind this process' socket to the IP and port from the first line of config file """
    try:
        SOCK.bind( parse_addr(ip_addrs[1]) )
    except socket.error, msg:
        print "Bind failed. Error Code: " + str(msg[0]) + " Message " + msg[1]
        sys.exit()

     
    """ Initiate a listener thread for this process to retrieve incoming messages """
    start_new_thread( recv_messages_thread, ("no args",) )

    print "*****"
    print "*****  Welcome to Chat!"
    print "*****  Type a message and hit return to send."
    print "*****"


    """ Prompt the user for input and mulicast that message to all other GROUPs """
    while True:
        msg_to_send = raw_input("")
        multicast(msg_to_send)





""" Run main when called from the command line """
if __name__ == "__main__":
    main(sys.argv[1:])

