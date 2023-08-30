from time import sleep
from pySerialTransfer import pySerialTransfer as txfer
import serial

class EyeDataController:
    def __init__(self, port='/dev/ttyUSB0', debug=False):
        self.eyeData = {
            'cam_x': 512.0,
            'cam_y': 512.0,
            'eye_x': 512.0,
            'eye_y': 512.0,
            'blink': False
        }
        self.link = txfer.SerialTransfer(port)
        self.link.open()
        sleep(2)
        self.uart_serial = serial.Serial(port, 115200)
        self.debug = debug

    def update_eye_data(self, cam_x, cam_y, eye_x, eye_y, blink):
        self.eyeData['cam_x'] = cam_x * 1024
        self.eyeData['cam_y'] = cam_y * 1024
        self.eyeData['eye_x'] = eye_x * 1024
        self.eyeData['eye_y'] = eye_y * 1024
        self.eyeData['blink'] = blink

    def send_eye_data(self):
        sendSize = 0
        sendSize = self.link.tx_obj(self.eyeData['cam_x'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.eyeData['cam_y'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.eyeData['eye_x'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.eyeData['eye_y'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.eyeData['blink'], start_pos=sendSize)
        self.link.send(sendSize)

    def print_response(self):
        # Read and print the response from Arduino if debug is enabled
        if self.debug:
            while self.uart_serial.in_waiting > 0:
                response = self.uart_serial.readline().decode('utf-8').strip()
                print('Received from Arduino:', response)

    def close(self):
        self.link.close()
        self.uart_serial.close()
