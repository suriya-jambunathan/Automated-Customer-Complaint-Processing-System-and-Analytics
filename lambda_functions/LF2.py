import openai
import nltk
import re
import contractions
import json
import os
import boto3
import psycopg2
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

API_KEY = os.environ['API_KEY']
openai.api_key = API_KEY

# Download the NLTK stop words data
nltk.data.path.append("./nltk_data")

stop_words = set(nltk.corpus.stopwords.words('english'))
stop_words = [stop_word for stop_word in stop_words if stop_word not in [contraction_key.lower() for contraction_key in list(contractions.contractions_dict.keys())]]
    
# Function to remove stop words
def remove_stopwords(text):
    # words = nltk.word_tokenize(text)
    words = text.split(' ')
    filtered_words = [word for word in words if word.lower() not in stop_words]
    return ' '.join(filtered_words)

def expand_contractions(text):
    expanded_words = []    
    for word in text.split():
      # using contractions.fix to expand the shortened words
      expanded_words.append(contractions.fix(word))   

    return ' '.join(expanded_words)
    
def remove_special_characters(text):
    # Remove special characters and keep only alphanumeric and space
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return cleaned_text

def preprocess_text(text):
    return remove_special_characters(expand_contractions(remove_stopwords(text)))

def estimate_tokens(sentence):
    return len(sentence)//4

def gen_gpt_msg(complaints, token_limit=15000):
    context_msg = f"""Classify the following complaint texts into a category (Admin, Developers, Payments, Quality Control, Logistics, Miscellaneous) and to a severity level (1 to 5). 
    Response format: 1. <category>,<severity> for each complaint text 
    Complaint Texts:\n"""
    context_tokens = estimate_tokens(context_msg)
    
    messages = []
    
    beginning = True
    for i in range(len(complaints)):
        if beginning:
            itr = 1
            cur_message = context_msg
            cur_tokens = context_tokens
            beginning = False
        cur_complaint = f"{itr}. {preprocess_text(complaints[i])}\n"
        cur_complaint_tokens = estimate_tokens(cur_complaint)
        itr += 1
        if cur_tokens + cur_complaint_tokens <= token_limit:
            cur_tokens += cur_complaint_tokens
            cur_message += cur_complaint
        else:
            beginning = True
            messages.append(cur_message)
            
    try:
        messages.append(cur_message)
    except:
        pass
            
    return messages

def classify_complaints(complaints, model="gpt-3.5-turbo"):
    
    num_tokens_used = 0
    severities = []
    teams = []
    
    complaint_messages = [{"role": "user", "content": message} for message in gen_gpt_msg(complaints)]
    for message in complaint_messages:
        try:
            response = openai.chat.completions.create(
                        model=model,
                        messages=[message],
                        temperature=0
                        )
        except Exception as e:
            print(str(e))
        num_tokens_used += response.usage.total_tokens
        
        preds = [pred.split('. ')[-1].split(', ') for pred in response.choices[0].message.content.split('\n')]
        
        teams.extend([pred[0] for pred in preds])
        severities.extend([int(pred[1]) for pred in preds])
        
    return teams, severities, num_tokens_used

def poll_sqs_messages(max_messages=1000, wait_time=20):
    """
    Poll messages from an SQS queue in batches.

    :param queue_url: URL of the SQS queue.
    :param max_messages: Maximum number of messages to retrieve (max 10).
    :param wait_time: Long polling wait time in seconds (max 20).
    """
    sqs = boto3.client('sqs')
    queue_url = "https://sqs.us-east-1.amazonaws.com/230469209761/complaintsQ"
    
    all_messages = []
    
    while True:
        try:
            # Retrieve messages from the SQS queue
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=wait_time
            )
            messages = response.get('Messages', [])
            if not messages:
                print("No messages in the queue.")
                break
                
            else:
                if len(all_messages) + len(messages) > max_messages:
                    break
                
                all_messages.extend([eval(message['Body'].replace('null', 'None')) for message in messages])
                
                for message in messages:
                    # Process each message
                    print("Received message:", message['Body'])
        
                    # Delete message from the queue after processing
                    delete_sqs_message(sqs, message['ReceiptHandle'])
                        
    
        except ClientError as e:
            print("Error polling messages:", e)
            break

    return all_messages

def delete_sqs_message(sqs_client, receipt_handle):
    """
    Delete a message from the SQS queue.

    :param sqs_client: Boto3 SQS client.
    :param queue_url: URL of the SQS queue.
    :param receipt_handle: Receipt handle of the message to be deleted.
    """
    queue_url = "https://sqs.us-east-1.amazonaws.com/230469209761/complaintsQ"
    try:
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
    except ClientError as e:
        print("Error deleting message:", e)

