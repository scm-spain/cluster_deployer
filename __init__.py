__author__ = 'fgh'
__version__= "1.0"

from boto import ec2

from asgard_microservice import asgard_deploy


def deploy_microservice(account_name, environment, user_mail, name, version, deploy):
    # elb
    if "elb" in deploy[environment]["deploy"].keys():
        if deploy[environment]["deploy"]["elb"]:
            elb = True
    else:
        elb = False

    # key_name
    if "key_name" in deploy[environment]["deploy"].keys():
        key_name = deploy[environment]["deploy"]["key_name"]
    else:
        key_name = account_name + "-" + environment

    # asgard_url
    if "asgard_url" in deploy[environment]["deploy"].keys():
        asgard_url = deploy[environment]["deploy"]["asgard_url"]
    else:
        asgard_url = "http://asgard." + account_name + "-" + environment + ".spain.schibsted.io:8080"
    if asgard_url.endswith("/"):
        asgard_url = asgard_url[:-1]

    # connect to ec2
    conn_ec2 = ec2.connect_to_region('eu-west-1', profile_name=account_name + "-" + environment)

    # security_group_name
    if "security_group" in deploy[environment]["deploy"].keys():
        security_group_name = deploy[environment]["deploy"]["security_group"]
    else:
        security_group_name = "sgClosed"
    security_group = conn_ec2.get_all_security_groups(groupnames=security_group_name)[0].id

    # ami_id
    amis = conn_ec2.get_all_images(filters={'name': name + "-" + version})
    if len(amis) == 1:
        ami_id = amis[0].id

    # role
    if len(deploy[environment]["dependencies"]) > 0:
        role = name
    else:
        role = ""

    instance_type = deploy[environment]["deploy"]["instance_type"]
    max_instances = deploy[environment]["deploy"]["max_instances"]
    min_instances = deploy[environment]["deploy"]["min_instances"]

    app = name

    print("###########################################################################################################")
    print("app=" + app)
    print("user_mail=" + user_mail)
    print("ami=" + ami_id)
    print("security_group=" + security_group)
    print("asgard_url=" + asgard_url)
    print("key_name=" + key_name)
    print("role=" + role)
    print("elb=" + str(elb))
    print("environment=" + environment)
    print("instance_type=" + instance_type)
    print("max_instances=" + str(max_instances))
    print("min_instances=" + str(min_instances))
    print("###########################################################################################################")

    asgard_deploy(app=app, user_mail=user_mail, ami=ami_id, security_group=security_group,
                  asgard_url=asgard_url, key_name=key_name, role=role, elb=elb, environment=environment,
                  instance_type=instance_type, max_instances=max_instances, min_instances=min_instances)
