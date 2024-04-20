import json
import boto3

def lambda_handler(event, context):
    client_ssm = boto3.client('ssm')
    
    instance_id = 'i-00eb45be517316429'
    
    service_type = 'ec2'
    service_name = 'tarun'
    

    terraform_command = f'''
        echo '\\nmodule "{service_name}" {{
          source = "./module/ec2"
          instance_name = "{service_name}"
        }}' >> module.tf
    '''
    
    output_command = f''' 
     echo '\\noutput "public_ip" {{
          value = module.{service_name}.public_ip
        }}' > outputs.tf
        
    '''


    # 'terraform fmt && terraform init && terraform apply -auto-approve'

    commands = ['cd /home/ubuntu/terraform', terraform_command, output_command ,'terraform fmt', 'terraform init > init.out', 'terraform apply -auto-approve > apply.out', 'terraform output public_ip']
    
    # commands = ['cd /home/ubuntu/terraform',terraform_command, output_command ]

    
    
    response = client_ssm.send_command(
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': commands },
        InstanceIds=[instance_id],
    )
    
    command_id = response['Command']['CommandId']
    
    print("command id: ", command_id)
    



    
    waiter = client_ssm.get_waiter('command_executed')
    waiter.wait(
        CommandId=command_id,
        InstanceId=instance_id
    )

    # # Retrieve the command output
    response = client_ssm.get_command_invocation(
        CommandId = command_id,
        InstanceId=instance_id
    )['StandardOutputContent']

    return {
        'statusCode': 200,
        'body': json.loads(json.dumps(response, default=str))
        # 'body': terraform_command
    }
