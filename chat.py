"""
CS 425 MP2
Will Hennessy, Stephen Herring

A python, command line chat client that communicates via
reliable multicast. List all member IP addresses in config.txt
"""

import socket
import sys
from time import sleep
from thread import *


CLIENTS = []
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


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



def recv_messages_thread(args):
    """ Thread that repeatedly recv's new messages """
    while True:
        received_msg = SOCK.recvfrom(4096)
        print received_msg[1][0] + ":  " + received_msg[0]



def multicast(message):
    for addr in CLIENTS:
        try :
            SOCK.sendto(message, addr)
        except socket.error:
            print 'Send to failed'



def main(argv):
    """ Get command line arguments """
    if( len(argv) == 3 ):
        config_file_name = argv[0]
        delay_time = argv[1]
        drop_rate = argv[2]
    else:
        print 'Usage:  python2 chat.py <configfile> <delay time> <drop rate>'
        sys.exit(2)


    """ Create the socket for this process """
    # try:
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #DGRAM = UDP
    # except socket.error:
    #     print 'Failed to create socket'
    #     sys.exit()
         


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



