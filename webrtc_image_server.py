"""
 pip install opencv-python numpy imageio aiortc
"""
import argparse
import asyncio
import cv2
import imageio
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from av import VideoFrame
from typing import Union, Optional


class ImageStreamTrack(VideoStreamTrack):
    def __init__(self, image_path: str) -> None:
        super().__init__()
        self.image: np.ndarray = imageio.imread(image_path)
        self.image = cv2.resize(self.image, (640, 480))
        if self.image.shape[2] == 4:  # RGBA image
            self.image = cv2.cvtColor(self.image, cv2.COLOR_RGBA2RGB)

    async def recv(self) -> VideoFrame:
        frame: VideoFrame = VideoFrame.from_ndarray(self.image, format="rgb24")
        frame.pts = self.timestamp
        frame.time_base = self.time_base
        return frame


async def run_offer(pc: RTCPeerConnection, signaling: TcpSocketSignaling, image_path: str) -> None:
    image_track: ImageStreamTrack = ImageStreamTrack(image_path)
    pc.addTrack(image_track)
    offer: RTCSessionDescription = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await signaling.send(pc.localDescription)

    while True:
        obj: Union[RTCSessionDescription, BYE] = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)
        elif obj is BYE:
            break


async def run_answer(pc: RTCPeerConnection, signaling: TcpSocketSignaling) -> None:
    offer: RTCSessionDescription = await signaling.receive()
    await pc.setRemoteDescription(offer)
    answer: RTCSessionDescription = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    await signaling.send(pc.localDescription)

    while True:
        obj: Union[RTCSessionDescription, BYE] = await signaling.receive()
        if obj is BYE:
            break


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Send an image over WebRTC.")
    parser.add_argument("image", help="Image file to send", nargs="?", default=None)
    parser.add_argument("--role", choices=["offer", "answer"], help="Role to play in WebRTC connection",
                        default="offer")
    parser.add_argument("--signaling", help="Signaling server address", default="localhost:5678")
    args: argparse.Namespace = parser.parse_args()

    signaling_address = args.signaling.split(":")
    signaling = TcpSocketSignaling(signaling_address[0], int(signaling_address[1]))

    pc: RTCPeerConnection = RTCPeerConnection()

    try:
        if args.role == "offer":
            if args.image is None:
                parser.error("Image file is required for 'offer' role.")
            asyncio.run(run_offer(pc, signaling, args.image))
        else:
            asyncio.run(run_answer(pc, signaling))
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        if not pc.closed:
            asyncio.run(pc.close())
