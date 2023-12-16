import json
import boto3
import random
import string
import requests
import os
from datetime import datetime
import uuid

def lambda_handler(event, context):
    intent_name = event['sessionState']['intent']['name']

    if intent_name == 'CheckComplaintStatus':
        return handle_check_complaint_status(event)
    elif intent_name == 'ResolveComplaint':
        return handle_resolve_complaint(event)
    elif intent_name == 'SubmitComplaint':
        return handle_submit_complaint(event)
    elif intent_name == "WelcomeIntent":
        return handle_branch(event)
    else:
        return close(event, 'Fulfilled', 'Sorry, I did not understand that.')



def elicit_intent(event, intent_name):
    # Setup to elicit the specific intent based on intent_name
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'ElicitIntent'
            },
            'intent': {
                'name': intent_name,
                'slots': event['sessionState']['intent']['slots']
            }
        },
        'messages': [{
            'contentType': 'PlainText',
            'content': f'Let’s proceed with {intent_name}.'
        }]
    }

        
def handle_branch(event):
    print("event in branch:")
    print(event)
    # Your existing logic
    complaint_text = get_slot_value(event, 'complaint_type')
    print("complaint text: ")
    print(complaint_text)
    ####
    intent_map = {"check_status":"check","resolve_status":"resolve","new_complaint":"new"}

    

    # prompt_text = f"""Map the complaint text into a category (check_status, resolve_status, new_complaint)
    # complaint text: {complaint_text}
    #  Response format: <category>"""
     
    prompt_text = f""""Determine the user's intent and respond with only one word: 'check_status', 'resolve_status', or 'new_complaint'.
    User: {complaint_text}"""

    url = "https://api.openai.com/v1/chat/completions"
    headers = {'Authorization': f'Bearer {os.environ["gpt_api_key"]}'}
    body = {
  "model": "gpt-3.5-turbo",
  "messages": [{"role": "user", "content": prompt_text}],
  "temperature": 0
    }
    
    response = requests.post(url, headers=headers, json=body)
    
    
    print(response.json())
    print(response.content)
    print(response.json()["choices"][0]["message"]["content"])
    intent_word = response.json()["choices"][0]["message"]["content"]
    intent_word = intent_map[intent_word]
    print(f"intent word is:{intent_word}")
    # Set the intent_word slot value
    #intent_word = "check"  # check, resolve, new
    # Update the current intent's slots
    current_intent = event['sessionState']['intent']
    current_intent['slots']['intent_word'] = {
        'value': {
            'originalValue': intent_word,
            'interpretedValue': intent_word,
            'resolvedValues': [intent_word]
        }
    }
    print("current intent:")
    print(current_intent)

    # Return the modified event to stay in the same intent with updated slots
    
    ################################
    ans = {
        'sessionState': {
            'dialogAction': {
                'type': 'Delegate',
                'slots': current_intent['slots']
            },
            'intent': current_intent,
            'sessionAttributes': event.get('sessionState', {}).get('sessionAttributes', {})
        },
        'messages': [{
            'contentType': 'PlainText',
            'content': f'Continuing with the updated slot value for intent_word: {intent_word}'
        }],
        'requestAttributes': event.get('requestAttributes')
    }
    print("return by handle:")
    print(ans)
    return ans
    #################################
    # if intent_word == "check":
    #     elicit_slot(event, 'ticket_id', 'CheckComplaintStatus', 'Sure, let me check that for you. Please enter the ticket_id you receieved over email.')
    # elif intent_word == "resolve":
    #     elicit_slot(event, 'ticket_id', 'ResolveComplaint', 'Okay. Please enter the ticket_id you received over email when you raised the complaint.')
    # elif intent_word == "new":
    #     elicit_slot(event, 'isPreviousOrder', 'SubmitComplaint', "I'm sorry for the inconvenience. Is your complaint related to any previous order that you placed?")
    # else:
    #     print("giving old response:")
    #     return {
    #     'sessionState': {
    #         'dialogAction': {
    #             'type': 'Delegate',
    #             'slots': current_intent['slots']
    #         },
    #         'intent': current_intent,
    #         'sessionAttributes': event.get('sessionState', {}).get('sessionAttributes', {})
    #     },
    #     'messages': [{
    #         'contentType': 'PlainText',
    #         'content': f'Continuing with the updated slot value for intent_word: {intent_word}'
    #     }],
    #     'requestAttributes': event.get('requestAttributes')
    #     }

