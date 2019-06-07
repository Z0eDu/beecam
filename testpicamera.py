from time import sleep
from picamera import PiCamera
import datetime


camera = PiCamera(resolution=(640,480), framerate=30)
camera.iso = 250
sleep(2)


camera.exposure_mode='off'
camera.shutter_speed = camera.exposure_speed

g = camera.awb_gains
camera.awb_mode = 'off'
camera.awb_gains = g
# Finally, take several photos with the fixed settings
print(datetime.datetime.now())
camera.capture_sequence(['image%02d.jpg' % i for i in range(5)])
print(datetime.datetime.now())