def send_to_sqs(complaint_record):
    sqs = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/230469209761/complaintsQ' 

    try:
        # Send message to SQS queue
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(complaint_record)
        )
        print("Message sent to SQS:", response.get('MessageId'))

    except ClientError as e:
        print("Failed to send message to SQS:", e)
        raise e
        
#Get Data from DynamoDB
def query_dynamodb(ticket_ids):
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table_name = 'complaints'
    table = dynamodb.Table(table_name)
    
    # Create a list of Key objects for BatchGetItem
    ticket_id_keys = [{'ticket_id': ticket_id} for ticket_id in ticket_ids]
    
    # Perform the BatchGetItem operation
    response = dynamodb.batch_get_item(
        RequestItems={
            table_name: {
                'Keys': ticket_id_keys
                }
            }
        )
    
    complaints_dict = [complaint_dict for complaint_dict in response['Responses'][table_name] if complaint_dict['status'] == 'new']
    
    return complaints_dict

# Update Data in DynamoDB
def update_dynamodb(complaints_dict):
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table_name = 'complaints'
    table = dynamodb.Table(table_name)
    
    # Perform the batch write operation
    try:
        with table.batch_writer() as batch:
            # Put items
            for complaint_dict in complaints_dict:
                complaint_dict['status'] = 'delegated'
                batch.put_item(Item=complaint_dict)
    
        print("Batch write operation successful.")
        return True
    except Exception as e:
        print("Error during batch write operation:", e)
        return False
    
# Push Data to RedShift
def update_redshift(rows):
    # Initialize RedShift client
    redshift = boto3.client('redshift')
    response = redshift.get_cluster_credentials(DbUser='awsuser',
                                              DbName='complaints',
                                              ClusterIdentifier='redshift-cluster-1',
                                              DurationSeconds=3600)
                                              
    conn = psycopg2.connect(host='redshift-cluster-1.cujjg3fofukv.us-east-1.redshift.amazonaws.com',
                            port=5439,
                            dbname='complaints',
                            user=response['DbUser'],
                            password=response['DbPassword']
                        )
                        
    cursor = conn.cursor()
    
    try:
        base_query = "INSERT INTO complaints.analytics.tickets (Ticket_id, Ticket_raised_timestamp, Team_name, Severity_level, Status, Resolved_timestamp)"
        rows_repr = ','.join([str(f"('{row[0]}','{row[1]}','{row[2]}','{row[3]}','{row[4]}',NULL)") for row in rows])
        cursor.execute(" ".join([base_query, "VALUES", rows_repr]))
        conn.commit()
        print("Data inserted successfully.")
        return 1
    except Exception as e:
        print("Error inserting data:", e)
        conn.rollback()
        return 0

#Send email for SES
def send_email(receiver_email, subject, message):
    # Initialize SES client
    ses_client = boto3.client("ses", region_name="us-east-1")
    
    sender_email = os.environ['EMAIL']
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    # Set message body
    body = MIMEText(message, 'html')
    msg.attach(body)

    response = ses_client.send_raw_email(
        Source=sender_email,
        Destinations=[receiver_email],
        RawMessage={"Data": msg.as_string()}
    )
    
    return response

def gen_team_msg(team_name, ticket_ids, complaints, severity_levels):
    base_msg = f"""
    <html>
      <body>
        <p><big>List of complaints corresponding to your <strong>{team_name}</strong> Team:</big></p>
        <table border="1">
          <tr>
            <th>Ticket ID</th>
            <th>Complaint</th>
            <th>Severity</th>
          </tr>
    """
    end_msg = """
        </table>
        <p><small><em>This is an automated email. Please do not reply.</em></small></p>
      </body>
    </html>
    """
    msg = base_msg
    for i in range(len(ticket_ids)):
        cur_msg = f"""
              <tr>
                <td>{ticket_ids[i]}</td>
                <td>{complaints[i]}</td>
                <td>{severity_levels[i]}</td>
              </tr>
        """
        msg += cur_msg
    msg += end_msg
    
    return msg
    
