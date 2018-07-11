from ws4py.client.threadedclient import WebSocketClient
import base64, json, ssl, subprocess, threading, time
import wave, Queue
from six.moves import queue
import pyaudio
import os


#?continuous=true
import speech_recognition as sr

class SpeechToTextClient(WebSocketClient):
	def __init__(self):
		ws_url = "wss://stream-tls10.watsonplatform.net/speech-to-text/api/v1/recognize?&acoustic_customization_id=7f5ea40e-ac4f-4fbd-a298-5b032c8dfafc&customization_id=dadff4e8-af0e-43b0-8f72-e45584aa8bcb"
		#url="https://stream-tls10.watsonplatform.net/speech-to-text/api/v1"
		username="1f5a4b93-6a45-4eba-adcf-0573289c00f4"
		password="m1B5r4OPuQPu"
		auth_string = "%s:%s" % (username, password)
		base64string = base64.encodestring(auth_string).replace("\n", "")

		self.listening = False

		try:
			WebSocketClient.__init__(self, ws_url,
				headers=[("Authorization", "Basic %s" % base64string)])
			self.connect()
			#self.opened()
			print "test"
		except: print "Failed to open WebSocket."

	def opened(self):
		self.send('{"action": "start", "content-type": "audio/l16;rate=16000"}')
		#self.send('{"continuous":True}')
		self.stream_audio_thread = threading.Thread(target=self.test_audio)
		self.stream_audio_thread.start()
		#self.stream_audio()

	def received_message(self, message):
		print "message received"
		message = json.loads(str(message))
		if "state" in message:
			if message["state"] == "listening":
				self.listening = True
		print "Message received: " + str(message)

	def stream_audio(self):
		#self.listening = True if online server response on received_message
		while not self.listening:
			time.sleep(0.1)

		CHUNK = 1024
		FORMAT = pyaudio.paInt16
		CHANNELS = 1
		RATE = 16000
		print "test"
		p = pyaudio.PyAudio()
		stream = p.open(format=FORMAT,
				channels=CHANNELS,
				rate=RATE,
				input=True,
				output=True,
				frames_per_buffer=CHUNK)
		start = time.time()
		while self.listening:
			data = stream.read(CHUNK)
			#print data
			self.send(bytearray(data),binary=True)
			if time.time() - start > 3:    # Records for n seconds
				self.send(json.dumps({'action': 'stop'}))
				return False
		stream.stop_stream()
		stream.close()
		p.terminate()

	 	self.listening = False
	 	self.stream_audio_thread.join()
		WebSocketClient.closed(self)

	def test_audio(self):
		r = sr.Recognizer()
		with sr.Microphone(sample_rate=44100) as source:
		    print("Say something!")
		    audio = r.listen(source)
		    self.send(bytearray(audio.get_wav_data()), binary=True)
		self.send(json.dumps({'action': 'stop'}))    
	# def close(self):
		
	# 	WebSocketClient.closed(self, code, reason= None)
	def closed(self, code, reason=None):
		self.listening = False
		self.stream_audio_thread.join()
        #print "Closed down", code, reason



try:
	stt_client = SpeechToTextClient()
	raw_input()
finally:
	stt_client.close()