import asyncio
import logging
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRecorder

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("client")

logging.getLogger("aiortc.rtcrtpreceiver").setLevel(logging.WARNING)
logging.getLogger("aiortc.rtcrtpsender").setLevel(logging.WARNING)


class VideoStreamClient:
    def __init__(self):
        self.pc = RTCPeerConnection()
        self.recorder = MediaRecorder('/Users/red_byte/PycharmProjects/simpleWebRTC-server/output.mp4')
        self.data_channel = None

    async def handle_answer(self, answer):
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

    async def send_offer(self):
        self.data_channel = self.pc.createDataChannel('dummy')

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

    await asyncio.sleep(15)
    await client.close()
    logger.info("Client closed")


asyncio.run(main())
