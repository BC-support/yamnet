#!/usr/bin/env python3

"""Create a JACK client that copies input audio directly to the outputs.

This is somewhat modeled after the "thru_client.c" example of JACK 2:
http://github.com/jackaudio/jack2/blob/master/example-clients/thru_client.c

If you have a microphone and loudspeakers connected, this might cause an
acoustical feedback!

"""
import sys
import os
import jack
import threading
import queue
import numpy as np
import time

argv = iter(sys.argv)
# By default, use script name without extension as client name:
defaultclientname = os.path.splitext(os.path.basename(next(argv)))[0]
clientname = next(argv, defaultclientname)
servername = next(argv, None)

client = jack.Client(clientname, servername=servername)

if client.status.server_started:
    print('JACK server started')
if client.status.name_not_unique:
    print(f'unique name {client.name!r} assigned')

event = threading.Event()

per_len = 4096
yam_len = 15600

target=np.zeros((1,yam_len)) # not sure if this should be (1,..) or (0,...)
cur_index = 0

@client.set_process_callback
def process(frames):
    assert len(client.inports) == len(client.outports)
    assert frames == client.blocksize

    datain = client.inports[0].get_array()
    qin.put(datain)
    data = qout.get_nowait()
    client.outports[0].get_array()[:] = data



@client.set_shutdown_callback
def shutdown(status, reason):
    print('JACK shutdown!')
    print('status:', status)
    print('reason:', reason)
    event.set()

qout = queue.Queue(maxsize=2)
qin = queue.Queue(maxsize=2)

# create two port pairs
client.inports.register('input_1')
client.outports.register('output_1')

data=np.zeros((per_len,))
qout.put_nowait(data)
qout.put_nowait(data)

with client:
    # When entering this with-statement, client.activate() is called.
    # This tells the JACK server that we are ready to roll.
    # Our process() callback will start running now.

    # Connect the ports.  You can't do this before the client is activated,
    # because we can't make connections to clients that aren't running.
    # Note the confusing (but necessary) orientation of the driver backend
    # ports: playback ports are "input" to the backend, and capture ports
    # are "output" from it.

    capture = client.get_ports(is_physical=True, is_output=True)
    if not capture:
        raise RuntimeError('No physical capture ports')


    client.connect('system:capture_1', 'concat:input_1')

    playback = client.get_ports(is_physical=True, is_input=True)
    if not playback:
        raise RuntimeError('No physical playback ports')


    client.connect('concat:output_1', 'system:playback_1')

  
    print('Press Ctrl+C to stop')
    try:
        while True:
            noisy = qin.get()
            #print("noisy: dim=",noisy.ndim," shape=",noisy.shape," size=",noisy.size)
            if cur_index < yam_len:
               a = yam_len - cur_index
               if a > per_len:
                  b = cur_index + per_len 
                  target[0][cur_index:b] = noisy                
                  cur_index = b 
                  print("cur_index: ",cur_index)
               else:
                  target[0][cur_index:cur_index+a] = noisy[0:a]
                  print("Filled another one!!!")
                  cur_index=0

            qout.put(noisy)
            #event.wait(timeout=3)
            
    except KeyboardInterrupt:
        print('\nInterrupted by user')

# When the above with-statement is left (either because the end of the
# code block is reached, or because an exception was raised inside),
# client.deactivate() and client.close() are called automatically.
