import requests


# Load json from a url and return this json
def load_json_from_url(my_url):
    r = requests.get(url=my_url)
    print("Retrieving asgard json from: {}".format(my_url))
    # print(r.json())
    return r.json()


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


# Check the asgard task status by the json and return state.
def check_asgard_stack_status(asgard_url, id_task):
    json_task_result = load_json_from_url("{0}/task/show/{1}.json".format(asgard_url, id_task))["status"]
    print("Result for task: {}".format(json_task_result))
    return json_task_result


