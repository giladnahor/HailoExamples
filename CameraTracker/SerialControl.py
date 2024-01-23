from time import sleep
from pySerialTransfer import pySerialTransfer as txfer
import serial
import RealTimePlotter as plotter
class EyeDataController:
    def __init__(self, port='/dev/ttyUSB0', debug=False):
        self.eyeData = {
            'cam_x': 512.0,
            'cam_y': 512.0,
            'eye_x': 512.0,
            'eye_y': 512.0,
            'blink': 0.0,
            'mouth': 0.0,
        }
        self.ConfigData = {
            'auto_blink': 1.0,
            'cam_x_p': 0.0,
            'cam_x_i': 0.0,
            'cam_x_d': 0.0,
            'cam_y_p': 0.0,
            'cam_y_i': 0.0,
            'cam_y_d': 0.0,
            'eye_x_p': 0.0,
            'eye_x_i': 0.0,
            'eye_x_d': 0.0,
            'eye_y_p': 0.0,
            'eye_y_i': 0.0,
            'eye_y_d': 0.0,
            'eye_open': 0.5,
            'servo_0_min': 270.0,
            'servo_0_max': 390.0,
            'servo_1_min': 280.0,
            'servo_1_max': 400.0,
            'servo_2_min': 270.0,
            'servo_2_max': 390.0,
            'servo_3_min': 280.0,
            'servo_3_max': 400.0,
            'servo_4_min': 280.0,
            'servo_4_max': 400.0,
            'servo_5_min': 280.0,
            'servo_5_max': 400.0,
            'servo_6_min': 250.0,
            'servo_6_max': 450.0,
            'servo_7_min': 320.0,
            'servo_7_max': 380.0,

        }
        self.port = port
        self.link = None
        self.debug = debug
        
    def connect(self):
        self.link = txfer.SerialTransfer(self.port)
        self.link.open()
        sleep(2)
        self.uart_serial = serial.Serial(self.port, 115200)

    def set_debug(self, debug):
        self.debug = debug
        # if self.debug:
        #     self.plotter = plotter.RealTimePlotter(plot_length=100, named_series=True)
    
    # Define class as a singleton
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EyeDataController, cls).__new__(cls)
        return cls._instance

    def update_eye_data(self, cam_x, cam_y, eye_x, eye_y, blink=0.0, mouth=0.0):
        self.eyeData['cam_x'] = cam_x * 1024.0
        self.eyeData['cam_y'] = cam_y * 1024.0
        self.eyeData['eye_x'] = eye_x * 1024.0
        self.eyeData['eye_y'] = eye_y * 1024.0
        self.eyeData['blink'] = blink
        self.eyeData['mouth'] = mouth

    def send_eye_data(self):
        if self.link is None:
            print('Serial link is not initialized. Call connect() first.')
        sendSize = 0
        sendSize = self.link.tx_obj(self.eyeData['cam_x'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.eyeData['cam_y'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.eyeData['eye_x'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.eyeData['eye_y'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.eyeData['blink'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.eyeData['mouth'], start_pos=sendSize)
        self.link.send(sendSize, packet_id=0)

    def update_config_data(self, auto_blink=1.0, 
                           cam_x_p=0.0, cam_x_i=0.0, cam_x_d=0.0, 
                           cam_y_p=0.0, cam_y_i=0.0, cam_y_d=0.0, 
                           eye_x_p=0.0, eye_x_i=0.0, eye_x_d=0.0, 
                           eye_y_p=0.0, eye_y_i=0.0, eye_y_d=0.0, 
                           eye_open=0.5):
        self.ConfigData['auto_blink'] = auto_blink
        self.ConfigData['cam_x_p'] = cam_x_p
        self.ConfigData['cam_x_i'] = cam_x_i
        self.ConfigData['cam_x_d'] = cam_x_d
        self.ConfigData['cam_y_p'] = cam_y_p
        self.ConfigData['cam_y_i'] = cam_y_i
        self.ConfigData['cam_y_d'] = cam_y_d
        self.ConfigData['eye_x_p'] = eye_x_p
        self.ConfigData['eye_x_i'] = eye_x_i
        self.ConfigData['eye_x_d'] = eye_x_d
        self.ConfigData['eye_y_p'] = eye_y_p
        self.ConfigData['eye_y_i'] = eye_y_i
        self.ConfigData['eye_y_d'] = eye_y_d
        self.ConfigData['eye_open'] = eye_open

    def send_config_data(self):
        if self.link is None:
            print('Serial link is not initialized. Call connect() first.')
        sendSize = 0
        sendSize = self.link.tx_obj(self.ConfigData['auto_blink'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['cam_x_p'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['cam_x_i'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['cam_x_d'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['cam_y_p'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['cam_y_i'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['cam_y_d'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['eye_x_p'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['eye_x_i'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['eye_x_d'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['eye_y_p'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['eye_y_i'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['eye_y_d'], start_pos=sendSize)
        sendSize = self.link.tx_obj(self.ConfigData['eye_open'], start_pos=sendSize)
        self.link.send(sendSize, packet_id=1)

    def print_response(self):
        # Read and print the response from Arduino if debug is enabled
        if self.debug:
            while self.uart_serial.in_waiting > 0:
                response = self.uart_serial.readline().decode('utf-8').strip()
                print('Received from Arduino:', response)
    
    def plot_response(self):
        # Read and plot the response from Arduino if debug is enabled
        if self.debug:
            while self.uart_serial.in_waiting > 0:
                response = self.uart_serial.readline().decode('utf-8').strip()
                print('Received from Arduino:', response)
                self.plotter.add_data(response)
                self.plotter.update_plot()


    def close(self):
        self.link.close()
        self.uart_serial.close()

# Instantiate the a class instance to make sure that only one instance is created.
# Users should use this instance to access the class methods.
arduino = EyeDataController()

if __name__ == '__main__':
    try:
        i = 0.0
        # arduino.update_config_data(eye_x_p=1, eye_x_i=1, eye_x_d=1)
        # arduino.send_config_data()
        arduino.set_debug(True)
        arduino.connect()
        while True:
            # arduino.update_eye_data(cam_x=0.5, cam_y=0.5, eye_x=i, eye_y=0.5, blink=False)
            arduino.update_eye_data(cam_x=0.5, cam_y=0.5, eye_x=0.5, eye_y=0.5, blink=False)
            
            import ipdb; ipdb.set_trace()
            arduino.send_eye_data()
            # arduino.update_config_data(eye_x_p=1.0, eye_x_i=0.0, eye_x_d=0.0)
            # arduino.send_config_data()
            # arduino.plot_response()
            # i += 0.01
            # if i > 1.0:
            #     i = 0.0
            arduino.print_response()
            sleep(0.03)
    finally:
        arduino.close()