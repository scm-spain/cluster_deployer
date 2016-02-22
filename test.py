import requests

class AsgardDeployer(object):
    def __init__(self, app, asgard_base_url):
        self.app = app
        self.asgard_base_url = asgard_base_url

    def request(self, path, body=''):
        url = "http://{0}/{1}".format(self.asgard_base_url, path)
        print(url)
        result = requests.get(url, body)
        return result

    def scaling_policy(self, version):
        # http://asgard.global-dev.spain.schibsted.io:8080/eu-west-1/scalingPolicy/create/testing-v002
        auto_scaling_group_name = "{}".format(self.app)
        if version:
            auto_scaling_group_name += "-{}".format(version)

        data = {
            'topic':                "",
            'ticket':               "",
            'adjustmentType':       "ExactCapacity",             #ChangeInCapacity, ExactCapacity, PercentChangeInCapacity
            'existingMetric':       '{"namespace":"AWS/EC2", "metricName":"CPUUtilization"}',
            'period':               60,
            'cooldown':             300,
            'threshold':            60,
            'evaluationPeriods':    2,
            'statistic':            "Maximum",
            'adjustment':           1,
            'description':          "description",
            'comparisonOperator':   "GreaterThanOrEqualToThreshold",
            'group':                auto_scaling_group_name,
            'region':               "eu-west-1"
        }

        r = self.request("scalingPolicy/create", data)

        if r.status_code != 200:
            return False

        return True


agd = AsgardDeployer(app="testing", asgard_base_url="asgard.global-dev.spain.schibsted.io:8080")
agd.scaling_policy(version="v002")