package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os/exec"
	"time"

	"github.com/pion/webrtc/v3"
	"github.com/pion/webrtc/v3/pkg/media"
)

var peerConnection *webrtc.PeerConnection
var videoTrack *webrtc.TrackLocalStaticSample

func startVideoStream() {
	cmd := exec.Command("ffmpeg", "-f", "avfoundation", "-i", "0:0", "-pix_fmt", "yuv420p", "-f", "rawvideo", "pipe:1")
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		log.Fatal(err)
	}
	if err := cmd.Start(); err != nil {
		log.Fatal(err)
	}

	buffer := make([]byte, 640*480*3/2) // 640x480 YUV420P
	for {
		_, err := stdout.Read(buffer)
		if err != nil {
			log.Fatal(err)
		}
		videoTrack.WriteSample(media.Sample{Data: buffer, Duration: time.Second / 30})
	}
}

func main() {
	var err error
	peerConnection, err = webrtc.NewPeerConnection(webrtc.Configuration{})
	if err != nil {
		log.Fatal(err)
	}

	peerConnection.OnICECandidate(func(candidate *webrtc.ICECandidate) {
		if candidate != nil {
			log.Println("New ICE Candidate:", candidate.ToJSON())
		}
	})

	videoTrack, err = webrtc.NewTrackLocalStaticSample(webrtc.RTPCodecCapability{MimeType: webrtc.MimeTypeVP8}, "video", "pion")
	if err != nil {
		log.Fatal(err)
	}
	peerConnection.AddTrack(videoTrack)

	http.HandleFunc("/offer", func(w http.ResponseWriter, r *http.Request) {
		log.Println("Received /offer request")

		offer := webrtc.SessionDescription{}
		if err := json.NewDecoder(r.Body).Decode(&offer); err != nil {
			log.Println("Error decoding offer:", err)
			http.Error(w, "Error decoding offer", http.StatusBadRequest)
			return
		}

		log.Println("Received offer:", offer)

		if err := peerConnection.SetRemoteDescription(offer); err != nil {
			log.Println("Error setting remote description:", err)
			http.Error(w, "Error setting remote description", http.StatusInternalServerError)
			return
		}

		answer, err := peerConnection.CreateAnswer(nil)
		if err != nil {
			log.Println("Error creating answer:", err)
			http.Error(w, "Error creating answer", http.StatusInternalServerError)
			return
		}

		if err := peerConnection.SetLocalDescription(answer); err != nil {
			log.Println("Error setting local description:", err)
			http.Error(w, "Error setting local description", http.StatusInternalServerError)
			return
		}

		<-webrtc.GatheringCompletePromise(peerConnection)

		finalAnswer := *peerConnection.LocalDescription()

		log.Println("Sending answer:", finalAnswer)
		answerJSON, err := json.Marshal(finalAnswer)
		if err != nil {
			log.Println("Error marshaling answer:", err)
			http.Error(w, "Error marshaling answer", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		if _, err := w.Write(answerJSON); err != nil {
			log.Println("Error writing response:", err)
		}
	})

	http.HandleFunc("/stop", func(w http.ResponseWriter, r *http.Request) {
		if err := peerConnection.Close(); err != nil {
			log.Fatal(err)
		}
		fmt.Fprintln(w, "Stream stopped")
	})

	log.Println("Server started at :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
