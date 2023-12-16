import boto3
import time
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    # Initialize boto3 clients
    redshift_client = boto3.client('redshift-data')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('complaints')

    # Redshift cluster info
    cluster_id = 'redshift-cluster-1'
    database = 'complaints'
    db_user = 'awsuser'
    # Credentials should be managed securely

    # SQL to select 5 random records with status not 'resolved'
    select_sql = """
    SELECT ticket_id, status
    FROM analytics.tickets
    WHERE status <> 'resolved'
    ORDER BY RANDOM()
    LIMIT 2;
    """

    # Execute the SELECT query
    try:
        select_response = redshift_client.execute_statement(
            ClusterIdentifier=cluster_id,
            Database=database,
            DbUser=db_user,
            Sql=select_sql
        )
        query_id = select_response['Id']

        # Check query execution status
        while True:
            status_response = redshift_client.describe_statement(Id=query_id)
            status = status_response['Status']
            if status in ['FINISHED', 'FAILED', 'ABORTED']:
                break
            time.sleep(1)  # Sleep for a short period before checking again
    except ClientError as e:
        print(e)
        return

    if status != 'FINISHED':
        print(f"Query did not finish successfully. Status: {status}")
        return

    # Fetch query results
    try:
        result_response = redshift_client.get_statement_result(Id=query_id)
        ticket_records = [
            {'ticket_id': record[0]['stringValue'], 'status': record[1]['stringValue']}
            for record in result_response['Records']
        ]
    except ClientError as e:
        print(e)
        return

 
    for record in ticket_records:
        ticket_id = record['ticket_id']
        new_status = 'pending' if record['status'] == 'delegated' else 'resolved'
        resolved_timestamp_sql = ", resolved_timestamp = current_timestamp" if new_status == 'resolved' else ""

        # SQL to update Redshift
        update_sql = f"""
        UPDATE analytics.tickets
        SET status = '{new_status}'{resolved_timestamp_sql}
        WHERE ticket_id = '{ticket_id}';
        """

        try:
            # Execute the UPDATE query in Redshift
            redshift_client.execute_statement(
                ClusterIdentifier=cluster_id,
                Database=database,
                DbUser=db_user,
                Sql=update_sql
            )
            
            # Update the item in DynamoDB
        
            table.update_item(
            Key={'ticket_id': ticket_id.upper()},
            UpdateExpression='SET #st = :new_status',
            ExpressionAttributeNames={'#st': 'status'},  # Placeholder for reserved keyword
            ExpressionAttributeValues={':new_status': new_status}
        )
        except ClientError as e:
            print(e)
            continue
