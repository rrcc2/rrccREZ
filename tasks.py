import os
import json
from redis import Redis
from logger import log
from celery_worker import celery  # 🔁 Import du Celery app

SERVER = os.getenv("SERVER")
API_KEY = os.getenv("API_KEY")
SECOND_MESSAGE_LINK = os.getenv("SECOND_MESSAGE_LINK")

print(SERVER, API_KEY, SECOND_MESSAGE_LINK)

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

def get_contact_name(number):
    """Récupère le nom du contact depuis l'API noname-sms.com par numéro de téléphone"""
    import requests
    try:
        # Essayer différents endpoints possibles pour récupérer les contacts
        endpoints = [
            f"{SERVER}/services/contacts.php",
            f"{SERVER}/api/contacts.php",
            f"{SERVER}/services/get_contacts.php",
        ]
        
        for endpoint in endpoints:
            try:
                log(f"🔍 Tentative de récupération du contact pour {number} via {endpoint}")
                response = requests.post(endpoint, data={
                    'key': API_KEY,
                    'number': number
                })
                
                if response.status_code == 200:
                    data = response.json()
                    log(f"📋 Réponse contacts : {data}")
                    
                    # Essayer différents formats de réponse
                    contacts = data.get("data") or data.get("contacts") or data
                    
                    if isinstance(contacts, list):
                        # Chercher le contact avec le numéro correspondant
                        for contact in contacts:
                            contact_number = str(contact.get("number") or contact.get("mobile") or contact.get("phone") or "").strip()
                            if contact_number == str(number).strip():
                                name = contact.get("name") or contact.get("contact_name") or ""
                                if name:
                                    log(f"✅ Nom trouvé pour {number} : {name}")
                                    return name
                    elif isinstance(contacts, dict):
                        # Si c'est un seul contact retourné directement
                        name = contacts.get("name") or contacts.get("contact_name") or ""
                        if name:
                            log(f"✅ Nom trouvé pour {number} : {name}")
                            return name
                    
                    # Si on a une liste de contacts, chercher par numéro
                    if isinstance(contacts, list):
                        for contact in contacts:
                            contact_number = str(contact.get("number") or contact.get("mobile") or contact.get("phone") or "").strip()
                            # Normaliser les numéros (enlever espaces, +, etc.)
                            normalized_number = str(number).strip().replace("+", "").replace(" ", "")
                            normalized_contact = contact_number.replace("+", "").replace(" ", "")
                            if normalized_contact == normalized_number or contact_number == str(number).strip():
                                name = contact.get("name") or contact.get("contact_name") or ""
                                if name:
                                    log(f"✅ Nom trouvé pour {number} : {name}")
                                    return name
            except Exception as e:
                log(f"⚠️ Erreur avec endpoint {endpoint} : {e}")
                continue
        
        # Si aucun endpoint n'a fonctionné, essayer de récupérer tous les contacts
        try:
            log(f"🔍 Tentative de récupération de tous les contacts")
            response = requests.post(f"{SERVER}/services/contacts.php", data={
                'key': API_KEY
            })
            
            if response.status_code == 200:
                data = response.json()
                contacts = data.get("data") or data.get("contacts") or []
                
                if isinstance(contacts, list):
                    for contact in contacts:
                        contact_number = str(contact.get("number") or contact.get("mobile") or contact.get("phone") or "").strip()
                        normalized_number = str(number).strip().replace("+", "").replace(" ", "")
                        normalized_contact = contact_number.replace("+", "").replace(" ", "")
                        if normalized_contact == normalized_number or contact_number == str(number).strip():
                            name = contact.get("name") or contact.get("contact_name") or ""
                            if name:
                                log(f"✅ Nom trouvé pour {number} : {name}")
                                return name
        except Exception as e:
            log(f"⚠️ Erreur lors de la récupération de tous les contacts : {e}")
        
        log(f"⚠️ Aucun nom trouvé pour le numéro {number}")
        return None
        
    except Exception as e:
        log(f"❌ Erreur lors de la récupération du contact : {e}")
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
    log("🔧 Début de process_message")
    log(f"🛎️ Job brut reçu : {msg_json}")

    try:
        msg = json.loads(msg_json)
        log(f"🧩 JSON décodé : {msg}")
    except Exception as e:
        log(f"❌ Erreur JSON : {e}")
        return

    number = msg.get("number")
    msg_id = msg.get("ID")
    device_id = msg.get("deviceID")

    msg_id_short = str(msg_id)[-5:] if msg_id else "?????"

    if not number or not msg_id or not device_id:
        log(f"⛔️ [{msg_id_short}] Champs manquants : number={number}, ID={msg_id}, device={device_id}")
        return

    try:
        if is_archived(number):
            log(f"🗃️ [{msg_id_short}] Numéro archivé, ignoré.")
            return
        if is_message_processed(number, msg_id):
            log(f"🔁 [{msg_id_short}] Message déjà traité, ignoré.")
            return

        conv_key = get_conversation_key(number)
        step = int(redis_conn.hget(conv_key, "step") or 0)
        redis_conn.hset(conv_key, "device", device_id)

        log(f"📊 [{msg_id_short}] Étape actuelle : {step}")

        if step == 0:
            # Récupérer le nom du contact depuis l'API
            contact_name = get_contact_name(number)
            # Si aucun nom n'est trouvé, utiliser une valeur par défaut
            name_value = contact_name if contact_name else "default"
            
            reply = f"Pardon, j’étais en tournée et je n’avais pas vu votre message. Il faut effectuer la demande via : https://{name_value}.{SECOND_MESSAGE_LINK}\n merci"
            send_single_message(number, reply, device_id)
            mark_message_processed(number, msg_id)
            archive_number(number)
            redis_conn.delete(conv_key)
            log(f"✅ [{msg_id_short}] Réponse envoyée et conversation archivée.")
        else:
            log(f"🗃️ [{msg_id_short}] Conversation déjà traitée, ignoré.")
            return

        log(f"🏁 [{msg_id_short}] Fin du traitement de ce message")

    except Exception as e:
        log(f"💥 [{msg_id_short}] Erreur interne : {e}")
