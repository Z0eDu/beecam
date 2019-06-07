import RPi.GPIO as GPIO
import time as t
import os
import subprocess
import sys
import pygame
import datetime
import cv2
import numpy as np
import json
from pygame.locals import *
from picamera import PiCamera
import file_analyze as ana
import threading


'''Needed to use the PI screen with the gui display'''
#piTFT environment variables
os.putenv('SDL_VIDEODRIVER', 'fbcon')
os.putenv('SDL_FBDEV', '/dev/fb1')
os.putenv('SDL_MOUSEDRV', 'TSLIB')
os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen')


'''
Helper functions
'''



'''Dictionary for bee enter/exit events'''
bee_log_dict={-1: {'entries':[], 'exits': []} }


def add_bee_event(bee_ID=-1,event_time=0,dir_out=True,log=bee_log_dict):
    if not bee_ID in log.keys():
        log[bee_ID]={'entries':[], 'exits': []} 

    if dir_out:
        log[bee_ID]['entries'].append(event_time)
    else:
        log[bee_ID]['exits'].append(event_time)

        
def get_run_count(runFile='runCount.dat'):
    '''
    Get the current run count, increment, and return
    '''
    fh=open(runFile,'r')
    s=fh.readline()
    fh.close()
    cnt=int(s)+1
    fh=open(runFile,'w')
    fh.write(str(cnt) + '\n')
    fh.close()
    return cnt

DATE_FMT_STR='%Y-%m-%d_%H-%M-%S'

def format_folder(dt):
    '''
    Create folder and return save_prefix
    '''
    usb_dir=''
    #Check if a usb key is mounted
    if not os.system('lsblk | grep usb0'):
        usb_dir = '/media/usb0/'
    else:
        print('WARNING: Did not find usb-key, writing to local dir.')
        
    pref=dt.strftime('__' + DATE_FMT_STR)
    pref = usb_dir + 'run-' + str(get_run_count()) +pref 
    os.mkdir(pref)
    os.mkdir(pref + '/var')
    return pref + '/'

size = width, height = 320, 240
pygame.init()
pygame.mouse.set_visible(False)
screen = pygame.display.set_mode(size)
font = pygame.font.Font(pygame.font.get_default_font(), 12)
white = 255, 255, 255
black = 0, 0, 0
color = 127, 15, 111

GPIO.setmode(GPIO.BCM)
GPIO.setup(19, GPIO.OUT)     #ring light 1
GPIO.setup(13, GPIO.OUT)     #ring light 2
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)   #bailout button
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)   #pause/start button
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)    #beam sensor 1
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)   #beam sensor 2
GPIO.output(19, GPIO.HIGH)
GPIO.output(13, GPIO.HIGH)

'''
Setup Variables
'''

'''set up camera stuff'''


camera = PiCamera(resolution=(640,480), framerate=50)
camera.iso = 250
t.sleep(2)


camera.exposure_mode='off'
camera.shutter_speed = camera.exposure_speed
camera.exposure_mode = 'off'
g = camera.awb_gains
camera.awb_mode = 'off'
camera.awb_gains = g

'''store local time'''
start_time=t.time()
bee_log_dict['start_time']=start_time
bee_log_dict['start_time_iso']=datetime.datetime.today().isoformat()

save_prefix=format_folder(datetime.datetime.today())


sensor1 = False     #exiting sensor
sensor2 = False     #entering sensor
current_time = 0.0
hasPollen = False
cnt = 0
num_name = ""
delay = 100         #minimum 100, maximum 6000, steps of 25
ss = 100            #100 is minimum already, maximum 1000, steps of 25
tag=[-1]


global paused
paused = False

global quit_program
quit_program = False


ss_up_button = pygame.draw.rect(screen, white, [20, 200, 50, 30])
ss_down_button = pygame.draw.rect(screen, white, [90, 200, 50, 30])
delay_up_button = pygame.draw.rect(screen, white, [180, 200, 50, 30])
delay_down_button = pygame.draw.rect(screen, white, [250, 200, 50, 30])
top = "default.png"

bees = []
pics_taken = []

'''
for x in range(50) :
    bee = Bee()
    bee.entries = []
    bee.exits = []
    bees.append(bee)
'''



def GPIO27_callback(channel):
    global quit_program
    quit_program = True
    for i in pics_taken:
        i.join()
    

    GPIO.cleanup()

def GPIO17_callback(channel):
    global paused
    paused = not paused

