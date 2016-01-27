from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import requests
import json
import sys


def printerr(msg):
    print(msg, file=sys.stderr)


class AsgardDeployer(object):
    def __init__(self, **kwargs):
        # Set properties with default values, then override them with provided
        # keyword arguments
        self.__dict__.update(self.defaults())
        self.__dict__.update(kwargs)

        self.asgard_base_url = "{0}/{1}".format(self.asgard_url, self.region)

        if self.max_instances is None:
            self.max_instances = self.min_instances

        self.app = self.app.replace("-", "_")
        if self.elb:
            self.app = self.app.replace("_", "")

    def defaults(self):
        return {
                'asgard_url': '',
                'elbs': [],
                'elb': None,
                'role': '',
                'user_mail': '',
                'min_instances': 1,
                'max_instances': None,
                'instance_type': 'm3.medium',
                'region': 'eu-west-1',
                'user_data': 'NULL'
                }

    def request(self, path, body=''):
        url = "http://{0}/{1}".format(self.asgard_base_url, path)
        print(url)
        result = requests.post(url, body)
        return result

    def validate_response(self, r):
        if r.status_code == 200 and "<div  class=\"errors\">" not in r.content:
            return True
        else:
            printerr(r.content)
            return False

    def application_exist(self):
        r = self.request("application/show/{}.json".format(self.app))
        return r.status_code == 200

    def loadbalancer_exist(self):
        r = self.request("loadBalancer/show/{}.json".format(self.app))
        return r.status_code == 200

    def create_application_if_not_present(self):
        if not self.application_exist():
            print("doesn't exist")
            if not self.create_application():
                printerr("application creation failed, quitting")
                exit(1)

    def create_application(self):
        data = {
            'name': self.app,
            'type': 'Web+Application',
            'description': self.app,
            'owner': self.user_mail,
            'email': self.user_mail,
            'monitorBucketType': 'application',
            'ticket': ''
        }

        r = self.request("application/save", data)

        return self.validate_response(r)

    def create_autoscalinggroup(self):

        data = {
            'ticket': '',
            'requestedFromGui': 'true',
            'appWithClusterOptLevel': 'false',
            'appName': self.app,
            'stack': '',
            'newStack': '',
            'detail': '',
            'countries': '',
            'devPhase': '',
            'partners': '',
            'revision': '',
            'min': self.min_instances,
            'max': self.max_instances,
            'desiredCapacity': self.min_instances,
            'healthCheckType': 'EC2',
            'healthCheckGracePeriod': '600',
            'terminationPolicy': 'Default',
            'subnetPurpose': 'external',
            'selectedZones': ['eu-west-1a', 'eu-west-1b', 'eu-west-1c'],
            'azRebalance': 'enabled',
            'imageId': self.ami,
            'instanceType': self.instance_type,
            'keyName': self.key_name,
            'selectedSecurityGroups': self.security_group,
            'pricing': 'ON_DEMAND',
            'kernelId': '',
            'ramdiskId': '',
            'iamInstanceProfile': self.role,
            'selectedLoadBalancers': self.elbs
        }

        r = self.request("autoScaling/save", data)

        return self.validate_response(r)

    def get_next_version(self):
        url = "deployment/prepare/" + self.app + ".json?deploymentTemplateName=CreateAndCleanUpPreviousAsg&includeEnvironment=true"

        r = self.request(url)

        if r.status_code == 200:
            data = json.loads(r.content)
            return data["environment"]["nextGroupName"]
        else:
            return None

    def deploy_version(self, version):

        data = {
            "deploymentOptions": {
                "clusterName": self.app,
                "notificationDestination": self.user_mail,
                "steps": [
                    {
                        "type": "CreateAsg"
                    },{
                        "type": "Resize",
                        "targetAsg": "Next",
                        "capacity": self.min_instances,
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
                "minSize": self.min_instances,
                "maxSize": self.max_instances,
                "desiredCapacity": self.min_instances,
                "defaultCooldown": 10,
                "availabilityZones": ["eu-west-1c","eu-west-1a","eu-west-1b"],
                "loadBalancerNames": self.elbs,
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
                "imageId": self.ami,
                "keyName": self.key_name,
                "securityGroups": [self.security_group],
                "userData": self.user_data,
                "instanceType": self.instance_type,
                "kernelId": "",
                "ramdiskId": "",
                "blockDeviceMappings": None,
                "instanceMonitoringIsEnabled": False,
                "instancePriceType": "ON_DEMAND",
                "iamInstanceProfile": self.role,
                "ebsOptimized": False,
                "associatePublicIpAddress": True
            }
        }

        r = self.request("deployment/start", json.dumps(data))

        print(r.content)

        return r.status_code == 200

    def create_loadbalancer(self):

        data = {
            'appName': self.app,
            'selectedZones': ['eu-west-1a', 'eu-west-1b', 'eu-west-1c'],
            'selectedSecurityGroups': self.security_group,
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

        r = self.request("loadBalancer/save", data)

        if r.status_code == 200:
            return True
        else:
            printerr("Load balancer creation failed")
            printerr(r.content)
            return False

    def set_scheduler(self, version):
        auto_scaling_group_name = "{}".format(self.app)
        if version:
            auto_scaling_group_name = auto_scaling_group_name + "-{}".format(version)

        # Stop al 19:30 from monday to friday
        data = {
            'group':        auto_scaling_group_name,
            'recurrence':   "30 17 * * 1-5",
            'min':          0,
            'max':          0,
            'desired':      0,
        }

        r = self.request("scheduledAction/save", data)

        if r.status_code != 200:
            return False

        # Start al 7:30 from monday to friday
        data = {
            'group': auto_scaling_group_name,
            'recurrence':   "30 5 * * 1-5",
            'min':          self.min_instances,
            'max':          self.max_instances,
            'desired':      self.min_instances,
            }

        r = self.request("scheduledAction/save", data)

        if r.status_code != 200:
            return False

        return True

    def deploy(self, environment='pre'):
        self.create_application_if_not_present()
        self.elbs = []
        if self.elb:
            if not self.loadbalancer_exist():
                if not self.create_loadbalancer():
                    print("load balancer creation failed", file=sys.stderr)
                    exit(1)
            self.elbs = [self.app]

        version = self.get_next_version()

        if version is None:
            version = self.app

        print("Deploying {}".format(version))
        self.deploy_version(version=version)

        if environment != 'pro':
            self.set_scheduler(version)
