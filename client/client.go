package main

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"sync"

	"github.com/pion/webrtc/v3"
)

func main() {
	peerConnection, err := webrtc.NewPeerConnection(webrtc.Configuration{})
	if err != nil {
		log.Fatal(err)
	}

	var iceCandidatesMux sync.Mutex
	iceCandidates := make([]*webrtc.ICECandidate, 0)

	peerConnection.OnICECandidate(func(candidate *webrtc.ICECandidate) {
		if candidate != nil {
			iceCandidatesMux.Lock()
			iceCandidates = append(iceCandidates, candidate)
			iceCandidatesMux.Unlock()
		}
	})

	videoTrackChan := make(chan *webrtc.TrackRemote)
	peerConnection.OnTrack(func(track *webrtc.TrackRemote, receiver *webrtc.RTPReceiver) {
		if track.Kind() == webrtc.RTPCodecTypeVideo {
			videoTrackChan <- track
		}
	})

	offer, err := peerConnection.CreateOffer(nil)
	if err != nil {
		log.Fatal(err)
	}

	if err := peerConnection.SetLocalDescription(offer); err != nil {
		log.Fatal(err)
	}

	<-webrtc.GatheringCompletePromise(peerConnection)

	finalOffer := *peerConnection.LocalDescription()

	offerJSON, err := json.Marshal(finalOffer)
	if err != nil {
		log.Fatal(err)
	}

	log.Println("Sending /offer request with offer:", string(offerJSON))
	resp, err := http.Post("http://localhost:8080/offer", "application/json", bytes.NewReader(offerJSON))
	if err != nil {
		log.Println("Error sending /offer request:", err)
		log.Fatal(err)
	}
	defer resp.Body.Close()

	log.Println("Received /offer response")
	answer := webrtc.SessionDescription{}
	if err := json.NewDecoder(resp.Body).Decode(&answer); err != nil {
		log.Println("Error decoding answer:", err)
		log.Fatal(err)
	}

	log.Println("Received answer:", answer)

	if err := peerConnection.SetRemoteDescription(answer); err != nil {
		log.Println("Error setting remote description:", err)
		log.Fatal(err)
	}

	videoTrack := <-videoTrackChan

	file, err := os.Create("video.raw")
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()

	for {
		packet, _, err := videoTrack.ReadRTP()
		if err != nil {
			if err == io.EOF {
				break
			}
			log.Fatal(err)
		}
		file.Write(packet.Payload)
	}
}
