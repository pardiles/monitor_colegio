import boto3

def handler(event, context):
    ec2 = boto3.client('ec2', region_name='us-east-2')
    ec2.start_instances(InstanceIds=['i-00d2a56f9b8078a10'])
    return {'statusCode': 200}
