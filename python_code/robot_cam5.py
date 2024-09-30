import depthai as dai
import socket
import struct
import time
import keyboard
import signal
import sys
import select

# Setup UDP server
UDP_IP = "192.168.53.14"  # The IP address of the PC receiving the data
UDP_PORT = 45001          # The port used by the transmitting client
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)   # Set the socket to non-blocking mode

# Set up the pipeline for DepthAI
pipeline = dai.Pipeline()

# Create color camera node
cam_rgb = pipeline.create(dai.node.ColorCamera)
cam_rgb.setBoardSocket(dai.CameraBoardSocket.RGB)
cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
cam_rgb.setFps(30)

# Create video encoder
video_encoder = pipeline.create(dai.node.VideoEncoder)
video_encoder.setDefaultProfilePreset(30, dai.VideoEncoderProperties.Profile.H264_MAIN)
cam_rgb.video.link(video_encoder.input)

# Create XLinkOut node to send encoded data to host
xout = pipeline.create(dai.node.XLinkOut)
xout.setStreamName("video")
video_encoder.bitstream.link(xout.input)

# Global variables to manage recording state
recording = False
video_file = None

# Function to manually start recording
def start_recording():
    global recording, video_file
    if not recording:
        timestamp = int(time.time())
        video_file = open(f"recording_{timestamp}.h264", "wb")
        recording = True
        print(f"Recording started manually: recording_{timestamp}.h264")

# Function to manually stop recording
def stop_recording():
    global recording, video_file
    if recording:
        recording = False
        if video_file:
            video_file.close()
        print("Recording stopped manually.")

# Signal handler for graceful shutdown on "Ctrl + C"
def signal_handler(sig, frame):
    print("Script terminated by user.")
    if recording and video_file:
        video_file.close()
    sock.close()
    sys.exit(0)

# Register the signal handler for Ctrl + C
signal.signal(signal.SIGINT, signal_handler)

# Initialize the device and pipeline
with dai.Device(pipeline) as device:
    video_queue = device.getOutputQueue(name="video", maxSize=30, blocking=True)

    print(f"Listening for UDP signals on {UDP_IP}:{UDP_PORT}")
    print("Press 'Ctrl + N' to start recording manually, 'Ctrl + S' to stop recording, and 'Ctrl + C' to exit the script.")

    while True:
        # Check if "Ctrl + N" is pressed to start recording
        if keyboard.is_pressed('ctrl+n'):
            start_recording()

        # Check if "Ctrl + S" is pressed to stop recording
        if keyboard.is_pressed('ctrl+s'):
            stop_recording()

        # Use select to check for incoming data with a timeout
        readable, _, _ = select.select([sock], [], [], 0.1)  # 0.1 second timeout

        if readable:
            # Receive UDP data
            data, addr = sock.recvfrom(1024)

            # Unpack the data according to the structure (big-endian format)
            try:
                robot_tx_cnt, robot_sts, robot_fault, pc_err, camera_err, arm_err_num = struct.unpack('>IBBBBB', data[:9])
                print(f"Received: tx_cnt={robot_tx_cnt}, sts={robot_sts}, fault={robot_fault}, pc_err={pc_err}, camera_err={camera_err}, arm_err_num={arm_err_num}")
            except struct.error:
                print("Received data format is incorrect.")
                continue

            # Check the status notification (robot_sts) value
            if robot_sts in (0x01, 0x02) and not recording:
                # Start recording when robot_sts is "Connecting" (0x01) or "Removing" (0x02)
                start_recording()

            elif robot_sts in (0x03, 0x05, 0x04, 0x06) and recording:
                # Stop recording when robot_sts is "Connect succeeded" (0x03), "Connect failed" (0x05),
                # "Remove succeeded" (0x04), or "Remove failed" (0x06)
                stop_recording()

        # Handle video stream if recording
        if recording:
            video_packet = video_queue.get()
            video_file.write(video_packet.getData())
