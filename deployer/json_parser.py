import json
import requests


# Load json from a url and return this json
def load_json_from_url(my_url):
    r = requests.get(url=my_url)
    print("Retrieving asgard json from: {}".format(my_url))
    # print(r.json())
    return r.json()


# Read a json and return this decoded
def decode_url_json(my_json):
    json_decoded = json.load(my_json)
    str_response = json_decoded.readall().decode('utf-8')
    return str_response


# It checks from a json if the status is working, and return working.
# Otherwise return the status of the stack.
# It only check the first entry on completedTaskList section.
def check_stack_status(json_decoded, stack_name):
    result = None
    print("Searching for stack: {}".format(stack_name))
    for iterator in json_decoded["runningTaskList"]:
        if iterator["objectId"] == stack_name:
            result = "working"
            break
    if result != "working":
        for iterator in json_decoded["completedTaskList"]:
            if iterator["objectId"] == stack_name:
                result = iterator["status"]
                break
    return result


# Check the asgard status by the json list and return state for a stack.
def check_asgard_stack_status(asgard_url, stack):
    asgard_url += "/task/list.json"
    json_decoded = load_json_from_url(asgard_url)
    return check_stack_status(json_decoded, stack)

