import asyncio
import logging
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay, MediaPlayer

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("server")

pcs = set()
relay = MediaRelay()


async def offer(request):
    try:
        params = await request.json()
        logger.debug("Received offer: %s", params)
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        pc = RTCPeerConnection()
        pcs.add(pc)

        @pc.on("datachannel")
        def on_datachannel(channel):
            logger.info("Data channel: %s", channel.label)

        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            logger.info("ICE connection state is %s", pc.iceConnectionState)
            if pc.iceConnectionState == "failed":
                await pc.close()
                pcs.discard(pc)

        @pc.on("track")
        def on_track(track):
            logger.info("Track %s received", track.kind)
            if track.kind == "video":
                pc.addTrack(relay.subscribe(player.video))

            @track.on("ended")
            async def on_ended():
                logger.info("Track %s ended", track.kind)
                await pc.close()
                pcs.discard(pc)

        player = MediaPlayer("default", format="avfoundation", options={
            "framerate": "30", "video_size": "640x480", "pixel_format": "uyvy422"
        })
        logger.debug("MediaPlayer created")
        video_track = player.video

        await pc.setRemoteDescription(offer)
        logger.debug("Remote description set")

        pc.addTrack(video_track)

        for transceiver in pc.getTransceivers():
            if transceiver.sender.track:
                transceiver.direction = "sendrecv"
            elif transceiver.receiver.track:
                transceiver.direction = "recvonly"
            else:
                transceiver.direction = "inactive"

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        logger.debug("Local description set")
        response = {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
        }
        logger.info("Response: %s", response)
        return web.json_response(response)
    except Exception as e:
        logger.error("Error processing offer: %s", e, exc_info=True)
        return web.Response(status=500, text="Internal Server Error")


async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


app = web.Application()
app.router.add_post("/offer", offer)
app.on_shutdown.append(on_shutdown)
web.run_app(app, port=8081)
