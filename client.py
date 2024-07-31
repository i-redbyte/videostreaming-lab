import cv2
import socket
import struct
import numpy as np
import time
import os


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 8080))
    data = b""
    payload_size = struct.calcsize(">L")

    output_dir = 'videos'
    os.makedirs(output_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    video_writer = None
    print(f"Output video file will be: {os.path.join(output_dir, f'{timestamp}.avi')}")

    try:
        while True:
            while len(data) < payload_size:
                packet = client_socket.recv(4 * 1024)
                if not packet:
                    break
                data += packet

            if len(data) < payload_size:
                print("Incomplete data received, exiting...")
                break

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">L", packed_msg_size)[0]

            while len(data) < msg_size:
                packet = client_socket.recv(4 * 1024)
                if not packet:
                    break
                data += packet

            if len(data) < msg_size:
                print("Incomplete frame data received, exiting...")
                break

            frame_data = data[:msg_size]
            data = data[msg_size:]

            frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)

            if video_writer is None:
                height, width, _ = frame.shape
                print(f"Frame size: {width}x{height}")

                codecs = ['XVID', 'MJPG', 'mp4v']
                formats = ['avi', 'mp4']
                for codec in codecs:
                    for fmt in formats:
                        print(f"Trying codec {codec} with format {fmt}")
                        video_writer = cv2.VideoWriter(os.path.join(output_dir, f"{timestamp}.{fmt}"),
                                                       cv2.VideoWriter_fourcc(*codec), 20, (width, height))
                        if video_writer.isOpened():
                            print(f"VideoWriter successfully opened with codec {codec} and format {fmt}")
                            break
                    if video_writer.isOpened():
                        break

                if not video_writer.isOpened():
                    print("Failed to open VideoWriter with any codec.")
                    break

            video_writer.write(frame)
            cv2.imshow('Video Stream', frame)

            # Остановка клиентского скрипта при нажатии 'q'
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Stopping client...")
                break
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client_socket.close()
        if video_writer:
            video_writer.release()
            print("VideoWriter released.")
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
