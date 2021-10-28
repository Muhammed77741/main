import sys
import os

from confluent_kafka import Consumer, KafkaException, KafkaError

if __name__ == '__main__':
    topics = ['comverse_15min_test']
    conf = {
         'bootstrap.servers': '172.28.58.54:9092',
         'group.id': 'test-comverse-group',
         'session.timeout.ms': 6000,
         'default.topic.config': {'auto.offset.reset': 'earliest'},
         'security.protocol': 'SASL_PLAINTEXT',
         'sasl.mechanisms': 'PLAIN',
         'sasl.username': 'blstriggers',
         'sasl.password': '7pdS7iTkNDfn'
    }

c = Consumer(**conf)
c.subscribe(topics)
while True:
    msg = c.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        print("Consumer error: {}".format(msg.error()))
        continue

    print('{}'.format(msg.value().decode('utf-8')))

c.close()