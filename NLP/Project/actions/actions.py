
from typing import Dict, Text, Any, List

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.types import DomainDict
from rasa_sdk.executor import CollectingDispatcher

import json
import os
import logging as logger
import re  # regex
from datetime import datetime

fileDir = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(fileDir, 'assets/labs.json')

compilationFile = os.path.join(fileDir, 'assets/compilation.json')
runtimeErrorFile = os.path.join(fileDir, 'assets/runtime.json')

with open(runtimeErrorFile) as c:
    runtime_data = json.load(c)

with open(filename) as read_file:
    logger.info("Reading lab data from the JSON file")
    lab_data = json.load(read_file)

with open(compilationFile) as c:
    compilation_data = json.load(c)


class ActionLabHandout(Action):
    def name(self) -> Text:
        return "action_lab_handout"

    def run(self, dispatcher, tracker, domain):
        curr_lab = str(tracker.get_slot("current_lab"))
        if int(curr_lab) > int(lab_data["current"]):
            dispatcher.utter_message("This lab has not been discussed in class yet")
        elif curr_lab in lab_data:
            dispatcher.utter_message(f"Here is a link where you can find the lab {curr_lab}: {lab_data[curr_lab]['title']}")
            dispatcher.utter_message(lab_data[curr_lab]["handout"])
            dispatcher.utter_message(f"If you need video lecture from the class, you can find it here: {lab_data[curr_lab]['video']}")
        else:
            dispatcher.utter_message("The lab you're searching for does not exist. This might be because you entered the wrong lab number. Please verify your lab number and try again.")

        return [SlotSet("current_lab", lab_data["current"])]


class ActionLabSubmission(Action):
    def name(self) -> Text:
        return "action_lab_submission"

    def run(self, dispatcher, tracker, domain):
        curr_lab = str(tracker.get_slot("current_lab"))

        if int(curr_lab) > int(lab_data["current"]):
            dispatcher.utter_message("This lab has not been discussed in class yet")
        elif curr_lab in lab_data:
            current = lab_data[curr_lab]
            dueDate = datetime.strptime(current["due"]+" 23:59:00", "%d/%m/%Y %H:%M:%S")
            dispatcher.utter_message(
                f"The lab you are trying to submit is worth {current['total']}. It is due on {dueDate}. You have to complete {current['required']/current['totalProblems']}. You are encouraged to do more, but only the top 4 problems are graded.")

            if bool(current["autograde"]):
                dispatcher.utter_message("This lab will be autograded and the grade you receive will be your final grade.")
            else:
                dispatcher.utter_message("This lab will be graded by your instructor. Check back later for your grades in autolab.")

            gradeDistribution = "\n".join(": ".join((str(k), str(v))) for k, v in current['submission']['points'].items())
            dispatcher.utter_message(f"Your grade is distributed as follows:\n{gradeDistribution}")

            dispatcher.utter_message("Follow the following steps to submit your work:")
            for index, step in enumerate(current['submission']["steps"], start=1):
                dispatcher.utter_message(f"{index}. {step}")

        else:
            dispatcher.utter_message("The lab you're searching for does not exist. This might be because you entered the wrong lab number. Please verify your lab number and try again.")

        return [SlotSet("current_lab", lab_data["current"])]


class ActionCompilationError(Action):
    def name(self) -> Text:
        return "action_compilation_error"

    def run(self, dispatcher, tracker, domain):
        message = tracker.get_slot('compilation_error_message')
        matches = re.match(r"([^\s]+)\.java:([0-9]+):\serror:\s(.+)$", message)

        filename = matches.group(1)
        lineNumber = matches.group(2)
        errorMessage = str(matches.group(3)).split(':')[0].strip()

        if errorMessage not in compilation_data:
            dispatcher.utter_message("We don't have this error in our database yet. Please check back later")
        else:
            dispatcher.utter_message(f"Based on the error message you have entered, you seem to have a problem in {filename} on line number {lineNumber}")
            dispatcher.utter_message(f"{compilation_data[errorMessage]['problem']}")
            dispatcher.utter_message("The following could be a potential fix for this problem:")
            dispatcher.utter_message(f"{compilation_data[errorMessage]['solution']}")


class ValidateCompilationErrorForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_compilation_error_form"

    def validate_compilation_error_message(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        message = tracker.latest_message.get('text')
        matches = re.match(r"([^\s]+)\.java:([0-9]+):\serror:\s(.+)$", message)
        if not bool(matches):
            dispatcher.utter_message("The format you used is wrong. Please check the format again.")
            return {"compilation_error_message": None}
        else:
            return {"compilation_error_message": message}


class ValidateLabForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_lab_form"

    def validate_current_lab(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        if slot_value >= 0 and slot_value <= 7:
            return {"current_lab": slot_value}
        else:
            return {"current_lab": int(lab_data["current"])}


class ValidateUserOsForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_user_os_form"

    def validate_os(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # Temp fix. For some reason the things gives entity as list sometimes

        slot_value = tracker.get_slot("os")
        if type(slot_value) is list:
            slot_value = slot_value[0]

        if slot_value not in ["windows", "mac", "linux", "chrome"]:
            dispatcher.utter_message("I didn't get what os you meant. Could you try that again?")
            return {"os": None}
        else:
            return {"os": slot_value}


class ActionInstallation(Action):
    def name(self) -> Text:
        return "action_installation"

    def run(self, dispatcher, tracker, domain) -> List:
        user_os = tracker.get_slot("os")

        if type(user_os) is list:
            user_os = user_os[0]

        guide = {
            "windows": "https://www.guru99.com/install-java.html",
            "linux": "https://opensource.com/article/19/11/install-java-linux",
            "mac": "https://www.whatismybrowser.com/guides/how-to-install-java/mac-os-x",
            "chrome": "https://platypusplatypus.com/chromebooks/enable-java/"
        }

        dispatcher.utter_message(f'Here is a link that contains detailed explanation on how to install java in {user_os} machine. Link: {guide[user_os]}')
        dispatcher.utter_message("Verfiy your java installation by typing 'java' in your terminal.")

        return [SlotSet("os", user_os)]


class ActionRuntimeError(Action):
    def name(self) -> Text:
        return "action_runtime_error"

    def run(self, dispatcher, tracker, domain):
        message = tracker.get_slot('runtime_error_message')

        matches = re.match(r'^(Exception in thread \")(\b.+\b)(\" java\..+\.)(.+)(?:(\: .+))?$', message)
        matchStr = (str(matches.group(4))).split(':')
        errorMessage = matchStr[0]

        if errorMessage not in runtime_data:
            dispatcher.utter_message("We do not have this error in our database yet. Please check back later")
        else:
            dispatcher.utter_message(f"{runtime_data[errorMessage]['problem']}")
            dispatcher.utter_message(f"{runtime_data[errorMessage]['solution']}")

        return [SlotSet("runtime_error_message", None)]


class ValidateRuntimeErrorForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_runtime_error_form"

    def validate_runtime_error_message(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        message = tracker.latest_message.get('text')
        print(message)
        matches = re.match(r'^(Exception in thread \")(\b.+\b)(\" java\..+\.)(.+)(?:(\: .+))?$', message)

        if not bool(matches):
            dispatcher.utter_message("The format you used is incorrect. Please use the correct format. It is recommended to directly enter the error message you got in the terminal")
            return {"runtime_error_message": None}
        else:
            return {"runtime_error_message": message}
