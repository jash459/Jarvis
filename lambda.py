import json
import boto3
import datetime 


def lambda_handler(event, context):
    # return {
    #     'statusCode': 200,
    #     'body': "Under Construction🔨"
    # }
    
    client = boto3.client('ec2', region_name='ap-south-1')
    client_ssm = boto3.client('ssm')
    
    if 'instanceInfo' in event:
        response = get_all_containers(client, client_ssm)
        
        return {
        'statusCode': 200,
        'body': response
        }
        

    
    instance_id = 'i-0111c349419c23dfa'
    server_type = event.get('serverType')
    port = open_new_port(client)
    
    command = ''
    if server_type == 'nginx':
        command = f'sudo docker run -d -p {port}:80 nginx'
    elif server_type == 'apache':
        command = f'sudo docker run -d -p {port}:80 httpd'
    
    
   

    response = client_ssm.send_command(
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [command]},
        InstanceIds=[instance_id],
    )

    command_id = response['Command']['CommandId']
    
    # Wait for the command to complete
    waiter = client_ssm.get_waiter('command_executed')
    waiter.wait(
        CommandId=command_id,
        InstanceId=instance_id
    )

    # Retrieve the command output
    container_id = client_ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )['StandardOutputContent']


    container_id = container_id.strip()
    container_ip, server_name = get_container_ip(client_ssm, instance_id, container_id)

    return {
        'statusCode': 200,
        'body': {
            'containerID': container_id,
            'containerIP': container_ip,
            'serverName': server_name,
            'url': f'http://3.110.131.140:{port}'
        }
    }
    # return {
    #     'statusCode': 200,
    #     'body': json.loads(json.dumps(output, default=str))
    # }
    
    



def get_container_ip(client_ssm, instance_id, container_id):

    # Command to retrieve container IP using Docker inspect
    docker_inspect_command = f"docker inspect {container_id}"
    
    # Send command to retrieve container IP
    response = client_ssm.send_command(
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [docker_inspect_command]},
        InstanceIds=[instance_id],
    )

    # Get the command invocation details
    command_id = response['Command']['CommandId']
    
    # Wait for the command to complete
    waiter = client_ssm.get_waiter('command_executed')
    waiter.wait(
        CommandId=command_id,
        InstanceId=instance_id
    )

    # Retrieve the command output
    output = client_ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )['StandardOutputContent']

    # Remove newline character from the output
    container_ip = json.loads(output)[0]['NetworkSettings']['IPAddress']
    server_name = json.loads(output)[0]['Config']['Image']

    return container_ip, server_name

    
def open_new_port(client):

    port = 3000
    security_group_id = 'sg-081498b5806dc1264'
    
    existing_ports = get_open_ports(client, security_group_id)
    

    for new_port in range(3000, 7000):  # You can adjust this range as needed
        if new_port not in existing_ports:
           port = new_port
           break
           
           
    # Define the inbound rule you want to add
    ip_protocol = 'tcp'  # or 'udp', 'icmp', etc.
    from_port = port  # start port
    to_port = port  # end port
    cidr_ip = '0.0.0.0/0'  # CIDR notation for IP range
    
    # Authorize the inbound rule
    response = client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {
                'IpProtocol': ip_protocol,
                'FromPort': from_port,
                'ToPort': to_port,
                'IpRanges': [{'CidrIp': cidr_ip}]
            }
        ]
    )
    
    return port
    
    
    
    
def get_instances_with_tag(tag_key, tag_value, client):
    response = client.describe_instances(
        Filters=[
            {
                'Name': 'tag:'+tag_key,
                'Values': [tag_value]
            }
        ]
    )
    
    return response
    
    
def get_open_ports(client, security_group_id):
    
    existing_permissions = client.describe_security_groups(GroupIds=[security_group_id])['SecurityGroups'][0]['IpPermissions']
    existing_ports = set()
    
    for permission in existing_permissions:
        if 'FromPort' in permission and 'ToPort' in permission:
            existing_ports.add(permission['FromPort'])
               
    return existing_ports
    
    
    
    

def get_all_containers(client, client_ssm):
    instance_id = 'i-0111c349419c23dfa'
    container_ports = get_container_ports(client_ssm, instance_id)
    delete_unused_inbound_rules(client, instance_id, container_ports)
    
    # get all running container ids and port
    docker_ps_command = "docker ps -q | xargs -n 1 docker inspect --format '{{.Id}}:{{.Config.Image}}:{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}:{{range $key, $value := .NetworkSettings.Ports}}{{if $value}}{{(index $value 0).HostPort}}{{end}}{{end}}'"



    # Send command to list containers
    response = client_ssm.send_command(
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [docker_ps_command]},
        InstanceIds=[instance_id],
    )

    # Get the command invocation details
    command_id = response['Command']['CommandId']

    # Wait for the command to complete
    waiter = client_ssm.get_waiter('command_executed')
    waiter.wait(CommandId=command_id, InstanceId=instance_id)

    # Retrieve the command output
    output = client_ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )['StandardOutputContent']
    
    
    container_info_list = output.strip().split('\n')
    
    print(container_info_list)

    # Initialize a list to store extracted information
    extracted_info = []
    
    # Iterate over each container info and extract ID, IP, and port
    for container_info in container_info_list:
    # Split container info by ':'
        info_parts = container_info.split(':')
        # if len(info_parts) != 3:
        #     # Skip this container info if it doesn't match the expected format
        #     continue
    
        # Extract ID, IP, and port
        container_id,server_name ,ip, port = info_parts
        print(info_parts)
    
        # Append the extracted information to the list
        extracted_info.append({
            'containerID': container_id,
            'containerIP': ip,
            'serverName': server_name,
            'url': f'http://3.110.131.140:{port}'
        })

    return extracted_info
    
    

    
    
def get_container_ports(client_ssm, instance_id):
    docker_ps_command = "docker ps --format '{{.Ports}}'"

    response = client_ssm.send_command(
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [docker_ps_command]},
        InstanceIds=[instance_id],
    )

    command_id = response['Command']['CommandId']

    waiter = client_ssm.get_waiter('command_executed')
    waiter.wait(
        CommandId=command_id,
        InstanceId=instance_id
    )

    output = client_ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )['StandardOutputContent']


    output_list = output.strip().split('\n')

    container_ports = []
    
    # Extract port information from the Docker PS output
    for row in output_list:
        container_ports.append(int(row.split(':')[1].split('->')[0]))

    return container_ports
    
    
def get_open_ports(client, security_group_id):
    existing_permissions = client.describe_security_groups(GroupIds=[security_group_id])['SecurityGroups'][0]['IpPermissions']
    existing_ports = set()

    for permission in existing_permissions:
        if 'FromPort' in permission and 'ToPort' in permission:
            if permission['FromPort'] not in [22, 80, 443, -1]:
                existing_ports.add(permission['FromPort'])

    return existing_ports
    

def delete_unused_inbound_rules(client, instance_id, container_ports):
    security_group_id = 'sg-081498b5806dc1264'
    existing_ports = get_open_ports(client, security_group_id)
    
    print('existing_ports', existing_ports)
    print('container_ports', container_ports)
    
    # Remove inbound rules for ports not used by running containers
    for port in existing_ports:
        if port not in container_ports:
            client.revoke_security_group_ingress(
                GroupId = 'sg-081498b5806dc1264',
                IpPermissions=[{
                    'IpProtocol': 'tcp',
                    'FromPort': port,
                    'ToPort': port,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }]
            )