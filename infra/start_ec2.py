import boto3

def handler(event, context):
    ec2 = boto3.client('ec2', region_name='us-east-2')
    ec2.start_instances(InstanceIds=['i-07385fb3d20c2749b'])
    return {'statusCode': 200, 'body': 'EC2 starting'}
