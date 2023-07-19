#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Standard python imports

import time

import numpy as np
# import cv2
import json
from enum import Enum
import zmq

if __name__ == '__main__':
    import time
    zmq_port = 5555
    zmq_ip = "127.0.0.1"
    context = zmq.Context()
    
    socket = context.socket(zmq.PULL)
    # socket.setsockopt(zmq.SUBSCRIBE, b"")
    socket.setsockopt(zmq.RCVHWM, 10)  # limit Q size
    socket.setsockopt(zmq.CONFLATE, 1)  # last msg only.
    socket.setsockopt(zmq.RCVTIMEO, 50)  # set recv timeout
    socket.connect("tcp://{}:{}".format(zmq_ip, zmq_port))

    print('Running ZMQ SUBSCRIBER')
    # fps = fps_measure(None)
    while(1):
        # buf = socket.recv()
        # # prefix = buf[0:6]
        # # new_frame = detection_pb2.Frame().FromString(buf[6:])
        # new_frame = detection_pb2.Frame().FromString(buf)
        # new_img = get_image(new_frame, outputRGB=True)
        # new_img = cv2.cvtColor(new_img, cv2.COLOR_RGB2BGR)
        # for detection in new_frame.Detections:
        #     print(detection)
        # print(f'{prefix} {new_frame.Width}')
        # if prefix == b'camera':
        #     cv2.imshow('streaming...', new_img)
        # else:
        #     cv2.imshow('Birdseye...', new_img)

        # new_img = socket.recv_pyobj()
        # new_img = cv2.cvtColor(new_img, cv2.COLOR_YUV2RGB_I420)
        # cv2.imshow('Birdseye...', new_img)
        # cv2.waitKey(1)
        try:
            data = socket.recv_pyobj()
            ids = data['ids']
            print(f'got data {ids}')
        except zmq.error.Again as e:
            pass
            # print("ZMQ 1 recv reached timeout")

