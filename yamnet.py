#!/usr/bin/env python3

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
target0=np.zeros((1,yam_len)) # 
target1=np.zeros((1,yam_len)) #
cur_index = 0
target_count = 0

@client.set_process_callback
def process(frames):
    assert len(client.inports) == len(client.outports)
    assert frames == client.blocksize

    datain = client.inports[0].get_array()
    qin.put(datain)
    c = time.time()
    #print("Time after qin.put(): ",c)
    data = qout.get_nowait()
    client.outports[0].get_array()[:] = data



@client.set_shutdown_callback
def shutdown(status, reason):
    print('JACK shutdown!')
    print('status:', status)
    print('reason:', reason)
    event.set()

def measure(buff):
   rms = np.sqrt(np.mean(buff**2))
   return rms

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


    client.connect('system:capture_1', 'yamnet:input_1')

    playback = client.get_ports(is_physical=True, is_input=True)
    if not playback:
        raise RuntimeError('No physical playback ports')


    client.connect('yamnet:output_1', 'system:playback_1')

  
    print('Press Ctrl+C to stop')
    try:
        while True:
            noisy = qin.get()
            c = time.time()
            #print("cur_index: ",cur_index)
            if cur_index < yam_len:
               a = yam_len - cur_index
               if a > per_len:
                  b = cur_index + per_len 
                  target[0][cur_index:b] = noisy                
                  cur_index = b 
               else:
                  target[0][cur_index:cur_index+a] = noisy[0:a]
                  #print("Filled another one!!!")
                  cur_index=0
                  rms = measure(target)
                  print("rms:  ", rms)
                     
            qout.put(noisy)
            
    except KeyboardInterrupt:
        print('\nInterrupted by user')

print("After interrupt")

   
# When the above with-statement is left (either because the end of the
# code block is reached, or because an exception was raised inside),
# client.deactivate() and client.close() are called automatically.
