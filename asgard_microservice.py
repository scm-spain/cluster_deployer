__author__ = 'fgh'


import requests
import json


REGION = "eu-west-1"

def application_exist(app, asgard_url):
    url = asgard_url + "/" + REGION + "/application/show/" + app + ".json"

    r = requests.post(url, '')

    if r.status_code == 200:
        return True
    else:
        return False


def loadbalancer_exist(app, asgard_url):
    url = asgard_url + "/" + REGION + "/loadBalancer/show/" + app + ".json"

    r = requests.post(url, '')

    if r.status_code == 200:
        return True
    else:
        return False


def create_application(app, asgard_url, user_mail):
    url = asgard_url + "/" + REGION + "/application/save"

    data = {
        'name': app,
        'type': 'Web+Application',
        'description': app,
        'owner': user_mail,
        'email': user_mail,
        'monitorBucketType': 'application',
        'ticket': ''
    }

    r = requests.post(url, data)

    if "<div class=\"errors\">" in r.content:
        print("[ERROR] application not created:")
        print(r.content)

        return False
    elif r.status_code == 200:
        return True
    else:
        print(r.content)
        return False

def create_autoscalinggroup(app, asgard_url, ami, security_group, key_name, role, elbs, instance_type,
                            max_instances, min_instances):
    url = asgard_url + "/" + REGION + "/autoScaling/save"

    data = {
        'ticket': '',
        'requestedFromGui': 'true',
        'appWithClusterOptLevel': 'false',
        'appName': app,
        'stack': '',
        'newStack': '',
        'detail': '',
        'countries': '',
        'devPhase': '',
        'partners': '',
        'revision': '',
        'min': min_instances,
        'max': max_instances,
        'desiredCapacity': min_instances,
        'healthCheckType': 'EC2',
        'healthCheckGracePeriod': '600',
        'terminationPolicy': 'Default',
        'subnetPurpose': 'external',
        'selectedZones': ['eu-west-1a', 'eu-west-1b', 'eu-west-1c'],
        'azRebalance': 'enabled',
        'imageId': ami,
        'instanceType': instance_type,
        'keyName': key_name,
        'selectedSecurityGroups': security_group,
        'pricing': 'ON_DEMAND',
        'kernelId': '',
        'ramdiskId': '',
        'iamInstanceProfile': role,
        'selectedLoadBalancers': elbs
    }

    r = requests.post(url, data)

    print("ASG: " + str(r.status_code))

    if r.status_code == 200:
        return True
    else:
        return False

def get_next_version(app, asgard_url):
    url = asgard_url + "/" + REGION + "/deployment/prepare/" + app + ".json??deploymentTemplateName=CreateAndCleanUpPreviousAsg&includeEnvironment=true"

    r = requests.get(url)

    if r.status_code == 200:
        data = json.loads(r.content)
        version = data["environment"]["nextGroupName"]
        return version
    else:
        return None

def deploy_version(app, asgard_url, ami, user_mail, version, security_group, key_name, role, elbs, instance_type,
                   max_instances, min_instances):
    url = asgard_url + "/" + REGION + "/deployment/start"


    data = {
        "deploymentOptions": {
            "clusterName": app,
            "notificationDestination": user_mail,
            "steps": [
                {
                    "type": "CreateAsg"
                },{
                    "type": "Resize",
                    "targetAsg": "Next",
                    "capacity": 1,
                    "startUpTimeoutMinutes": 10
                },{
                    "type": "DisableAsg",
                    "targetAsg": "Previous"
                },{
                    "type": "DeleteAsg",
                    "targetAsg": "Previous"
                }
            ]
        },
        "asgOptions": {
            "autoScalingGroupName": version,
            "launchConfigurationName": None,
            "minSize": min_instances,
            "maxSize": max_instances,
            "desiredCapacity": min_instances,
            "defaultCooldown": 10,
            "availabilityZones": ["eu-west-1c","eu-west-1a","eu-west-1b"],
            "loadBalancerNames": elbs,
            "healthCheckType": "EC2",
            "healthCheckGracePeriod": 600,
            "placementGroup": None,
            "subnetPurpose": "external",
            "terminationPolicies": ["Default"],
            "tags": [],
            "suspendedProcesses": []
        },
        "lcOptions": {
            "launchConfigurationName": None,
            "imageId": ami,
            "keyName": key_name,
            "securityGroups": [security_group],
            "userData": "NULL",
            "instanceType": instance_type,
            "kernelId": "",
            "ramdiskId": "",
            "blockDeviceMappings": None,
            "instanceMonitoringIsEnabled": False,
            "instancePriceType": "ON_DEMAND",
            "iamInstanceProfile": role,
            "ebsOptimized": False,
            "associatePublicIpAddress": True
        }
    }

    r = requests.post(url, data=json.dumps(data))

    print(r.status_code)

    if r.status_code == 200:
        return True
    else:
        return False


