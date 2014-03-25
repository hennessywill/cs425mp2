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


GROUP = []          # a list of addresses of all the group members
ACKS = {}           # a dict of id:bool indicating if the msg has been acknowledged
RECEIVED = {}       # a dict of unique_id:boolean indicating if the message has been received before
CURR_MSG_ID = 0
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # this process' socket
DELAY_TIME = 0      # average delay time (milliseconds)
DROP_RATE = 0       # probability of dropping a message (between 0 and 1.0)
ACK_MSG = "ack"     # static string



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
    components = content.split("#")     # format is 'msg_id#message'
    msg_id = components[0]
    message = components[1]

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

    return message, addr



def deliver(source, message):
    """ Deliver a received message to the application layer (print it) """
    user = source[0] + ":" + str(source[1])
    print user + " -- " + message



def unicast_send(dest_addr, message):
    """ Send a single message to a single client.
        Waits indefinitely for an acknowledgement that this message was received.
        (The recv_messages_thread adjusts ACKS upon receipt)
        Repeatedly retransmit the message until it it acknowledged. """
    try :
        global CURR_MSG_ID
        CURR_MSG_ID += 1
        while str(CURR_MSG_ID) not in ACKS:
            if not should_drop():               # simulate dropping messages
                random_delay()                  # simulate transmission delay
                SOCK.sendto( str(CURR_MSG_ID) + "#" + message, dest_addr )
    except socket.error:
        print 'Send to failed'



def multicast(message):
    """ Send a message to every client in the chat group """
    for addr in GROUP:
        unicast_send(addr, message)



def recv_messages_thread(args):
    """ Thread that repeatedly recv's new messages """
    while True:
        message, addr = unicast_receive()
        if message != None and message != ACK_MSG:
            deliver(addr, message) 



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
    for addr in ip_addrs:
        GROUP.append( parse_addr(addr) )



    """ Bind this process' socket to the IP and port from the first line of config file """
    try:
        SOCK.bind( parse_addr(ip_addrs[0]) )
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



