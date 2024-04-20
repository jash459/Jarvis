import json
import boto3

def lambda_handler(event, context):
    client_ssm = boto3.client('ssm')
    
    instance_id = 'i-012e904b8c39a26b9'
    command = "ls"
     
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
    resposne = client_ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )['StandardOutputContent']

    return {
        'statusCode': 200,
        'body': json.loads(json.dumps(response, default=str))
    }
