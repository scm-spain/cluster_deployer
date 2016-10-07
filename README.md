# Asgard Deployer

Python module to deploy microservices

It contains the AsgardDeployer class, which can be used from other python libraries to manipulate asgard for things like creating applications and deploying them

## Basic usage

To start using AsgardDeployer you just have to create an instance:

```
    deployer = AsgardDeployer(account_name="my_aws_account", start_up_timeout_minutes=5)
```

Once you have your instance you can now deploy:

```
    deployer.deploy()
```

## Configuration

There are plenty configuration parameters you should take care in order to construct your AsgardDeployer.

Basically the constructor of AsgardDeployer receives a dictionary with the following values:

| Parameter                | Type    | Description                                      | Default     |
| ------------------------ | ------- | ------------------------------------------------ | ----------- |
| asgard_url               | String  | The asgard URL                                   | ''          |
| elb                      | Boolean | If should deploy an ELB                          | False       |
| elb_dns                  | Boolean | If should be exposed via a DNS (Route53)         | False       |
| hosted_zone_domain       | String  | Route53 hosted zone if elb_dns=True              | ''          |
| role                     | String  | IAM instance profile needed                      | None        |
| user_mail                | String  | User mail to get notified of Asgard changes      | None        |
| min_instances            | Integer | Number of minimum EC2 instances needed           | 1           |
| max_instances            | Integer | Number of maximum EC2 instances needed           | None        |
| instance_type            | String  | Name of the EC2 instance                         | 'm3.medium' |
| region                   | String  | AWS Region used to deploy                        | 'eu-west-1' |
| user_data                | String  | User data of the EC2 instances                   | 'NULL'      |
| start_up_timeout_minutes | String  | Maximum time to wait for instances to start up   | 10          |
| instance_price_type      | String  | Type of instance price                           | 'ON_DEMAND' |
| elb_mapping_ports        | Array   | Array of mapping ports                           |             |
| stack_label              | String  | Stack label of the installation to be added as a prefix on the cluster name |  None       |

### ELB Mapping ports

Mappings ports variable is an array of exposed ports on the ELB and the mapping port to EC2 instances that belongs.

| Parameter                | Type    | Description                                      |
| ------------------------ | ------- | ------------------------------------------------ |
| protocol                 | String  | Protocol (TCP, HTTP, HTTPS, SSL)                 |
| elb_port                 | Boolean | The ELB exposed port                             |
| instance_port            | Boolean | The EC2 instance target port                     |


Take care: Currently only two mappings are supported

If elb is set to true, it will by default map the following if the mapping ports is not set to:
```
    'protocol': 'HTTP',
    'elb_port': 80,
    'instance_port': 8000
```

You shouldn't use this default values, because there is a highly probability that this will change in the future.


### Example
```
deploy_config = {
    'asgard_url': 'http://asgard.mydomain.com:8080',
    'elb': True,
    'elb_dns': True,
    'hosted_zone_domain': 'service.mydomain.com.',
    'user_mail': 'my_email@mydomain.com',
    'min_instances': 2,
    'max_instances': 5,
    'instance_type': 'm4.large',
    'region': 'eu-west-1',
    'user_data': '',
    'start_up_timeout_minutes': 15,
    'instance_price_type': "ON_DEMAND",
    'elb_mapping_ports': [
        {
            'protocol': 'HTTP',
            'elb_port': 80,
            'instance_port': 8080
        },
        {
            'protocol': 'HTTPS',
            'elb_port': 443,
            'instance_port': 8443
        }
    ]
}

my_deployer = AsgardDeployer(deploy_config)
```

## Deploy variables

Once your configuration is set, you can use the deploy method as follows:

### Deploy without eureka:
The module can deploy without wait service is ready in eureka. To do that use in deploy function use the parameter eureka=False:
```
deployer = AsgardDeployer(...)
deployer.deploy(eureka=False)
```
Without eureka, if not health check is defined the asg wait the start_up_timeout_minutes before desgerister and kill the previous asg, if a health check is defined the asgard tries to have a 200 response from the health check url, if no have good response in start_up_timeout_minutes period the deploy don't finish
```
deployer = AsgardDeployer(...)
deployer.deploy(eureka=False, health_check="/", health_check_port="8080", remove_old=True)
```

* **start_up_timeout_minutes** --> The maximun timeoit of the proces.
* **eureka** --> Default value is True, define if deploy loocks dependency with eureka or not.
* **health_check** --> Only when eureka=False or elb=True, is the of the health check path to confirm that the new versions works correctly (optional value)
* **health_check_port** --> Only when eureka=False or elb=True, is the of the health check port to confirm that the new versions works correctly (optional value)
* **remove_old** --> Only when eureka=False, the deploy proces don't remove previous version, only deploy new version and wait until the new version is correctly deployed.
