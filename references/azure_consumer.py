import os
from azure.eventhub import EventHubConsumerClient
from dotenv import load_dotenv

load_dotenv()  # This line brings all environment variables from .env into os.environ

# Replace the following values with your Azure Event Hub settings
connection_str = os.environ['DEVICE_EVENT_HUB_CONNECTION_STRING']
consumer_group = '$Default'
eventhub_name = os.environ['EVENT_HUB_NAME']

def on_event(partition_context, event):
    # Print the event data content
    print("Received event: ", event.body_as_str())
    # Update the checkpoint so that the program doesn't read the events it has already read
    partition_context.update_checkpoint(event)

def on_error(partition_context, error):
    # Print the error
    if not partition_context:
        print("An error occurred on partition: None,", error)
    else:
        print("An error occurred on partition: {},".format(partition_context.partition_id), error)

client = EventHubConsumerClient.from_connection_string(
    connection_str, consumer_group, eventhub_name=eventhub_name)

print("connected")
try:
    with client:
        client.receive(
            on_event=on_event,
            on_error=on_error,
            starting_position="-1",  # "-1" is from the beginning of the partition.
        )
except KeyboardInterrupt:
    print("Stopped by user")
except Exception as e:
    print(f"An error occurred: {e}")
