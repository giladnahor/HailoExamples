import cv2
import numpy as np
from pyzbar import pyzbar

class QRDetector:
    def __init__(self, method="opencv"):
        self.method = method
        if method == "opencv":
            self.detector = cv2.QRCodeDetector()
        elif method == "zbar":
            pass
        else:
            raise ValueError("Invalid method. Choose either 'opencv' or 'zbar'.")

    def detect_and_decode(self, frame):
        if self.method == "opencv":
            retval, decoded_info, points, straight_qrcode = self.detector.detectAndDecodeMulti(frame)
            return retval, decoded_info, points
        elif self.method == "zbar":
            decoded_symbols = pyzbar.decode(frame)
            decoded_info = [symbol.data.decode('utf-8') for symbol in decoded_symbols]
            points = [symbol.polygon for symbol in decoded_symbols]
            return True if decoded_symbols else False, decoded_info, points

    def draw_boxes(self, frame, points):
        points = np.array(points, dtype=np.int32)
        for point in points:
            if len(point) == 4:
                pts = [pt for pt in point]
                for i in range(4):
                    cv2.line(frame, pts[i], pts[(i+1)%4], color=(0, 255, 0), thickness=2)
        return frame

if __name__ == "__main__":
    method = "zbar"  # Change to "zbar" if you prefer using zbar
    qr_detector = QRDetector(method=method)
    
    # Option to read from camera or file
    source = 2  # Use 0 for camera, or replace with 'path/to/video/file.mp4' to read from file
    
    cap = cv2.VideoCapture(source)
    # set resolution to 1080p
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    ret, frame = cap.read()
    print(f"Frame shape: {frame.shape}")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        retval, decoded_info, points = qr_detector.detect_and_decode(frame)
        
        if retval:
            print(f"QR Code(s) Detected: {decoded_info}")
            frame = qr_detector.draw_boxes(frame, points)
        
        cv2.imshow('QR Code Detector', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
