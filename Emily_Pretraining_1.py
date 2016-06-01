# First pretraining step 
# Fixed Interval reward schedule delivering reward AFTER licking central spout
#
# June 2016
# Author: yves weissenberger
# Contact: yvesweissenberger@gmail.com
# Github: https://github.com/yves-weissenberger

print "Im online :)"   #Vital handshake line that is read by server to check that we are running a correct script



#-----------------------------------------------------------------
#Import relevent libraries

import numpy as np
import numpy.random as rnd
import time
import billiard
import RPi.GPIO as GPIO
import pygame
import pickle
import csv
import requests as req
import socket



#-----------------------------------------------------------------
#Initialise function for sending data to server

#Figure out appropriate IP address based on the server
pi_IP = [(s.connect(('8.8.8.8', 80)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
pi_ID = str(int(pi_IP[-3:])-100)


def send_data(load):

    headers = {'User-Agent': 'Mozilla/5.0'}
    link = 'http://192.168.0.99:8000/getData/' + pi_ID + '/get_PiData/'

    session = req.Session()
    r1 = session.get(link,headers=headers)

    link1 = 'http://192.168.0.99:8000/getData/' + pi_ID + '/write_PiData/'


    payload = {'piData':load,'csrfmiddlewaretoken':r1.cookies['csrftoken']}
    #cookies = dict(session.cookies)
    session.post(link1,headers=headers,data=payload)
    return None
#-----------------------------------------------------------------
#Setup input output on raspberry pi board
GPIO.setmode(GPIO.BOARD)


#Set pins to detect licks on
lickL = 40
lickR = 36
lickC = 38

#set those pins as inputs
GPIO.setup(lickL,GPIO.IN)
GPIO.setup(lickR,GPIO.IN)
GPIO.setup(lickC,GPIO.IN)

#add forced callbacks to those pins so that program response in instantaneous
GPIO.add_event_detect(lickL,GPIO.RISING)
GPIO.add_event_detect(lickR,GPIO.RISING)
GPIO.add_event_detect(lickC,GPIO.RISING)


#Set pins so trigger solenoids
rewC = 31
rewL = 33
rewR = 35

#Set those pins as outputs
GPIO.setup(rewL,GPIO.OUT)
GPIO.setup(rewR,GPIO.OUT)
GPIO.setup(rewC,GPIO.OUT)


#-----------------------------------------------------------------
# Initialise Reward Delivery Functions and Processes (billiard is python 3 version of the multiprocessing library)

solOpenDur = 0.12  #Opening time for the solenoid

#Intialise reward delivery function
def deliverRew(channel):
    GPIO.output(channel,1)
    time.sleep(solOpenDur)
    GPIO.output(channel,0)


#Create the processes that will deliver reward. When processes are run i.e. rewProcL.run()
#a separate python instance on one core runs the code in the assigned function so that
#the rest of the code doesn't block during the sleep command
rewProcL = billiard.Process(target=deliverRew,args=(rewL,))
rewProcR = billiard.Process(target=deliverRew,args=(rewR,))
rewProcC = billiard.Process(target=deliverRew,args=(rewC,))


#Helper function called when reward is to be delivered. 
#The mapping is 0 is right response, 1 is left response, 2 is central response
def rew_action(side,rewProcR,rewProcL,rewProcC):
    if side==0:
        rewProcR.run()
        rewProcR = billiard.Process(target=deliverRew,args=(rewR,))
    if side==1:
        rewProcL.run()
        rewProcL = billiard.Process(target=deliverRew,args=(rewL,))
    if side==2:
        rewProcL.run()
        rewProcL = billiard.Process(target=deliverRew,args=(rewC,))

    LR_target = rnd.randint(2)
    return LR_target


#-----------------------------------------------------------------


# Initialise variables
Training = True
maxRews = 300; nRews = 0
intervalDur = 10

#Initialise lists for storage of reward and lick sides and times
lickList = [];  rewList = []
minILI = 0.01

#deliver reward centrally at beginning

#Initialise relevant timers
timer = time.time() - 10; lickT = time.time(); prevL = time.time(); sendT = time.time()

#Define start time
start = time.time()


#Deliver an initial central reward
_ = rew_action(2,rewProcR,rewProcL,rewProcC)
rewList.append([time.time() - start,'C'])


while Training:
    #Control Sector to send data to webserver -----------------------------------------------------------------
    #if 5 seconds have elapsed since the last data_sending
    if (time.time()-sendT>5):

        lickStr = 'LickList:' + '-'.join([str(np.round(entry[0],decimals=3))+entry[1] for entry in lickList])
        rewStr = 'rewList:' + '-'.join([str(np.round(entry[0],decimals=3))+entry[1] for entry in rewList])
        sendStr = ','.join([rewStr,lickStr])
                    
        sendProc = billiard.Process(target=send_data,args=(sendStr,))
        sendProc.start()
        print 'seeeeeending'
        sendT = time.time()
        lickList = []; rewList = [];


#Lick Detection and if appropriate reward delivery ------------------------------------------------------------

    #if a left lick is detected immediately run code in if loop
    if (GPIO.event_detected(lickL)):
        print 'L'
        #if check to make sure only 1 lick is detected if the mouse makes contact
        #corrects essentially for switch bounces from the relay in the lick
        #detectors
        if (time.time()-prevL)>minILI:
            lickT = time.time()
            lickList.append([lickT -start,'L'])
            prevL = time.time()
        else:
            prevL = time.time()


    #if a right lick is detected immediately run code in if loop
    if (GPIO.event_detected(lickR)):
        print 'R'
        if (time.time()-prevL)>minILI:
            lickT = time.time()
            lickList.append([lickT -start,'R'])
            prevL = time.time()
        else:
            prevL = time.time()


    #if a central lick is detected immediately run code in if loop
    if (GPIO.event_detected(lickC)):
        print 'C'

        if (time.time()-prevL)>minILI:
            lickT = time.time()
            lickList.append([lickT -start,'C'])
            prevL = time.time()

            # If fixed interval timer has timed out, deliver reward upon lick
            if (time.time() - timer)>intervalDur:
                timer = time.time()
                _ = rew_action(2,rewProcR,rewProcL,rewProcC)
                rewList.append([time.time() - start,'C'])

                nRews += 1            
        else:
            prevL = time.time()

    if nRews>maxRews:
        Training = False

