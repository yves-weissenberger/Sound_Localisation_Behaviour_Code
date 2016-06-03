from __future__ import division
import numpy as np
import pygame
import time
import sys
import matplotlib.pyplot as plt

print 'Running %s' %sys.argv[0]

#________________ Parse input arguments__________________________

SOUNDDUR = float(sys.argv[2])
freq = float(sys.argv[1])
print 'frequency is %sHz' %freq


#______________________________________________________

max16bit = 32766
sR = 96000 # sampling rate = 96 kHz

def gensin(frequency=800, duration=1, sampRate=sR, edgeWin=0.05):
    cycles = np.linspace(0,duration*2*np.pi,num=duration*sampRate)
    wave = np.sin(cycles*frequency, dtype='float32')
    
    #smooth sine wave at the edges
    numSmoothSamps = int(edgeWin*sR)
    wave[0:numSmoothSamps] = wave[0:numSmoothSamps] * np.cos(np.pi*np.linspace(0.5,1,num=numSmoothSamps))**2
    wave[-numSmoothSamps:] = wave[-numSmoothSamps:] * np.cos(np.pi*np.linspace(1,0.5,num=numSmoothSamps))**2
    wave = np.round(wave*max16bit)
    #plt.plot(wave)
    #plt.show()
    return wave.astype('int16')



#buffer=4096
pygame.mixer.pre_init(frequency=sR, size=-16, channels=2, buffer=1024)
#pygame.mixer.init(frequency=sR, size=-16, channels=2, buffer=1024)
pygame.init()


soundArr_1D = gensin(frequency=freq,sampRate=sR,duration=SOUNDDUR)
soundArr_2D = np.vstack([soundArr_1D,soundArr_1D]).T
print soundArr_2D.shape

sound = pygame.sndarray.make_sound(soundArr_2D)
#print sound.getframerate()
print sound.get_num_channels()
print sound.get_length()
print 'playing sound'
channel = sound.play()
channel.set_volume(1, 0)
playT = time.time()
time.sleep(SOUNDDUR)
#i = 0
#while (time.time() - playT)<(SOUNDDUR+1):
#    i += 1 

#pygame.quit()
if pygame.mixer.get_busy()==False:
    pygame.quit()
    print 'sound played'

