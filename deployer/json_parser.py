import json
import requests


def load_json_from_url(my_url):
    r = requests.get(url=my_url)
    print("Retrieving asgard json from: {}".format(my_url))
    # print(r.json())
    return r.json()


def decode_url_json(my_json):
    json_decoded = json.load(my_json)
    str_response = json_decoded.readall().decode('utf-8')
    return str_response


# It checks if the status is working progress, and return working,
# Otherwise return the status of the stack. It only check the first entry on completedTaskList section.
def check_stack_status(json_decoded, stack_name):
    result = None
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


def check_asgard_stack_status(asgard_url, stack):
    asgard_url += "/task/list.json"
    json_decoded = load_json_from_url(asgard_url)
    return check_stack_status(json_decoded, stack)

#check_asgard_stack_status("http://ec2-52-18-32-197.eu-west-1.compute.amazonaws.com:8080", "ms_autocomplete-awscfdeployms3122-v000")