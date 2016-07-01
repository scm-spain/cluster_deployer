from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import requests
import json
import sys
import time
import os
import datetime

from requests import ConnectionError


def printerr(msg):
    print(msg, file=sys.stderr)


class AsgardDeployer(object):
    def __init__(self, **kwargs):
        # Set properties with default values, then override them with provided
        # keyword arguments
        self.__dict__.update(self.defaults())
        # Only update if its value is not None
        self.__dict__.update((k, v) for k, v in kwargs.iteritems() if v is not None)

        self.asgard_base_url = "{0}/{1}".format(self.asgard_url, self.region)

        if self.max_instances is None:
            self.max_instances = self.min_instances

        self.app = self.app.replace("-", "_")
        if self.elb:
            self.app = self.app.replace("_", "")

    @staticmethod
    def defaults():
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
                'user_data': 'NULL',
                'start_up_timeout_minutes': 10,
                'instance_price_type': "ON_DEMAND",
                'elb_mapping_ports': [
                    {
                        'protocol': 'HTTP',
                        'elb_port': 80,
                        'instance_port': 8000
                    }
                ]
        }

    def request(self, path, body=''):
        url = "http://{0}/{1}".format(self.asgard_base_url, path)
        print(url)
        result = requests.post(url, body)
        return result

    @staticmethod
    def validate_response(r):
        if r.status_code == 200 and "errors" not in r.text:
            return True
        else:
            printerr(r.text)
            return False

    def application_exist(self):
        r = self.request("application/show/{0}.json".format(self.app))
        return r.status_code == 200

    def loadbalancer_exist(self):
        r = self.request("loadBalancer/show/{0}.json".format(self.app))
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

    def create_empty_autoscalinggroup(self):
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
            'min': 0,
            'max': 0,
            'desiredCapacity': 0,
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
        url = "deployment/prepare/" + self.app + \
              ".json?deploymentTemplateName=CreateAndCleanUpPreviousAsg&includeEnvironment=true"

        r = self.request(url)

        if r.status_code == 200:
            data = json.loads(str(r.text))
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
                    }, {
                        "type": "Resize",
                        "targetAsg": "Next",
                        "capacity": self.min_instances,
                        "startUpTimeoutMinutes": self.start_up_timeout_minutes,
                    }, {
                        "type": "DisableAsg",
                        "targetAsg": "Previous"
                    }, {
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
                "securityGroups": self.security_group,
                "userData": self.user_data,
                "instanceType": self.instance_type,
                "kernelId": "",
                "ramdiskId": "",
                "blockDeviceMappings": None,
                "instanceMonitoringIsEnabled": False,
                "instancePriceType": self.instance_price_type,
                "iamInstanceProfile": self.role,
                "ebsOptimized": False,
                "associatePublicIpAddress": True
            }
        }

        r = self.request("deployment/start", json.dumps(data))

        print(r.text)

        return r.status_code == 200

    def deploy_version_without_eureka(self, version, health_check, health_check_port, remove_old):
        print("--> PARAMS: "
              "version={version}, "
              "health_check={health_check}, "
              "health_check_port={health_check_port}, "
              "remove_old={remove_old}".format(version=version,
                                               health_check=health_check,
                                               health_check_port=health_check_port,
                                               remove_old=remove_old))

        data = {
            "deploymentOptions": {
                "clusterName": self.app,
                "notificationDestination": self.user_mail,
                "steps": [
                    {
                        "type":                     "CreateAsg"
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
                "availabilityZones": ["eu-west-1c", "eu-west-1a", "eu-west-1b"],
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
                "securityGroups": self.security_group,
                "userData": self.user_data,
                "instanceType": self.instance_type,
                "kernelId": "",
                "ramdiskId": "",
                "blockDeviceMappings": None,
                "instanceMonitoringIsEnabled": False,
                "instancePriceType": self.instance_price_type,
                "iamInstanceProfile": self.role,
                "ebsOptimized": False,
                "associatePublicIpAddress": True
            }
        }

        request = self.request("deployment/start", json.dumps(data))

        time.sleep(30)

        self.resize_asg(asg_name=version)

        good_deploy = self.wait_asg_ready(version=version,
                                          health_check=health_check,
                                          health_check_port=health_check_port)

        if good_deploy:
            if remove_old:
                self.remove_old_asg(new_asg_name=version)
        else:
            self.disable_asg(asg_name=version)

        return request.status_code == 200

    def remove_old_asg(self, new_asg_name):
        for asg_name in self.get_asg_names_in_cluster():
            if asg_name != new_asg_name:
                print("Deleting ASG {0}".format(asg_name))
                self.delete_asg(asg_name)

    def resize_asg(self, asg_name):
        data = {"name": asg_name,
                "minAndMaxSize": self.min_instances,
                "type": "Resize",
                }

        r = self.request("cluster/resize", data)

        return r.status_code == 200

    def wait_asg_ready(self, version, health_check, health_check_port):
        start = datetime.datetime.now()
        wait_seconds = 60 * int(self.start_up_timeout_minutes)

        # wait until a instance are ready
        print("--> wait until a instance are ready")
        instances = self.get_instances_in_asg(version)
        count = 0
        not_started = True
        while not_started:
            instances = self.get_instances_in_asg(version)
            count += 1
            if count > 20:
                not_started = False
            else:
                if len(instances) > 0:
                    not_started = False

            if (datetime.datetime.now()-start).total_seconds() > wait_seconds and not_started:
                return False
            time.sleep(30)

        hostname = None
        for instance in instances:
            if hostname is None:
                hostname = instance["ec2Instance"]["publicIpAddress"]

        # wait instance answer ping
        print("--> wait instance answer ping")
        not_started = True
        while not_started:
            response = os.system("ping -c 1 " + hostname)
            if response == 0:
                not_started = False

            if (datetime.datetime.now()-start).total_seconds() > wait_seconds and not_started:
                return False
            time.sleep(30)

        if health_check is None:
            # wait the rest time
            print("--> wait the rest time")
            not_started = True
            while not_started:
                if (datetime.datetime.now()-start).total_seconds() > wait_seconds:
                    not_started = False
                print((datetime.datetime.now()-start).total_seconds())
                time.sleep(10)
            return True
        else:
            # wait until the health check response
            not_started = True
            while not_started:
                if health_check_port is not None:
                    url = "http://{0}:{1}{2}".format(hostname, health_check_port, health_check)
                else:
                    url = "http://{0}{1}".format(hostname, health_check)

                try:
                    r = requests.get(url)
                    print("--> {0}".format(r.status_code))
                    if r.status_code == 200:
                        not_started = False

                except ConnectionError:
                    print("--> health check don't answer yet.")
                except Exception as e:
                    print("[ERROR] request to health check error {0}: {1}".format(e.errno, e.strerror))
                    return False

                if (datetime.datetime.now()-start).total_seconds() > wait_seconds and not_started:
                    return False

                print((datetime.datetime.now()-start).total_seconds())
                time.sleep(30)
            return True

    def get_asg_names_in_cluster(self):
        # function get from: https://github.schibsted.io/spt-infrastructure/asgard_manager

        """ Return a list of AutoScaling Groups for the app cluster
        :return: List. Autoscaling Groups in cluster
        """
        resp = self.request("cluster/list.json", None)
        for cluster in json.loads(resp.text):
            if cluster["cluster"] == self.app:
                return cluster["autoScalingGroups"]

        return [] # there are no ASGs, so return an empty list

    def get_instances_in_asg(self, asg_name):
        result = list()
        resp = self.request("instance/list.json", None)
        for cluster in json.loads(resp.text):
            if cluster["autoScalingGroupName"] == asg_name:
                result.append(cluster)
        return result

    def disable_asg(self, asg_name):
        data = {"name": asg_name}
        r = self.request("cluster/deactivate", data)
        return r.status_code == 200

    def enable_asg(self, asg_name):
        data = {"name": asg_name}
        r = self.request("cluster/activate", data)
        return r.status_code == 200

    def delete_asg(self, asg_name):
        data = {"name": asg_name}
        r = self.request("cluster/delete", data)
        return r.status_code == 200

    def create_loadbalancer(self, health_check='healthcheck', health_check_port=8000):
        data = {
            'appName': self.app,
            'selectedZones': ['eu-west-1a', 'eu-west-1b', 'eu-west-1c'],
            'selectedSecurityGroups': self.security_group,
            'subnetPurpose': 'external',
            'target': "HTTP:{0}/{1}".format(health_check_port, health_check),
            'interval': '10',
            'timeout': '5',
            'unhealthy': '2',
            'healthy': '10'
        }
        i = 1
        for mapping in self.elb_mapping_ports:
            data['protocol' + str(i)] = mapping['protocol']
            data['lbPort' + str(i)] = mapping['elb_port']
            data['instancePort' + str(i)] = mapping['instance_port']
            i += 1

        r = self.request("loadBalancer/save", data)

        if r.status_code == 200:
            return True
        else:
            printerr("Load balancer creation failed")
            printerr(r.text)
            return False

    def set_scheduler(self, version):
        auto_scaling_group_name = "{0}".format(self.app)
        if version:
            auto_scaling_group_name = version

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

    def deploy(self, environment='pre', eureka=True, health_check=None, health_check_port=None, remove_old=True):
        self.create_application_if_not_present()
        self.elbs = []
        if self.elb:
            if not self.loadbalancer_exist():
                if not self.create_loadbalancer(health_check, health_check_port):
                    print("load balancer creation failed", file=sys.stderr)
                    exit(1)
            self.elbs = [self.app]

        version = self.get_next_version()

        if version is None:
            self.create_empty_autoscalinggroup()
            version = self.get_next_version()

        print("Deploying {}".format(version))
        if eureka:
            self.deploy_version(version=version)
        else:
            self.deploy_version_without_eureka(version=version,
                                               health_check=health_check,
                                               health_check_port=health_check_port,
                                               remove_old=remove_old)

        if environment != 'pro':
            self.set_scheduler(version)
