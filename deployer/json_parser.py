import json
import requests


def load_json_from_url(my_url):
    r = requests.get(url=my_url)
    # print(r.json())
    return r.json()


def decode_url_json(my_json):
    json_decoded = json.load(my_json)
    str_response = json_decoded.readall().decode('utf-8')
    return str_response


# Return True if the stack have the first entry with status completed or False in the other cases
def check_stack_status(json_decoded, stack_name):
    for iterator in json_decoded["completedTaskList"]:
        if iterator["objectId"] == stack_name:
            break
    if iterator["status"] == "completed":
        result = True
    else:
        result = False
    return result


def check_asgard_stack_status(asgard_url, stack):
    asgard_url += "/task/list.json"
    json_decoded = load_json_from_url(asgard_url)
    print(check_stack_status(json_decoded, stack))

check_asgard_stack_status("http://ec2-52-18-32-197.eu-west-1.compute.amazonaws.com:8080", "ms_autocomplete-awscfdeployms3122-v000")