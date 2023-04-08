from engine import (
    extractHumanResponse,
    extractOrderFromResponse,
    placeOrder,
    generateResponse,
    listenToSpeech,
    listenForWakeWord,
    textToSpeech,
)
from playsound import playsound


def run():
    recognisedWakeWord = listenForWakeWord()
    while recognisedWakeWord:
        playsound("wake.mp3")
        recognisedSpeech = listenToSpeech()
        if recognisedSpeech == "Exit.":
            exit()
        response = generateResponse(recognisedSpeech)
        print(recognisedSpeech)
        textToSpeech(response)
        if "-" in response:
            humanResponse = extractHumanResponse(response)
            order = extractOrderFromResponse(response)
            print('order: ', order)
            placeOrder(order)
            textToSpeech(humanResponse)
            print(response)
        
        


run()
