import cv2
import socket
import struct
import numpy as np
import time


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 8080))
    data = b""
    payload_size = struct.calcsize(">L")

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    video_writer = None

    while True:
        while len(data) < payload_size:
            packet = client_socket.recv(4 * 1024)
            if not packet:
                break
            data += packet

        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack(">L", packed_msg_size)[0]

        while len(data) < msg_size:
            data += client_socket.recv(4 * 1024)

        frame_data = data[:msg_size]
        data = data[msg_size:]

        frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)

        if video_writer is None:
            height, width, _ = frame.shape
            video_writer = cv2.VideoWriter(f"{timestamp}.avi", cv2.VideoWriter_fourcc(*'XVID'), 20, (width, height))

        video_writer.write(frame)
        cv2.imshow('Video Stream', frame)

        # Остановка клиентского скрипта при нажатии 'q'
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Stopping client...")
            break

    client_socket.close()
    video_writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
