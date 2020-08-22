from core.model import ModelWrapper, read_image

# imports for env kafka redis
from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka import KafkaConsumer
from json import loads
import base64
import json
import os
import redis

load_dotenv()

KAFKA_HOSTNAME = os.getenv("KAFKA_HOSTNAME")
KAFKA_PORT = os.getenv("KAFKA_PORT")
REDIS_HOSTNAME = os.getenv("REDIS_HOSTNAME")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

RECEIVE_TOPIC = 'MAX_AUDIO'
SEND_TOPIC_FULL = "IMAGE_RESULTS"
SEND_TOPIC_TEXT = "TEXT"


print(f"kafka : {KAFKA_HOSTNAME}:{KAFKA_PORT}")

# Redis initialize
r = redis.StrictRedis(host=REDIS_HOSTNAME, port=REDIS_PORT,
                      password=REDIS_PASSWORD, ssl=True)

# Kafka initialize - To receive img data to process
consumer_max_caption = KafkaConsumer(
    RECEIVE_TOPIC,
    bootstrap_servers=[f"{KAFKA_HOSTNAME}:{KAFKA_PORT}"],
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="my-group",
    value_deserializer=lambda x: loads(x.decode("utf-8")),
)

# Kafka initialize - For Sending processed img data further
producer = KafkaProducer(
    bootstrap_servers=[f"{KAFKA_HOSTNAME}:{KAFKA_PORT}"],
    value_serializer=lambda x: json.dumps(x).encode("utf-8"),
)

for message in consumer_max_caption:
    print('xxx--- inside consumer_max_caption ---xxx')
    print(f"kafka - - : {KAFKA_HOSTNAME}:{KAFKA_PORT}")

    message = message.value
    image_id = message['image_id']
    data = message['data']

    # Setting image-id to topic name(container name), so we can know which image it's currently processing
    r.set(RECEIVE_TOPIC, image_id)

    data = base64.b64decode(data.encode("ascii"))
    image_data = data
    image = read_image(image_data)

    model_wrapper = ModelWrapper()
    preds = model_wrapper.predict(image)
    
    result = {'status': 'error', 'image_id': image_id}
    label_preds = [{'label_id': p[0], 'label': p[1], 'probability': p[2]} for p in [x for x in preds]]
    result['predictions'] = label_preds
    result['status'] = 'ok'

    print(result)

    # sending full and text res(without cordinates or probability) to kafka
    producer.send(SEND_TOPIC_FULL, value=result)
    producer.send(SEND_TOPIC_TEXT, value=result)

    producer.flush()

