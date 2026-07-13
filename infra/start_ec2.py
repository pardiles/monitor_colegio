import boto3

def handler(event, context):
    ec2 = boto3.client('ec2', region_name='us-east-2')
    ec2.start_instances(InstanceIds=['i-0ad4f13769d8bea94'])
    return {'statusCode': 200}
