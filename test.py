import json
import time
import boto3

ec2 = boto3.client('ec2')
s3 = boto3.client('s3')
elb = boto3.client('elbv2')

def wait_until_instance_running(instance_id):
    """
    Wait until the EC2 instance is in the 'running' state.
    """
    while True:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        state = response['Reservations'][0]['Instances'][0]['State']['Name']
        if state == 'running':
            return response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        time.sleep(15*60)

def create_ec2_instance(ami):
    instance_params = {
        'ImageId': ami,
        'InstanceType': 't2.micro',
        'MinCount': 1,
        'MaxCount': 1,
    }
    
    response = ec2.run_instances(**instance_params)
    instance_id = response['Instances'][0]['InstanceId']
    
    public_ip = wait_until_instance_running(instance_id)
    
    return f"EC2 instance {instance_id} created successfully. Public IP: {public_ip}"

def create_s3_bucket(bucket_name):
    location_constraint = 'ap-south-1'
    s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': location_constraint})
    return f"S3 bucket {bucket_name} created successfully in {location_constraint}"

def create_load_balancer(name, subnet_1, subnet_2):
    lb_params = {
        'Name': name,
        'Subnets': [subnet_1, subnet_2],
    }
    
    response = elb.create_load_balancer(**lb_params)
    lb_arn = response['LoadBalancers'][0]['LoadBalancerArn']
    
    return f"Load balancer {lb_arn} created successfully"

def lambda_handler(event, context):
    resource_requests = event.get('resource_requests', [])
    output = {}
    
    for resource_request in resource_requests:
        resource_type = resource_request.get('resource_type')
        
        if resource_type == "ec2":
            output['ec2'] = create_ec2_instance(resource_request.get("ami"))
        elif resource_type == "s3":
            output['s3'] = create_s3_bucket(resource_request.get("name"))
        elif resource_type == "elbv2":
            output['elbv2'] = create_load_balancer(resource_request.get("name"), resource_request.get("subnet_1"), resource_request.get("subnet_2"))
        else:
            output[resource_type] = "Unsupported resource type"
        
    return {
        'statusCode': 200,
        'body': json.dumps(output)
    }