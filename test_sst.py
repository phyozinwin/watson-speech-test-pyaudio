from ws4py.client.threadedclient import WebSocketClient
import base64, json, ssl, subprocess, threading, time
import wave, Queue
from six.moves import queue
import pyaudio
import os


RATE = 16000
CHUNK = int(RATE / 10) 
class MicrophoneStream(object):
	"""Opens a recording stream as a generator yielding the audio chunks."""
	counter = 0
	def __init__(self, rate, chunk):
		self._rate = rate
		self._chunk = chunk

		# Create a thread-safe buffer of audio data
		self._buff = queue.Queue()
		self.closed = True

	def _startTimer(self):
		start_timer = time.time()


	def __enter__(self):
		MicrophoneStream.counter += 1
		self._audio_interface = pyaudio.PyAudio()
		self._audio_stream = self._audio_interface.open(
			format=pyaudio.paInt16,
			# The API currently only supports 1-channel (mono) audio
			# https://goo.gl/z757pE
			channels=1, rate=self._rate,
			input=True, frames_per_buffer=self._chunk,
			# Run the audio stream asynchronously to fill the buffer object.
			# This is necessary so that the input device's buffer doesn't
			# overflow while the calling thread makes network requests, etc.
			stream_callback=self._fill_buffer,
		)
		print "microphone enter"

		self.closed = False
		return self

	def __exit__(self, type, value, traceback):
		self._audio_stream.stop_stream()
		self._audio_stream.close()
		self.closed = True
		# Signal the generator to terminate so that the client's
		# streaming_recognize method will not block the process termination.
		self._buff.put(None)
		self._audio_interface.terminate()
		print "microphone exit"
		self.recording(self.recording_data)

	def recording(self,data):
		name = "file" + str(MicrophoneStream.counter) + ".wav"
		dir = os.path.dirname(__file__)
		filename = os.path.join(dir, 'resources',name)

		waveFile = wave.open(filename, 'wb')
		waveFile.setnchannels(1)
		waveFile.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
		waveFile.setframerate(RATE)
		waveFile.writeframes(b''.join(data))
		waveFile.close()



	def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
		"""Continuously collect data from the audio stream, into the buffer."""
		#print ("indata",type(in_data))
		self._buff.put(in_data)
		return None, pyaudio.paContinue

	def generator(self):
		start_timer = time.time()
		self.recording_data = []
		while not self.closed and time.time() - start_timer < 25:
			# Use a blocking get() to ensure there's at least one chunk of
			# data, and stop iteration if the chunk is None, indicating the
			# end of the audio stream.
			chunk = self._buff.get()
			if chunk is None:
				return
			data = [chunk]
			#print data
			# Now consume whatever other data's still buffered.
			while True:
				try:
					chunk = self._buff.get(block=False)
					if chunk is None:
						return
					data.append(chunk)
				
				except queue.Empty:
					break
			self.recording_data =  self.recording_data + data
			yield b''.join(data)
			#yield data
		print "generator break"


#?continuous=true
import speech_recognition as sr

class SpeechToTextClient(WebSocketClient):
	def __init__(self):
		ws_url = "wss://stream-tls10.watsonplatform.net/speech-to-text/api/v1/recognize"
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
		self.stream_audio_thread = threading.Thread(target=self.stream_audio)
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
			if time.time() - start > 5:    # Records for n seconds
				self.send(json.dumps({'action': 'stop'}))
				return False
		stream.stop_stream()
		stream.close()
		p.terminate()

	 	self.listening = False
	 	self.stream_audio_thread.join()
		WebSocketClient.close(self)

	def test_audio(self):
		r = sr.Recognizer()
		with sr.Microphone(sample_rate=44100) as source:
		    print("Say something!")
		    audio = r.listen(source)
		    self.send(bytearray(audio), binary=True)
		self.send(json.dumps({'action': 'stop'}))    
	def close(self):
		self.listening = False
		self.stream_audio_thread.join()
		WebSocketClient.close(self)




try:
	stt_client = SpeechToTextClient()
	raw_input()
finally:
	stt_client.close()