import RPi.GPIO as GPIO
import time
import os
GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)   #bailout button


global loop
loop=True
global go_in_to
go_in_to=False

def GPIO22_callback(channel):
	global go_in_to
	go_in_to=True
	print('go',go_in_to)
	os.system('sudo python BeeCam_NN.py')
	print('pressed1')
	

GPIO.add_event_detect(22, GPIO.FALLING, callback=GPIO22_callback, bouncetime=300)


while (loop):
	if(not go_in_to):
		print('go',go_in_to)
	print(loop)
	time.sleep(1)
GPIO.cleanup()