GPIO.add_event_detect(27, GPIO.FALLING, callback=GPIO27_callback, bouncetime=300)
GPIO.add_event_detect(17, GPIO.FALLING, callback=GPIO17_callback, bouncetime=300)
sensor1,sensor2=False,False
sensor_on_times=0
enter,exitt=False,False
start_time=t.time()
while(not quit_program):
    
    if (not paused): 
        pre_sensor1,pre_sensor2=sensor1,sensor2
        sensor1,sensor2=not GPIO.input(5),not GPIO.input(26)

        ''' find falling edge'''
        if(not sensor1 and pre_sensor1):
            sensor_on_times+=1
            enter=True
            leave=False
        elif (not sensor2 and pre_sensor2):
            sensor_on_times+=1
            leave=True
            enter=False
        
        '''assum only one bee right now. either go back to triger 1 twice or go through '''
        if(sensor_on_times==2):
            sensor_on_times=0
            for i in pics_taken:
                i.join()
            pics_taken=[]
            
        '''continously take pictures'''
        if (sensor_on_times==1):
            
            print 'enter','leave'
            print enter,leave
            
            

            pre_num_name=num_name
            cnt = cnt + 1
            print('cnt',cnt)

            if(enter):
                num_name = str(cnt) + "_s1"
            if(leave): 
                num_name = str(cnt) + "_s2" 

            time_pre_image=t.time()
            
            t.sleep(1.0*delay/1000)
            
            
            camera.capture(save_prefix+"top" + num_name + ".jpg")
            
            print("Elapsed Time for capture: ", str(t.time()-time_pre_image))

        
            
            
            '''Change here to use different tag family. Currently tag36h11'''
            
            thread=threading.Thread(target=ana.analyze,args=(cnt,pre_num_name,num_name,save_prefix,bee_log_dict,start_time,tag))
            print("back from threading")
            pics_taken.append(thread)
            
            thread.start()
            '''
            test and display tag
            '''
            #print("start")
            #thread.join()
            
            top = save_prefix + "top" + num_name + ".jpg"
            
            t.sleep(.2)

           

            

    
   
    pygame.draw.rect(screen, black, [0, 0, 320, 200])

    image1 = pygame.image.load(top)
    image1 = pygame.transform.scale(image1, (160, 160))
    
    image1_rect = image1.get_rect()
    image1_rect = image1_rect.move(80, 10)

    delay_up_button = pygame.draw.rect(screen, white, [180, 200, 50, 30])
    ss_up_button = pygame.draw.rect(screen, white, [20, 200, 50, 30])
    ss_down_button = pygame.draw.rect(screen, white, [90, 200, 50, 30])
    delay_down_button = pygame.draw.rect(screen, white, [250, 200, 50, 30])
 
    
    ss_up_b = font.render("SS+", True, black)
    ss_up_b_rect = ss_up_b.get_rect()
    ss_up_b_rect.center = ss_up_button.center  

    ss_down_b = font.render("SS-", True, black)
    ss_down_b_rect = ss_down_b.get_rect()
    ss_down_b_rect.center = ss_down_button.center  

    delay_up_b = font.render("DELAY+", True, black)
    delay_up_b_rect = delay_up_b.get_rect()
    delay_up_b_rect.center = delay_up_button.center  

    delay_down_b = font.render("DELAY-", True, black)
    delay_down_b_rect = delay_down_b.get_rect()
    delay_down_b_rect.center = delay_down_button.center  

    shs = font.render("Shutter Speed: " + str(ss) + " us", True, white)
    shs_r = shs.get_rect()
    shs_r.left = 18
    shs_r.top = 180
    
    dl = font.render("Delay: " + str(delay) + " ms", True, white)
    dl_r = dl.get_rect()
    dl_r.left = 180
    dl_r.top = 180

    file_name = font.render(num_name + ".txt", True, white)
    file_r = file_name.get_rect()
    file_r.left = 5
    file_r.top = 45

    tagid = font.render("Tag ID# :", True, white)
    tagid_r = tagid.get_rect()
    tagid_r.left = 5
    tagid_r.top = 10

    idNum = font.render(str(tag[0]), True, white)
    idNum_r = idNum.get_rect()
    idNum_r.left = 5
    idNum_r.top = 25 
    
    date = font.render("Date:", True, white)
    date_r = date.get_rect()
    date_r.left = 255
    date_r.top = 10

    time = font.render(str(current_time), True, white)
    time_r = time.get_rect()
    time_r.left = 255
    time_r.top = 25

    for event in pygame.event.get():
        if(event.type is MOUSEBUTTONDOWN):
            mouse_pos = pygame.mouse.get_pos()
            if(ss_up_button.collidepoint(mouse_pos)):
                ss = min(ss + 25, 1000)
            if(ss_down_button.collidepoint(mouse_pos)):
                ss = max(ss - 25, 100)
            if(delay_up_button.collidepoint(mouse_pos)):
                delay = min(delay + 25, 6000)
            if(delay_down_button.collidepoint(mouse_pos)):
                delay = max(delay - 25, 100)
    
    screen.blit(file_name, file_r)
    screen.blit(shs, shs_r)
    screen.blit(dl, dl_r)
    screen.blit(time, time_r)
    screen.blit(tagid, tagid_r)
    screen.blit(idNum, idNum_r)
    screen.blit(date, date_r)
    screen.blit(ss_up_b, ss_up_b_rect)
    screen.blit(ss_down_b, ss_down_b_rect)
    screen.blit(delay_up_b, delay_up_b_rect)
    screen.blit(delay_down_b, delay_down_b_rect)
    screen.blit(image1, image1_rect)
    
    pygame.display.flip()


print('Bye bye!')
     
