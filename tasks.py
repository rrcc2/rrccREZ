
import os
import json
from redis import Redis
from logger import log
from celery_worker import celery  # 🔁 Import du Celery app

SERVER = os.getenv("SERVER")
API_KEY = os.getenv("API_KEY")
SECOND_MESSAGE_LINK = os.getenv("SECOND_MESSAGE_LINK")

# ✅ Connexion Redis
REDIS_URL = os.getenv("REDIS_URL")
redis_conn = Redis.from_url(REDIS_URL)

def get_conversation_key(number):
    return f"conv:{number}"

def is_archived(number):
    return redis_conn.sismember("archived_numbers", number)

def archive_number(number):
    redis_conn.sadd("archived_numbers", number)

def mark_message_processed(number, msg_id):
    redis_conn.sadd(f"processed:{number}", msg_id)

def is_message_processed(number, msg_id):
    return redis_conn.sismember(f"processed:{number}", msg_id)

def send_request(url, post_data):
    import requests
    log(f"🌐 Requête POST → {url} | data: {post_data}")
    try:
        response = requests.post(url, data=post_data)
        data = response.json()
        log(f"📨 Réponse reçue : {data}")
        return data.get("data")
    except Exception as e:
        log(f"❌ Erreur POST : {e}")
        return None

def send_single_message(number, message, device_slot):
    log(f"📦 Envoi à {number} via SIM {device_slot}")
    return send_request(f"{SERVER}/services/send.php", {
        'number': number,
        'message': message,
        'devices': device_slot,
        'type': 'mms',
        'prioritize': 1,
        'key': API_KEY,
    })

@celery.task(name="process_message")
def process_message(msg_json):
    try:
        msg = json.loads(msg_json)

        number = msg.get("number")
        msg_id = msg.get("ID")
        device_id = msg.get("deviceID")

        if not number or not msg_id or not device_id:
            return

        conv_key = get_conversation_key(number)
        step = int(redis_conn.hget(conv_key, "step") or 0)

        # 👉 1 seule réponse, une seule fois
        if step != 0:
            return

        reply = (
            f"Pardon, j’étais en tournée et je n’avais pas vu votre message. "
            f"Il faut effectuer la demande via : https://%name%.{SECOND_MESSAGE_LINK} merci"
        )

        redis_conn.hset(conv_key, "step", 1)

        send_single_message(number, reply, device_id)
        mark_message_processed(number, msg_id)

    except Exception as e:
        log(f"Erreur process_message : {e}")
