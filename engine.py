from prompt_engine.chat_engine import ChatEngine, ChatEngineConfig
from prompt_engine.model_config import ModelConfig
from prompt_engine.interaction import Interaction
import os
import azure.cognitiveservices.speech as speechsdk
import openai
import os

openai.organization = "org-xwIudUz9vZhKbTbBroTcMtfP"
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

config = ChatEngineConfig(ModelConfig(max_tokens=1024), bot_name="ECHO")
description = "Vous vous appelez Echo et vous êtes capable de tenir des conversations avec des humains. Vous faites toujours votre réponse en une phrase et demie. Lorsque vous n'avez pas de réponse, répondez uniquement par (je ne sais pas) ou toute autre variante. Lorsque le message n'est pas claire, répondez toujours par (Veuillez répéter) ou toute autre variante."
examples = [
    Interaction("Hello", "Hey, how are you?"),
    Interaction("I am feeling okay, and you?", "I'm in my best shape!"),
    Interaction(
        "What is a quantum state?",
        "In quantum mechanics, a quantum state is a precise mathematical description of a physical system that includes both position and momentum.",
    ),
    Interaction(
        "What is Compton effect?",
        "The Compton effect, first described by Arthur Holly Compton, is the phenomenon in which an x-ray or gamma ray photon interacts with an electron.",
    ),
    Interaction(
        "How can I generate signals exploiting the properties of operational amplifiers?",
        "Operational amplifiers (or op amps) can be used to generate various types of signals",
    ),
]
global chat_engine
chat_engine = ChatEngine(config=config, description=description, examples=examples)


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


def generatePrompt(query):
    return chat_engine.build_prompt(query)


def addToContext(query, response):
    chat_engine.add_interaction(query, response)


def generateResponse(prompt):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=60,
        temperature=0.7,
    )
    return response.choices[0].text.split("ECHO: ")[1]


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
