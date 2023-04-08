from prompt_engine.chat_engine import ChatEngine, ChatEngineConfig
from prompt_engine.model_config import ModelConfig
from prompt_engine.interaction import Interaction
import azure.cognitiveservices.speech as speechsdk
import openai
from dotenv import load_dotenv
import os
import requests
import yaml
import json
load_dotenv()
openai.organization = os.environ.get("OPENAI_ORG")
openai.api_key = os.environ.get("OPENAI_KEY")

speech_config = speechsdk.SpeechConfig(
    subscription=os.environ.get("AZURE_SPEECH_KEY"),
    region=os.environ.get("AZURE_SPEECH_REGION"),
)
speech_config.speech_recognition_language = "en-US"
audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
speechRecognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config, audio_config=audio_config
)


def listenForWakeWord():
    model = speechsdk.KeywordRecognitionModel("final_highfa.table")
    keyword = "Hey Echo"
    wakeWordRecognizer = speechsdk.KeywordRecognizer()

    def recognized_cb(evt):
        result = evt.result
        if result.reason == speechsdk.ResultReason.RecognizedKeyword:
            print("RECOGNIZED KEYWORD: {}".format(result.text))
        return True

    def canceled_cb(evt):
        result = evt.result
        if result.reason == speechsdk.ResultReason.Canceled:
            print("CANCELED: {}".format(result.cancellation_details.reason))
            return False

    wakeWordRecognizer.recognized.connect(recognized_cb)
    wakeWordRecognizer.canceled.connect(canceled_cb)
    recognisedWakeWord = wakeWordRecognizer.recognize_once_async(model)
    print(
        'Say something starting with "{}" followed by whatever you want...'.format(
            keyword
        )
    )
    result = recognisedWakeWord.get()

    if result.reason == speechsdk.ResultReason.RecognizedKeyword:
        stop_future = wakeWordRecognizer.stop_recognition_async()
        stopped = stop_future.get()
        return True


def textToSpeech(text):
    speech_config.speech_synthesis_voice_name = "fr-FR-DeniseNeural"
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()
    if (
        speech_synthesis_result.reason
        == speechsdk.ResultReason.SynthesizingAudioCompleted
    ):
        return True
    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))

def extractOrderFromResponse(response):
    order = response.split("-")[1].rstrip().rstrip()
    return order
def extractHumanResponse(response):
    humanResponse = response.split("-")[0][1:]
    return humanResponse
def listenToSpeech():
    print("Listening")
    recognisedSpeech = speechRecognizer.recognize_once_async().get()
    if recognisedSpeech.reason == speechsdk.ResultReason.RecognizedSpeech:
        return recognisedSpeech.text
    elif recognisedSpeech.reason == speechsdk.ResultReason.NoMatch:
        print(
            "No speech could be recognized: {}".format(
                recognisedSpeech.no_match_details
            )
        )
        return "No speech could be recognized:"
    elif recognisedSpeech.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = recognisedSpeech.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details))
        return "Error"

def orderToJSON(order):
    order = json.loads(order)
    return order

def getMenu():
    url = "http://localhost:3000/api/robot"
    body = {"intent": "getMenu"}
    response = requests.get(url, body)
    response = response.json()
    return response

def placeOrder(order):
    url = "http://localhost:3000/api/robot"
    body = {"intent": "placeOrder", "order": order}
    response = requests.post(url, body)
    response = response.json()
    print(response)
    return response
    
def JSONToYAML(json):
    return yaml.dump(json)

systemContext = JSONToYAML(getMenu())

def generateResponse(prompt, context=systemContext):
    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": '''
         Your name is Echo. I want you to be a restaurant waiter. You are provided by menu and all the information necessary to do the duties of a waiter. Your job will be to talk to clients and take orders from them. You are responsible for table 2.


Once the order is placed you must only reply using this template: A message to be delivered to the client and a JSON object that has the table number and the order. Here's an example of such a response:
"Your order of Omlette has been placed and will be prepared shortly. Is there anything else I can get for you in the meantime, such as a drink or side dish? - {"intent": "placeOrder", "table": tableNumber, "plate": plateName}"

The restaurant's menu:
{} ''' + context},
        {"role": "user", "content": prompt}
    ]
)
    return response.choices[0].message.content