def handle_check_complaint_status(event):
    ticket_id = get_slot_value(event, 'ticket_id')
    # Add logic to fetch status from your system
    
    dynamodb = boto3.resource('dynamodb')

    try:
        # Assuming the table name is 'complaints'
        table = dynamodb.Table('complaints')

        # Fetching the complaint status based on complaint_id
        response = table.get_item(
            Key={'ticket_id': ticket_id.lower()}
        )

        # Extract the status if the item is found
        status = response['Item'].get('status', 'No status available') if 'Item' in response else 'Ticket not found'

    except ClientError as e:
        print(f"An error occurred: {e}")
        status = 'Unable to fetch the status. got error.'

    return close(event, 'Fulfilled', f'The status of ticket {ticket_id} is {status}.')


def handle_resolve_complaint(event):
    ticket_id = get_slot_value(event, 'ticket_id')
    print(ticket_id)
    
    # Initialize a boto3 resource for DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('complaints')

    try:
        # Check if the ticket exists
        response = table.get_item(
            Key={'ticket_id': ticket_id.lower()}
        )
        if 'Item' not in response:
            # Ticket ID not found in the table
            return elicit_slot(event, 'ticket_id', 'ResolveComplaint', 'Ticket ID not found. Please enter a valid ticket ID.')

        # If ticket exists, update the status to resolved
        dynamodb_client = boto3.client('dynamodb')
        update_response = dynamodb_client.update_item(
            TableName='complaints',
            Key={'ticket_id': {'S': ticket_id.lower()}},
            UpdateExpression='SET #status = :resolved',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':resolved': {'S': 'resolved'}}
        )
        return close(event, 'Fulfilled', f'Ticket {ticket_id} has been marked as resolved.')
    except ClientError as e:
        return close(event, 'Failed', f'Error processing your request: {e}')

def elicit_slot(event, slot_to_elicit, intent_name, message):
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'ElicitSlot',
                'slotToElicit': slot_to_elicit
            },
            'intent': {
                'name': intent_name,
                'slots': event['sessionState']['intent']['slots']
            }
        },
        'messages': [{
            'contentType': 'PlainText',
            'content': message
        }]
    }

def handle_submit_complaint(event):
    order_id = get_slot_value(event, 'order_id')
    if order_id == 'null':
        order_id = None
    complaint_text = get_slot_value(event, 'complaint_text')
    user_id = event["sessionId"].replace("-at-","@")  # Replace with actual user ID
    ticket_id = str(uuid.uuid4())
    ticket_id = ticket_id.lower()
    #ticket_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("event in submit")
    print(event)

    # Add logic to save the complaint in your system
    complaint_record = {
        'ticket_id': ticket_id,
        'user_id': user_id,
        'order_id': order_id,
        'complaint_text': complaint_text,
        'status':'new',
        'timestamp': current_timestamp  # Generate current timestamp
    }
    # Save complaint_record to your database
    dynamodb = boto3.resource('dynamodb')

    try:
        # Assuming the table name is 'complaints'
        table = dynamodb.Table('complaints')

        # Saving the complaint record to the DynamoDB table
        table.put_item(Item=complaint_record)
        
        send_to_sqs(complaint_record)


    except ClientError as e:
        print(f"An error occurred: {e}")
        return close(event, 'Failed', 'Failed to submit your complaint.')

    return close(event, 'Fulfilled', f'Your complaint has been submitted with ticket ID: {ticket_id}. Thank you for your patience')


    #return close(event, 'Fulfilled', f'Your complaint has been submitted with ticket ID: {ticket_id}.')

def get_slot_value(event, slot_name):
    return event['sessionState']['intent']['slots'][slot_name]['value']['interpretedValue']

def close(event, fulfillment_state, message):
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'Close'
            },
            'intent': {
                'name': event['sessionState']['intent']['name'],
                'state': fulfillment_state,
            }
        },
        'messages': [{
            'contentType': 'PlainText',
            'content': message
        }]
    }


def send_to_sqs(complaint_record):
    sqs = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/230469209761/complaintsQ'  # Replace with your Queue URL

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