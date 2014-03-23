"""
CS 425 MP2
Will Hennessy, Stephen Herring

A python, command line chat client that communicates via
reliable multicast. List all member IP addresses in config.txt
"""

import socket
import sys
from random import randint, random
from time import sleep
from thread import *


CLIENTS = []
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
DELAY_TIME = 0      # average delay time (milliseconds)
DROP_RATE = 0       # probability of dropping a message (between 0 and 1.0)


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



def random_delay():
    """ Sleep for a random amount of time, based on the command line parameter
        Multiply by 2 because DELAY_TIME is the average delay time - linearity of expectation
        Divide by 1000 because the parameter DELAY_TIME is in milliseconds """
    delay = float(randint(0, 2 * DELAY_TIME)) / 1000.0
    sleep(delay)



def should_drop():
    """ Determine if you should drop the message based on the probability
        command line parameter """
    return random() < DROP_RATE



def unicast_receive():
    """ Receive a single message from a single client.
        Implement a randomized delay before delivering the message """
    received_msg = SOCK.recvfrom(4096)
    random_delay()
    return received_msg



def deliver(source, message):
    """ Deliver a received message to the application layer (print it) """
    user = source[0] + ":" + str(source[1])
    print user + " -- " + message



def unicast_send(dest_addr, message):
    """ Send a single message to a single client """
    try :
        SOCK.sendto(message, dest_addr)
    except socket.error:
        print 'Send to failed'



def multicast(message):
    """ Send a message to every client in the chat group """
    for addr in CLIENTS:
        unicast_send(addr, message)



def recv_messages_thread(args):
    """ Thread that repeatedly recv's new messages """
    while True:
        received_msg = unicast_receive()
        if not should_drop():
            deliver(received_msg[1], received_msg[0]) 



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



    """ read in an array of IP addresses from the config file 
        CLIENTS - an array of addresses to all the other processes """
    ip_addrs = read_config_file(config_file_name)
    for addr in ip_addrs[1:]:
        CLIENTS.append( parse_addr(addr) )



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


    """ Prompt the user for input and mulicast that message to all other clientsa """
    while True:
        msg_to_send = raw_input()
        multicast(msg_to_send)





""" Run main when called from the command line """
if __name__ == "__main__":
    main(sys.argv[1:])



