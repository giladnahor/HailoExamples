#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Standard python imports

import time

import numpy as np
import cv2
import json
from enum import Enum
import zmq

if __name__ == '__main__':
    import time
    zmq_port = 5557
    zmq_port2 = 6666
    zmq_ip = "10.41.76.25"

    # TBD
    # socket = ClientSocket(zmq_port, zmq_ip)
    context = zmq.Context(1)
    context2 = zmq.Context(2)
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    socket.setsockopt(zmq.RCVHWM, 2)  # limit Q size
    socket.setsockopt(zmq.CONFLATE, 1)  # last msg only.
    socket.setsockopt(zmq.RCVTIMEO, 5)  # set recv timeout
    socket.connect("tcp://{}:{}".format(zmq_ip, zmq_port))

    socket2 = context2.socket(zmq.SUB)
    socket2.setsockopt(zmq.SUBSCRIBE, b"")
    socket2.setsockopt(zmq.RCVHWM, 2)  # limit Q size
    socket2.setsockopt(zmq.CONFLATE, 1)  # last msg only.
    socket2.setsockopt(zmq.RCVTIMEO, 5)  # set recv timeout
    socket2.connect("tcp://{}:{}".format(zmq_ip, zmq_port2))

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
            (frame, detections, meta) = socket.recv_pyobj(False)
            #import ipdb; ipdb.set_trace()
            print(f'got run_camera {meta}')
            #frame = cv2.cvtColor(frame, cv2.COLOR_YUV2RGB_I420)
            cv2.imshow('streaming...', frame)
            #cv2.waitKey(1)
        except zmq.error.Again as e:
            pass
            # print("ZMQ 1 recv reached timeout")
        #try:
        #    frame = socket2.recv_pyobj()
        #    cv2.imshow('Birdseye...', frame)
        #    print("got birdseye")
        #except zmq.error.Again as e:
        #    pass
        #    # print("ZMQ 2 recv reached timeout")
        cv2.waitKey(1)
