# Deployer

Python module to deploy microservices

It contains the AsgardDeployer class, which can be used from other python libraries to manipulate asgard for things like creating applications and deploying them


## Deploy without eureka:
The module can deploy without wait service is ready in eureka. To do that use in deploy function use the parameter eureka=False:
```
jenkins = Jenkins(account_name="global-dev", environment="dev", start_up_timeout_minutes=5)
jenkins.deploy(eureka=False)
```
Without eureka, if not health check is defined the asg wait the start_up_timeout_minutes before desgerister and kill the previous asg, if a health check is defined the asgard tries to have a 200 response from the health check url, if no have good response in start_up_timeout_minutes period the deploy don't finish
```
jenkins = Jenkins(account_name="global-dev", environment="dev", start_up_timeout_minutes=5)
jenkins.deploy(eureka=False, health_check="/", health_check_port="8080", remove_old=True)
```

* **start_up_timeout_minutes** --> The maximun timeoit of the proces.
* **eureka** --> Default value is True, define if deploy loocks dependency with eureka or not.
* **health_check** --> Only when eureka=False, is the of the health check path to confirm that the new versions works correctly (optional value)
* **health_check_port** --> Only when eureka=False, is the of the health check port to confirm that the new versions works correctly (optional value)
* **remove_old** --> Only when eureka=False, the deploy proces don't remove previous version, only deploy new version and wait until the new version is correctly deployed.
