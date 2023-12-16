import json
import boto3
import datetime
import uuid

def generate_session_id():
    # Generate a unique identifier for the session
    unique_identifier = str(uuid.uuid4())
    
    # Generate the timestamp when the conversation starts
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Combine the timestamp and the unique identifier
    session_id = f"{timestamp}-{unique_identifier}"

    return session_id

import boto3
import uuid
from botocore.config import Config

my_config = Config(
    region_name='us-east-1',
    read_timeout=60,  # Read timeout in seconds
    connect_timeout=60,  # Connect timeout in seconds
)


def lambda_handler(event, context):
    # Connect to Lex V2
    client = boto3.client('lexv2-runtime')

    print("Event is: ", event)
    user_id = 'user1'
    bot_id = 'DU8EUHOAUC'  # Replace with your Bot ID DU8EUHOAUC
    bot_alias_id = 'TSTALIASID'  # Replace with your Bot Alias ID TSTALIASID
    locale_id = 'en_US'  # Replace with your Locale ID


    try:
        email_id = event['messages'][0]['unstructured']['id']
        print(email_id)
    except KeyError:
        email_id = "testemail.com"
    
    email_id = email_id.replace("@","-at-")

    msg_text = event['messages'][0]['unstructured']['text']
    print(msg_text)
    

    response = client.recognize_text(
        botId=bot_id,
        botAliasId=bot_alias_id,
        localeId=locale_id,
        sessionId=email_id,
        text=msg_text
    )
    print("initial response:")
    print(response)


    # Check if there is a slot to elicit
    if 'sessionState' in response:
        if 'intent' in response['sessionState']:
            intent_state = response['sessionState']['intent']['state']
            if intent_state == 'InProgress' and 'slotToElicit' in response['sessionState']['intent']:
                slot_to_elicit = response['sessionState']['dialogAction']['slotToElicit']
                # Get the prompt for the slot to elicit
                for message in response.get('messages', []):
                    if message['contentType'] == 'PlainText':
                        prompt_message = message['content']
                        break
                else:
                    prompt_message = "What is the value for {}?".format(slot_to_elicit)

                bot_response = {
                    "messages": [
                        {
                            "type": "unstructured",
                            "unstructured": {
                                "id": user_id,
                                "text": prompt_message,
                                "timestamp": "",
                                'sessionId': email_id
                            }
                        }
                    ]
                }
                return bot_response

    # Default response if no slot elicitation is required
    print("reached end")
    bot_response = {
        "messages": [
            {
                "type": "unstructured",
                "unstructured": {
                    "id": user_id,
                    "text": response['messages'][0]['content'] if 'messages' in response else '',
                    "timestamp": "",
                    'sessionId': email_id
                }
            }
        ]
    }

    return bot_response