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
speech_config.speech_recognition_language = "fr-FR"
audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
speechRecognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config, audio_config=audio_config
)


def JSONToText(json):
    result = ""

    for index, item in enumerate(json):
        values = ",".join(str(value) for value in item.values())
        result += f"{index + 1}: {values}\n"

    return result


def getMenu():
    url = os.environ.get("ROBOTS_API_ENDPOINT")
    body = {"intent": "getMenu"}
    response = requests.get(url, body)
    response = response.json()
    return response


menu = JSONToText(getMenu())


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


def textToSpeech(text):
    speech_config.speech_synthesis_voice_name = "fr-FR-YvetteNeural"
    # fr-FR-DeniseNeural
    # en-US-JennyNeural
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


def generateResponse(prompt):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt="""
            Assume the role of an attentive restaurant waiter. Your responsibilities include:

            Warmly welcoming clients and answering their questions based on the menu, ensuring that your responses are flexible and not repetitive.
            
            Adapt to the language spoken by the client, ensuring that your responses are always in the same language as the client's communication.
            
            Taking orders from clients and ensuring their specific requests are noted.
            
            If no order has been placed, respond with a normal phrase that doesn't include any symbols, such as answering questions about the menu or providing recommendations.
            
            For example: "We have a variety of appetizers, what would you like to order?"

            Only when an order is placed, respond with a unique template that consists of two parts:

            a. A contextually relevant phrase from the ongoing conversation.
            b. The order name.

            The two parts of the template must be separated by the symbol "<==>."

            For example: "Certainly, your appetizer will be out shortly (or any other variation) <==> Tiramisu."

            
            Menu: \n
            """
        + menu
        + """
        CLIENT: """
        + prompt
        + """
        ECHO: """,
        max_tokens=100,
    )
    return response.choices[0].text


def extractOrderFromResponse(response):
    order = response.split("<==>")[1]
    return order


def extractHumanResponse(response):
    humanResponse = response.split("<==>")[0][1:]
    return humanResponse


def placeOrder(order):
    url = os.environ.get("ROBOTS_API_ENDPOINT")
    body = {"intent": "placeOrder", "order": order}
    response = requests.post(url, body)
    response = response.json()
    print(response)
    return response


""" def generateResponse(prompt):
    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {
        "role": "system", "content": '''
        You're Echo, a waiter for table 2. Once orders are placed respond with: "Your order of [plate] is placed. Need anything else? <==> {"intent": "placeOrder", "table": tableNumber, "plate": plateName}"

        Menu:
        {} ''' 
        },
        {"role": "user", "content": prompt}
    ]
    )
    return response.choices[0].message.content """