def gen_user_msg(user_id, ticket_ids, complaints):
    base_msg = f"""
    <html>
      <body>
        <p><big>Dear <strong>{user_id}</strong>,</big></p>
        <p><big>Below are the list of complaints corresponding to your chat with us</big></p>
        <table border="1">
          <tr>
            <th>Ticket ID</th>
            <th>Complaint</th>
          </tr>
    """
    end_msg = """
        </table>
        <p>We sincerely apologize for any inconvenience you may have experienced. We value your feedback and prioritize customer satisfaction. Please be assured that we are dedicated to promptly addressing your complaint and resolving it to your satisfaction. Thank you for being a valued customer.</p>
        <p><small><em>This is an automated email. Please do not reply.</em></small></p>
      </body>
    </html>
    """
    msg = base_msg
    for i in range(len(ticket_ids)):
        cur_msg = f"""
              <tr>
                <td>{ticket_ids[i]}</td>
                <td>{complaints[i]}</td>
              </tr>
        """
        msg += cur_msg
    msg += end_msg
    
    return msg
    
def lambda_handler(event, context):
    complaints_dict = poll_sqs_messages()

    # ticket_ids = ['692c7b11-c1d0-4c15-92a7-694a0ef6653b', '7ea3db0c-0e3e-476d-b759-0624798b20e7', 'f6a4808d-4c35-46b2-aa2b-c26000b12857', 'e63e6179-27dd-4145-81ad-a139e7c12a44']
    # complaints_dict = query_dynamodb(ticket_ids)
    
    if len(complaints_dict) > 0:
        complaints = [complaint_dict['complaint_text'] for complaint_dict in complaints_dict]
        ticket_ids = [complaint_dict['ticket_id'] for complaint_dict in complaints_dict]
        user_ids = [complaint_dict['user_id'] for complaint_dict in complaints_dict]
        ticket_raised_timestamps = [complaint_dict['timestamp'] for complaint_dict in complaints_dict]
        
        try:
            team_names, severity_levels, num_tokens_used = classify_complaints(complaints)
        except:
            # Setting default case
            team_names, severity_levels, num_tokens_used = ['Miscellaneous' for i in range(len(complaints))], [3 for i in range(len(complaints))], 0
        
        print(team_names, severity_levels, num_tokens_used )
        
        rows = []
        segregated_complaints_dict = {}
        user_specific_complaints_dict = {}
        for i in range(len(ticket_ids)):
            row = [ticket_ids[i], ticket_raised_timestamps[i], team_names[i], severity_levels[i], 'delegated', None]
            if team_names[i] not in list(segregated_complaints_dict.keys()):
                segregated_complaints_dict[team_names[i]] = {'ticket_ids': [], 'complaints': [], 'severity_levels': []}
            if user_ids[i] not in list(user_specific_complaints_dict.keys()):
                user_specific_complaints_dict[user_ids[i]] = {'ticket_ids': [], 'complaints': []}
            
            segregated_complaints_dict[team_names[i]]['ticket_ids'].append(ticket_ids[i])
            segregated_complaints_dict[team_names[i]]['complaints'].append(complaints[i])
            segregated_complaints_dict[team_names[i]]['severity_levels'].append(severity_levels[i])
            
            user_specific_complaints_dict[user_ids[i]]['ticket_ids'].append(ticket_ids[i])
            user_specific_complaints_dict[user_ids[i]]['complaints'].append(complaints[i])
            
            rows.append(row)
            
        for team_name in list(segregated_complaints_dict.keys()):
            team_ticket_ids = segregated_complaints_dict[team_name]['ticket_ids']
            team_complaints = segregated_complaints_dict[team_name]['complaints']
            team_severities = segregated_complaints_dict[team_name]['severity_levels']
            
            team_msg = gen_team_msg(team_name, team_ticket_ids, team_complaints, team_severities)
            
            subject = "Automated Complaint Delegation"
            send_email('vamsikrishh0099@gmail.com', subject, team_msg)
            print(f"Delegated to {team_name} Team")
            
        for user_id in list(user_specific_complaints_dict.keys()):
            user_ticket_ids = user_specific_complaints_dict[user_id]['ticket_ids']
            user_complaints = user_specific_complaints_dict[user_id]['complaints']
            
            subject = "Confirmation of Receipt for Your Complaints"
            user_msg = gen_user_msg(user_id, user_ticket_ids, user_complaints)
            
            send_email(user_id, subject, user_msg)
            print(f"Reported to {user_id} user")
            
        rs_success = update_redshift(rows)
        if rs_success:
            ddb_success = update_dynamodb(complaints_dict)
            
        if not (rs_success or ddb_success):
            for complaint_record in complaints_dict:
                send_to_sqs(complaint_record)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }