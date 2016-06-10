# First pretraining step 
# Go to centre, go to speaker that played sound. Single Speaker
# Second box IP pi@192.168.0.155
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
import csv
import requests as req
import socket


#-----------------------------------------------------------------
#Setup input output on raspberry pi board
GPIO.setmode(GPIO.BOARD)


#Set pins to detect licks on
sndT = 37

#set those pins as inputs
GPIO.setup(sndT,GPIO.IN)

GPIO.add_event_detect(sndT,GPIO.RISING)




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
soundID = np.random.randint(nSounds)
snd = snds[0]
                #sndList.append([time.time()-start,str(soundID)])
#snd.play()

#print 'playing'
#time.sleep(5)
#-----------------------------------------------------------------


while True:

	if (GPIO.event_detected(sndT)):
		print 'hello'
		soundID = np.random.randint(nSounds)
		snd = snds[soundID]
		#sndList.append([time.time()-start,str(soundID)])
		snd.play()


