 # First pretraining step 
# Go to centre, go to speaker that played sound. Single Speaker
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
rewC = 35
rewL = 31
rewR = 33

#Set those pins as outputs
GPIO.setup(rewL,GPIO.OUT)
GPIO.setup(rewR,GPIO.OUT)
GPIO.setup(rewC,GPIO.OUT)


#-----------------------------------------------------------------
# Initialise Reward Delivery Functions and Processes (billiard is python 3 version of the multiprocessing library)

solOpenDur = 0.1  #Opening time for the solenoid

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
        print 'R'
        rewProcR.run()
        rewProcR = billiard.Process(target=deliverRew,args=(rewR,))
    if side==1:
        print 'L'
        rewProcL.run()
        rewProcL = billiard.Process(target=deliverRew,args=(rewL,))
    if side==2:
        print 'C'
        rewProcC.run()
        rewProcC = billiard.Process(target=deliverRew,args=(rewC,))

    LR_target = rnd.randint(2)
    return LR_target


#-----------------------------------------------------------------

nSounds = 4
maxF = 16000
minF = 2000
dur = 1
freqs = np.logspace(np.log10(minF),np.log10(maxF),num=nSounds)

#initialise the sound mixer
pygame.mixer.pre_init(96000,-16,1,256) #if jitter, change 256 to different value
pygame.init()


max16bit = 32766
sR = 96000 # sampling rate = 96 kHz
def gensin(frequency=2000, duration=1, sampRate=sR, edgeWin=0.01):
    cycles = np.linspace(0,duration*2*np.pi,num=duration*sampRate)
    wave = np.sin(cycles*frequency, dtype='float32')
    
    #smooth sine wave at the edges
    numSmoothSamps = int(edgeWin*sR)
    wave[0:numSmoothSamps] = wave[0:numSmoothSamps] * np.cos(np.pi*np.linspace(0.5,1,num=numSmoothSamps))**2
    wave[-numSmoothSamps:] = wave[-numSmoothSamps:] * np.cos(np.pi*np.linspace(1,0.5,num=numSmoothSamps))**2
    wave = np.round(wave*max16bit)
    
    return wave.astype('int16')


snds = [pygame.sndarray.make_sound(gensin(f,duration=dur)) for f in freqs]

#-----------------------------------------------------------------
# Initialise variables
Training = True
maxRews = 300; nRews = 0
intervalDur = 5

#Initialise lists for storage of reward and lick sides and times
lickList = [];  rewList = []; sndList = []
minILI = 0.05

#deliver reward centrally at beginning

#Initialise relevant timers
timer = time.time() + 10; lickT = time.time(); prevL = time.time(); sendT = time.time()

#Define start time
start = time.time()


#Deliver an initial central reward
#_ = rew_action(2,rewProcR,rewProcL,rewProcC)
rewList.append([time.time() - start,'C'])

lateral_rew_available = False
while Training:
    #Control Sector to send data to webserver -----------------------------------------------------------------
    #if 5 seconds have elapsed since the last data_sending
    if (time.time()-sendT>5):

        lickStr = 'LickList:' + '-'.join([str(np.round(entry[0],decimals=3))+entry[1] for entry in lickList])
        rewStr = 'rewList:' + '-'.join([str(np.round(entry[0],decimals=3))+entry[1] for entry in rewList])
	sndStr = 'rewList:' + '-'.join([str(np.round(entry[0],decimals=3))+entry[1] for entry in sndList])
        sendStr = ','.join([rewStr,lickStr,sndStr])
                    
        sendProc = billiard.Process(target=send_data,args=(sendStr,))
        sendProc.start()
        print 'seeeeeending'
        sendT = time.time()
        lickList = []; rewList = []; sndList = []


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

		if lateral_rew_available:
			_ = rew_action(0,rewProcR,rewProcL,rewProcC)
			rewList.append([time.time() - start,'L'])
			lateral_rew_available = False
			print 'rewL'

		prevL = time.time()
	else:
		prevL = time.time()


    #if a right lick is detected immediately run code in if loop
    if (GPIO.event_detected(lickR)):
	print 'R'
	#if check to make sure only 1 lick is detected if the mouse makes contact
	#corrects essentially for switch bounces from the relay in the lick
	#detectors
	if (time.time()-prevL)>minILI:
		lickT = time.time()
		lickList.append([lickT -start,'R'])

		if lateral_rew_available:
			_ = rew_action(0,rewProcR,rewProcL,rewProcC)
			rewList.append([time.time() - start,'R'])
			lateral_rew_available = False
			print 'rewR'

		prevL = time.time()
	else:
		prevL = time.time()

    #if a central lick is detected immediately run code in if loop
    if (GPIO.event_detected(lickC)):

        if (time.time()-prevL)>minILI:
            print 'C'
            lickT = time.time()
            lickList.append([lickT -start,'C'])
            prevL = time.time()

            # If they haven't already licked in the centre
            if not lateral_rew_available:
                _ = rew_action(2,rewProcR,rewProcL,rewProcC)
                rewList.append([time.time() - start,'C'])
		soundID = np.random.randint(nSounds)		
		
		snd = snds[soundID]
		sndList.append([time.time()-start,str(soundID)])
		snd.play()
		lateral_rew_available = True
                nRews += 1            
        else:
            prevL = time.time()

    if nRews>maxRews:
        Training = False

