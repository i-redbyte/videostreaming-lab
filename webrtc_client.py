import asyncio
import logging
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaRecorder
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Исправлено на basicConfig
logger = logging.getLogger("client")

# Reduce logging level for aiortc
logging.getLogger("aiortc.rtcrtpreceiver").setLevel(logging.WARNING)
logging.getLogger("aiortc.rtcrtpsender").setLevel(logging.WARNING)

class VideoStreamClient:
    def __init__(self):
        self.pc = RTCPeerConnection()
        self.recorder = MediaRecorder('/Users/red_byte/PycharmProjects/simpleWebRTC-server/output.mp4')

    async def handle_answer(self, answer: Dict[str, Any]):
        await self.pc.setRemoteDescription(RTCSessionDescription(sdp=answer["sdp"], type=answer["type"]))

        @self.pc.on("track")
        async def on_track(track):
            logger.info("Track received: %s", track.kind)
            if track.kind == "video":
                try:
                    logger.info("Adding track to recorder")
                    await self.recorder.addTrack(track)
                    logger.info("Track successfully added to recorder")
                except Exception as e:
                    logger.error("Error adding track to recorder: %s", e)

        try:
            await self.recorder.start()
            logger.info("Recording started")
        except Exception as e:
            logger.error("Error starting recorder: %s", e)

    async def send_offer(self) -> Dict[str, Any]:
        # Add a dummy video track
        class DummyVideoTrack(MediaStreamTrack):
            kind = "video"

            async def recv(self):
                pass

        self.pc.addTrack(DummyVideoTrack())

        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        logger.info("Offer created")
        return {
            "sdp": self.pc.localDescription.sdp,
            "type": self.pc.localDescription.type,
        }

    async def close(self):
        try:
            await self.recorder.stop()
            logger.info("Recording stopped")
        except Exception as e:
            logger.error("Error stopping recorder: %s", e)
        await self.pc.close()

async def main():
    client = VideoStreamClient()

    offer = await client.send_offer()

    async with ClientSession() as session:
        async with session.post('http://localhost:8081/offer', json=offer) as resp:
            logger.info("Response status: %s", resp.status)
            resp_text = await resp.text()
            logger.info("Response text: %s", resp_text)
            if resp.status == 200:
                answer = await resp.json()
                logger.info("Answer received: %s", answer)
                await client.handle_answer(answer)
            else:
                logger.error("Failed to get a valid answer from server")

    # Run for a fixed amount of time, then close
    await asyncio.sleep(15)  # Increase the sleep time if needed
    await client.close()
    logger.info("Client closed")

asyncio.run(main())
