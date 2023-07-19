# import the necessary packages
from augmented_reality import find_and_warp
from imutils.video import VideoStream
from collections import deque
import argparse
import imutils
import time
import cv2
video_src = 2

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", type=str, required=False, default="/local/workspace/tappas/apps/gstreamer/resources/mp4/detection.mp4",
	help="path to input video file for augmented reality")
ap.add_argument("-c", "--cache", type=int, default=-1,
	help="whether or not to use reference points cache")
args = vars(ap.parse_args())

# load the ArUCo dictionary and grab the ArUCo parameters
print("[INFO] initializing marker detector...")
arucoDict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_ARUCO_ORIGINAL)
arucoParams = cv2.aruco.DetectorParameters_create()
# initialize the video file stream
print("[INFO] accessing video stream...")
vf = cv2.VideoCapture(args["input"])
# initialize a queue to maintain the next frame from the video stream
Q = deque(maxlen=128)
# we need to have a frame in our queue to start our augmented reality
# pipeline, so read the next frame from our video file source and add
# it to our queue
(grabbed, source) = vf.read()
Q.appendleft(source)
# initialize the video stream and allow the camera sensor to warm up
print("[INFO] starting video stream...")
vs = VideoStream(src=video_src).start()
time.sleep(2.0)

# loop over the frames from the video stream
while len(Q) > 0:
	# grab the frame from our video stream and resize it
	frame = vs.read()
	frame = imutils.resize(frame, width=600)
	# attempt to find the ArUCo markers in the frame, and provided
	# they are found, take the current source image and warp it onto
	# input frame using our augmented reality technique
	warped = find_and_warp(
		frame, source,
		cornerIDs=(923, 1001, 241, 1007),
		arucoDict=arucoDict,
		arucoParams=arucoParams,
		useCache=args["cache"] > 0)
	# if the warped frame is not None, then we know (1) we found the
	# four ArUCo markers and (2) the perspective warp was successfully
	# applied
	if warped is not None:
		# set the frame to the output augment reality frame and then
		# grab the next video file frame from our queue
		frame = warped
		source = Q.popleft()
	# for speed/efficiency, we can use a queue to keep the next video
	# frame queue ready for us -- the trick is to ensure the queue is
	# always (or nearly full)
	if len(Q) != Q.maxlen:
		# read the next frame from the video file stream
		(grabbed, nextFrame) = vf.read()  
        # if the frame was read (meaning we are not at the end of the
        # video file stream), add the frame to our queue
		if grabbed:
			Q.append(nextFrame)

	# show the output frame
	cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF
	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break
# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()