def create_scheduler(auto_scaling_group_name, asgard_url, max_instances, min_instances):
    result = True

    url = asgard_url + "/" + REGION + "/scheduledAction/save"

    # Stop al 19:30 from monday to friday
    data = {
        'group':        auto_scaling_group_name,
        'recurrence':   "30 17 * * 1-5",
        'min':          0,
        'max':          0,
        'desired':      0,
    }

    r = requests.post(url, data)
    print("Stop_week_" + auto_scaling_group_name + ": " + str(r.status_code))

    if r.status_code != 200:
        result = False

    # Start al 7:30 from monday to friday
    data = {
        'group': auto_scaling_group_name,
        'recurrence':   "30 5 * * 1-5",
        'min':          min_instances,
        'max':          max_instances,
        'desired':      min_instances,
        }

    r = requests.post(url, data)
    print("Start_week_" + auto_scaling_group_name + ": " + str(r.status_code))

    if r.status_code != 200:
        result = False

    return result


def create_loadbalancer(app, asgard_url, security_group):
    url = asgard_url + "/" + REGION + "/loadBalancer/save"

    data = {
        'appName': app,
        'selectedZones': ['eu-west-1a', 'eu-west-1b', 'eu-west-1c'],
        'selectedSecurityGroups': security_group,
        'protocol1': 'HTTP',
        'lbPort1': '80',
        'instancePort1': '8000',
        'subnetPurpose': 'external',
        'target': 'HTTP:8000/healthcheck',
        'interval': '10',
        'timeout': '5',
        'unhealthy': '2',
        'healthy': '10'
    }

    r = requests.post(url, data)

    print("ASG: " + str(r.status_code))

    if r.status_code == 200:
        return True
    else:
        print(r.content)
        return False


def asgard_deploy(app, user_mail, ami, security_group, asgard_url, key_name, role, elb, environment,
                        instance_type, max_instances, min_instances):
    if instance_type is None:
        instance_type = "m3.medium"

    if min_instances is None:
        min_instances = 1
    if max_instances is None:
        max_instances = min_instances


    app = app.replace("-","_")
    if elb:
        app = app.replace("_","")

    if not application_exist(app, asgard_url):
        create_application(app, asgard_url, user_mail)
        if not application_exist(app, asgard_url):
            print("[ERROR] creating asgard aplication " + app)
            exit(1)

        # create ELB if need it
        if elb:
            if not loadbalancer_exist(app, asgard_url):
                create_loadbalancer(app, asgard_url, security_group)

            elbs = [app]
        else:
            elbs = []

        # si no existia aplicacio tampoc autoscaling
        create_autoscalinggroup(app=app, asgard_url=asgard_url, ami=ami, security_group=security_group,
                                key_name=key_name, role=role, elbs=elbs, instance_type=instance_type,
                                max_instances=max_instances, min_instances=min_instances)
        if environment is not "pro":
            create_scheduler(app=app, asgard_url=asgard_url, max_instances=max_instances, min_instances=min_instances)
    else:
        # create ELB if need it
        if elb:
            if not loadbalancer_exist(app, asgard_url):
                create_loadbalancer(app, asgard_url, security_group)

            elbs = [app]
        else:
            elbs = []

        # si peta vols dir que no ni ha asg o cap versio previa
        version = get_next_version(app, asgard_url)

        if version is None:
            create_autoscalinggroup(app=app, asgard_url=asgard_url, ami=ami, security_group=security_group,
                                    key_name=key_name, role=role, elbs=elbs, instance_type=instance_type,
                                    max_instances=max_instances, min_instances=min_instances)
            if environment is not "pro":
                create_scheduler(app, asgard_url, max_instances=max_instances, min_instances=min_instances)
        else:
            deploy_version(app=app, asgard_url=asgard_url, ami=ami, user_mail=user_mail, version=version,
                           security_group=security_group, key_name=key_name, role=role, elbs=elbs,
                           instance_type=instance_type, max_instances=max_instances, min_instances=min_instances)
            if environment is not "pro":
                create_scheduler(app=app + "-" + version, asgard_url=asgard_url,
                                 max_instances=max_instances, min_instances=min_instances)