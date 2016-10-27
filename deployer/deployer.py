from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re

import requests
import json
import sys
import time
import os
import datetime

from requests import ConnectionError
from deployer.json_parser import check_asgard_stack_status


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
            if len(self.elbs) == 0:
                self.elbs.append(self.get_cluster_name())

    @staticmethod
    def defaults():
        return {
            'asgard_url': '',
            'elbs': [],
            'elb': False,
            'elb_dns': None,
            'hosted_zone_domain': '',
            'role': '',
            'user_mail': '',
            'min_instances': 1,
            'max_instances': None,
            'instance_type': 'm3.medium',
            'region': 'eu-west-1',
            'user_data': 'NULL',
            'start_up_timeout_minutes': 10,
            'instance_price_type': "ON_DEMAND",
            'subnet_purpose_tag': "external",
            'elb_mapping_ports': [
                {
                    'protocol': 'HTTP',
                    'elb_port': 80,
                    'instance_port': 8000
                }
            ],
            'stack_label': None
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
        r = self.request("loadBalancer/show/{0}.json".format(self.get_cluster_name()))
        return r.status_code == 200

    def get_loadbalancer_data(self):
        r = self.request("loadBalancer/show/{0}.json".format(self.get_cluster_name()))

        if r.status_code != 200:
            return None
        else:
            return r.json()

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
            'stack': self.get_stack(),
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
            'subnetPurpose': self.subnet_purpose_tag,
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
        url = "deployment/prepare/" + self.get_cluster_name() + \
              ".json?deploymentTemplateName=CreateAndCleanUpPreviousAsg&includeEnvironment=true"

        r = self.request(url)

        if r.status_code == 200:
            data = json.loads(str(r.text))
            return data["environment"]["nextGroupName"]
        else:
            return None

    def get_stack(self):
        stack = ''
        if self.stack_label is not None:
            stack = self.stack_label
        return stack

    def get_cluster_name(self):
        cluster_name = self.app
        if self.stack_label is not None:
            cluster_name = "{}-{}".format(self.app, self.stack_label)
        return cluster_name

    def deploy_version(self, version):
        data = {
            "deploymentOptions": {
                "clusterName": self.get_cluster_name(),
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
                "availabilityZones": ["eu-west-1c", "eu-west-1a", "eu-west-1b"],
                "loadBalancerNames": self.elbs,
                "healthCheckType": "EC2",
                "healthCheckGracePeriod": 600,
                "placementGroup": None,
                "subnetPurpose": self.subnet_purpose_tag,
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

        for i in range(1, 10):
            print("start deploy version:{} try:{}".format(version, i))

            self.request("deployment/start", json.dumps(data))

            #success = self.wait_for_auto_scaling_group_creation(version)
            success = self.check_auto_scaling_group_creation(version)
            if success:
                break

        if not success:
            raise Exception("Fucking asgard!")

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
                "clusterName": self.get_cluster_name(),
                "notificationDestination": self.user_mail,
                "steps": [
                    {
                        "type": "CreateAsg"
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
                "subnetPurpose": self.subnet_purpose_tag,
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

        success = False
        for i in range(1, 10):
            print("start deploy version:{} try:{}".format(version, i))

            self.request("deployment/start", json.dumps(data))

            #success = self.wait_for_auto_scaling_group_creation(version)
            success = self.check_auto_scaling_group_creation(version)
            if success:
                break

        if success:
            self.resize_asg(asg_name=version)

            good_deploy = self.wait_asg_ready(version=version,
                                              health_check=health_check,
                                              health_check_port=health_check_port)

            if good_deploy:
                if remove_old:
                    self.remove_old_asg(new_asg_name=version)
            else:
                self.disable_asg(asg_name=version)

        else:
            raise Exception("Fucking asgard!")

    def check_auto_scaling_group_creation(self, version):
        retries = 10
        wait_seconds = 10
        url = "http://{0}".format(self.asgard_base_url)
        for r in range(retries):
            status = check_asgard_stack_status(url, version)
            if status:
                return True
            time.sleep(wait_seconds)
        return False


    def wait_for_auto_scaling_group_creation(self, asg_name):
        retries = 10
        wait_seconds = 10

        for r in range(retries):
            resp = self.request("autoScaling/show/{}.json".format(asg_name), None)
            if resp.status_code == 200:
                return True
            time.sleep(wait_seconds)

        return False

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
        not_started = True
        while not_started:
            instances = self.get_instances_in_asg(version)

            if len(instances) > 0:
                not_started = False

            if (datetime.datetime.now() - start).total_seconds() > wait_seconds and not_started:
                return False
            time.sleep(30)

        hostname = None
        for instance in instances:
            if hostname is None:
                hostname = instance["ec2Instance"]["publicDnsName"]

        # wait instance answer ping
        print("--> wait instance answer ping")
        not_started = True
        while not_started:
            response = os.system("ping -c 1 " + hostname)
            if response == 0:
                not_started = False
            if (datetime.datetime.now() - start).total_seconds() > wait_seconds and not_started:
                return False
            time.sleep(30)

        if health_check is None:
            # wait the rest time
            print("--> wait the rest time")
            not_started = True
            while not_started:
                if (datetime.datetime.now() - start).total_seconds() > wait_seconds:
                    not_started = False
                print((datetime.datetime.now() - start).total_seconds())
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

                if (datetime.datetime.now() - start).total_seconds() > wait_seconds and not_started:
                    return False

                print((datetime.datetime.now() - start).total_seconds())
                time.sleep(30)
            return True

    def get_asg_names_in_cluster(self):
        # function get from: https://github.schibsted.io/spt-infrastructure/asgard_manager

        """ Return a list of AutoScaling Groups for the app cluster
        :return: List. Autoscaling Groups in cluster
        """
        resp = self.request("cluster/list.json", None)
        for cluster in json.loads(resp.text):
            if cluster["cluster"] == self.get_cluster_name():
                return cluster["autoScalingGroups"]

        return []  # there are no ASGs, so return an empty list

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

    def create_loadbalancer(self, health_check, health_check_port):
        data = {
            'stack': self.get_stack(),
            'appName': self.app,
            'selectedZones': ['eu-west-1a', 'eu-west-1b', 'eu-west-1c'],
            'selectedSecurityGroups': self.security_group,
            'protocol1': 'HTTP',
            'lbPort1': '80',
            'instancePort1': '8000',
            'subnetPurpose': self.subnet_purpose_tag,
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
        auto_scaling_group_name = "{0}".format(self.get_cluster_name())
        if version:
            auto_scaling_group_name = version

        # Stop al 19:30 from monday to friday
        data = {
            'group': auto_scaling_group_name,
            'recurrence': "30 17 * * 1-5",
            'min': 0,
            'max': 0,
            'desired': 0,
        }

        r = self.request("scheduledAction/save", data)

        if r.status_code != 200:
            return False

        # Start al 7:30 from monday to friday
        data = {
            'group': auto_scaling_group_name,
            'recurrence': "30 5 * * 1-5",
            'min': self.min_instances,
            'max': self.max_instances,
            'desired': self.min_instances,
        }

        r = self.request("scheduledAction/save", data)

        if r.status_code != 200:
            return False

        return True

    def deploy(self, environment='pre', eureka=True, health_check=None, health_check_port=None, remove_old=True):
        if health_check is None:
            health_check = 'healthcheck'

        if health_check_port is None:
            health_check_port = 8000

        self.create_application_if_not_present()

        if self.elb:
            self.deploy_elb(health_check, health_check_port)

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

    def deploy_elb(self, health_check, health_check_port):
        elb_data = self.get_or_create_loadbalancer_data(health_check, health_check_port)

        self.validate_loadbalancer(elb_data, health_check, health_check_port)

        if self.elb_dns:
            domain_name = elb_data["loadBalancer"]["DNSName"]
            self.check_or_create_route53(domain_name)

    def get_or_create_loadbalancer_data(self, health_check, health_check_port):
        elb_data = self.get_loadbalancer_data()

        if elb_data is None:
            if not self.create_loadbalancer(health_check, health_check_port):
                print("load balancer creation failed", file=sys.stderr)
                exit(1)
            elb_data = self.get_loadbalancer_data()

        return elb_data

    @staticmethod
    def validate_loadbalancer(elb_data, health_check, health_check_port):
        elb_healthcheck_target = elb_data.get("loadBalancer", {}).get("healthCheck", {}).get("target")

        if elb_healthcheck_target is None:
            raise Exception("Health check configuration not found on ELB {0}".format(elb_data["name"]))

        search_data = re.search(r"^HTTP:{0}/*{1}$".format(health_check_port, health_check), elb_healthcheck_target)
        if search_data is None:
            wanted_healthcheck = "HTTP:{0}/{1}".format(health_check_port, health_check)

            raise Exception("Deployed ELB healthcheck changed, Updates should be done manually:\n" +
                            "Found: {0} | Requested {1}".format(elb_healthcheck_target, wanted_healthcheck))

    def check_or_create_route53(self, domain_name):
        hosted_zone = self.get_hosted_zone()

        hosted_zone_id = hosted_zone["id"]
        hosted_zone_name = hosted_zone["name"]

        target_route_name = "{0}.{1}".format(self.app, hosted_zone_name)

        route53 = self.get_route53(hosted_zone["id"], target_route_name)

        if route53 is None:
            self.create_route53_cname(hosted_zone_id, target_route_name, domain_name)

        print("Service is exposed on " + target_route_name)

    def get_hosted_zone(self):
        r = self.request("hostedZone/list.json")

        if r.status_code is not 200:
            raise Exception("There isn't hosted zones on AWS")

        json_response = r.json()
        hosted_zones = [route for route in json_response if route.get("name", "") == self.hosted_zone_domain]

        if len(hosted_zones) is not 1:
            hosted_zone = map(lambda route: route["name"], hosted_zones)

            raise Exception("Cannot guess the hostedZone, candidates are: {0}".format(hosted_zone))

        return hosted_zones[0]

    def get_route53(self, hosted_zone_id, wanted_route53_name):
        r = self.request("hostedZone/show/{0}.json".format(hosted_zone_id))

        if r.status_code is not 200:
            raise Exception("Cannot retrieve the list of routes in hosted zone {0}".format(hosted_zone_id))

        json_response = r.json()

        routes = [route for route in json_response.get("resourceRecordSets", []) if route["name"] == wanted_route53_name]

        routes_len = len(routes)

        if routes_len == 0:
            return None
        elif routes_len == 1:
            return routes[0]
        else:
            # Probably this is impossible, or very unlikely (race condition)
            routes_names = map(lambda route: route["name"], routes)
            raise Exception(
                "Found more routes than expected for {0}, candidates {1}".format(wanted_route53_name, routes_names))

    def create_route53_cname(self, hosted_zone_id, route53_name, domain_name):
        # should follow redirects
        path = "hostedZone/addResourceRecordSet"

        data = {
            "type": "CNAME",
            "resourceRecordSetName": route53_name,
            "resourceRecords": domain_name,
            "ttl": "60",
            "hostedZoneId": hosted_zone_id
        }

        r = self.request(path, data)

        if r.status_code != 200 or "DNS CREATE change submitted" not in r.text:
            raise Exception(
                "Cannot create Route53 {0} on hosted_zone {1} - {2}: {3}".format(route53_name, hosted_zone_id,
                                                                                 r.status_code, r.text))
