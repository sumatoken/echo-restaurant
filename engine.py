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
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    #fr-FR-DeniseNeural
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
    order = response.split("<==>")[1].rstrip().rstrip().rstrip()
    return order
def extractHumanResponse(response):
    humanResponse = response.split("<==>")[0][1:]
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
    url = os.environ.get("ROBOTS_API_ENDPOINT")
    body = {"intent": "getMenu"}
    response = requests.get(url, body)
    response = response.json()
    return response

def placeOrder(order):
    url = os.environ.get("ROBOTS_API_ENDPOINT")
    body = {"intent": "placeOrder", "order": order}
    response = requests.post(url, body)
    response = response.json()
    print(response)
    return response
    
def JSONToYAML(json):
    result = ""
    
    for index, item in enumerate(json):
        values = ",".join(str(value) for value in item.values())
        result += f"{values}\n"
        
    return result
menu = JSONToYAML(getMenu())

def generateResponse(prompt, context=menu):
    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {
        "role": "system", "content": '''
        You're Echo, a waiter for table 2. Once orders are placed respond with: "Your order of [plate] is placed. Need anything else? <==> {"intent": "placeOrder", "table": tableNumber, "plate": plateName}"

        Menu:
        {} ''' + context
        },
        {"role": "user", "content": prompt}
    ]
    )
    return response.choices[0].message.content
print(generateResponse("I want a salad with seafood."))