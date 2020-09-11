import json
import uuid
from db_models.mongo_setup import global_init
from db_models.models.cache_model import Cache
import init
from caption_service import predict
import globals
import numpy


def send_to_topic(topic, value_to_send_dic):
    # default=convert only used in this project
    data_json = json.dumps(value_to_send_dic)
    init.producer_obj.send(topic, value=data_json)


if __name__ == "__main__":
    global_init()
    print('main fxn')
    for message in init.consumer_obj:
        message = message.value
        db_key = str(message)
        print(db_key, 'db_key')
        db_object = Cache.objects.get(pk=db_key)
        file_name = db_object.file_name
        init.redis_obj.set(globals.RECEIVE_TOPIC, file_name)
        print('after redis')
        if db_object.is_doc_type:
            """document"""
            print('in doc type')
            images_array = []
            for image in db_object.files:
                pdf_image = str(uuid.uuid4()) + ".jpg"
                with open(pdf_image, 'wb') as file_to_save:
                    file_to_save.write(image.file.read())
                images_array.append(pdf_image)
            full_res_list = []
            text_res_list = []
            for image in images_array:
                image_results = predict(image, doc=True)
                full_res = image_results["full_res"]
                text_res = image_results["text_res"]
                full_res_list.append(full_res)
                text_res_list.append(text_res)

            full_res = {
                "container_name": globals.RECEIVE_TOPIC,
                "file_name": file_name,
                "captions": full_res_list,
                "is_doc_type": True
            }
            text_res = {
                "container_name": globals.RECEIVE_TOPIC,
                "file_name": file_name,
                "captions": text_res_list,
                "is_doc_type": True
            }
            print(full_res, "full_res")
            send_to_topic(globals.SEND_TOPIC_FULL, value_to_send_dic=full_res)
            send_to_topic(globals.SEND_TOPIC_TEXT, value_to_send_dic=text_res)
            init.producer_obj.flush()

        else:
            """image"""
            print('in image type')
            if db_object.mime_type in globals.ALLOWED_IMAGE_TYPES:
                with open(file_name, 'wb') as file_to_save:
                    file_to_save.write(db_object.file.read())
                image_results = predict(file_name)
                
                full_res = {
                "container_name": globals.RECEIVE_TOPIC,
                "file_name": file_name,
                "captions": image_results["full_res"],
                "is_doc_type": False
                }
                text_res = {
                    "container_name": globals.RECEIVE_TOPIC,
                    "file_name": file_name,
                    "captions": image_results["text_res"],
                    "is_doc_type": False
                }
                print(full_res, 'full_res')
                send_to_topic(globals.SEND_TOPIC_FULL, value_to_send_dic=full_res)
                send_to_topic(globals.SEND_TOPIC_TEXT, value_to_send_dic=text_res)
                init.producer_obj.flush()
