import cv2
import socket
import threading
import struct
import sys

stop_signal = threading.Event()


def video_stream(sock):
    cap = cv2.VideoCapture(0)
    while not stop_signal.is_set():
        ret, frame = cap.read()
        if not ret:
            break
        data = cv2.imencode('.jpg', frame)[1].tobytes()
        size = len(data)
        sock.sendall(struct.pack(">L", size) + data)
    cap.release()
    sock.close()


def listen_for_stop():
    global stop_signal
    while True:
        user_input = input()
        if user_input.lower() == 'z':
            print("Stopping server...")
            stop_signal.set()
            break


def main():
    global stop_signal
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8080))
    server_socket.listen(5)
    print("Server started, waiting for clients...")

    threading.Thread(target=listen_for_stop, daemon=True).start()

    while not stop_signal.is_set():
        try:
            client_socket, addr = server_socket.accept()
            print(f"Connection from {addr}")
            threading.Thread(target=video_stream, args=(client_socket,)).start()
        except socket.error:
            break

    server_socket.close()


if __name__ == "__main__":
    main()
