import os
import json
from redis import Redis
from logger import log
from celery_worker import celery  # 🔁 Import du Celery app

SERVER = os.getenv("SERVER")
API_KEY = os.getenv("API_KEY")
SECOND_MESSAGE_LINK = os.getenv("SECOND_MESSAGE_LINK")

print(SERVER, API_KEY, SECOND_MESSAGE_LINK)

# 🧪 Fonction helper pour obtenir la liste des endpoints à tester
def get_contact_endpoints_to_test():
    """Retourne une liste de tuples (endpoint, method, params) à tester"""
    return [
        # Format /services/...
        (f"{SERVER}/services/contact.php", "POST", {'key': API_KEY}),
        (f"{SERVER}/services/contacts.php", "POST", {'key': API_KEY}),
        (f"{SERVER}/services/get_contact.php", "POST", {'key': API_KEY}),
        (f"{SERVER}/services/get_contacts.php", "POST", {'key': API_KEY}),
        (f"{SERVER}/services/contact_list.php", "POST", {'key': API_KEY}),
        (f"{SERVER}/services/list_contacts.php", "POST", {'key': API_KEY}),
        # Format /api/...
        (f"{SERVER}/api/contact.php", "POST", {'key': API_KEY}),
        (f"{SERVER}/api/contacts.php", "POST", {'key': API_KEY}),
        (f"{SERVER}/api/get_contacts.php", "POST", {'key': API_KEY}),
        # Format avec action
        (f"{SERVER}/api.php", "POST", {'key': API_KEY, 'action': 'contacts'}),
        (f"{SERVER}/api.php", "POST", {'key': API_KEY, 'action': 'get_contacts'}),
        (f"{SERVER}/api.php", "POST", {'key': API_KEY, 'action': 'list_contacts'}),
        (f"{SERVER}/services/api.php", "POST", {'key': API_KEY, 'action': 'contacts'}),
        # Format GET
        (f"{SERVER}/services/contacts.php", "GET", {'key': API_KEY}),
        (f"{SERVER}/api/contacts.php", "GET", {'key': API_KEY}),
        (f"{SERVER}/api.php?key={API_KEY}&action=contacts", "GET", None),
        # Format dashboard
        (f"{SERVER}/dashboard/api/contacts.php", "POST", {'key': API_KEY}),
        (f"{SERVER}/dashboard/services/contacts.php", "POST", {'key': API_KEY}),
    ]

# 🧪 Fonction de test pour récupérer tous les contacts
# 
# ⚠️ NOTE: Si aucun endpoint ne fonctionne, vérifiez dans votre dashboard noname-sms.com:
#   1. Allez sur https://noname-sms.com/dashboard.php
#   2. Cherchez une section "API" ou "Documentation"
#   3. Vérifiez s'il y a un endpoint spécifique pour récupérer les contacts
#   4. Il est possible que l'API ne permette pas de récupérer les contacts directement
#      Dans ce cas, vous devrez peut-être stocker les contacts localement ou utiliser une autre méthode
#
def test_get_all_contacts():
    """Test pour récupérer tous les contacts et les afficher"""
    import requests
    print(f"\n{'='*60}")
    print("🧪 TEST: Récupération de TOUS les contacts")
    print(f"{'='*60}")
    print(f"SERVER: {SERVER}")
    print(f"API_KEY: {API_KEY[:20]}..." if API_KEY else "API_KEY: None")
    
    endpoints_to_test = get_contact_endpoints_to_test()
    
    for endpoint, method, params in endpoints_to_test:
        try:
            print(f"\n🔍 Test endpoint: {endpoint}")
            print(f"   Méthode: {method}, Params: {params}")
            
            if method == "POST":
                if params:
                    response = requests.post(endpoint, data=params, timeout=10)
                else:
                    response = requests.post(endpoint, timeout=10)
            else:  # GET
                if params:
                    response = requests.get(endpoint, params=params, timeout=10)
                else:
                    response = requests.get(endpoint, timeout=10)
            
            print(f"📡 Status Code: {response.status_code}")
            print(f"📡 URL finale: {response.url}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"\n✅ SUCCÈS! RÉPONSE JSON:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    
                    contacts = data.get("data") or data.get("contacts") or data.get("result") or data
                    print(f"\n📋 CONTACTS EXTRACTÉS:")
                    print(f"Type: {type(contacts)}")
                    
                    if isinstance(contacts, list):
                        print(f"✅ Nombre de contacts: {len(contacts)}")
                        for idx, contact in enumerate(contacts, 1):
                            print(f"\n  Contact #{idx}:")
                            print(json.dumps(contact, indent=4, ensure_ascii=False))
                    elif isinstance(contacts, dict):
                        print(f"✅ Contact unique (dict):")
                        print(json.dumps(contacts, indent=4, ensure_ascii=False))
                    else:
                        print(f"Contenu: {contacts}")
                    
                    print(f"\n{'='*60}\n")
                    print(f"🎉 ENDPOINT TROUVÉ: {endpoint} avec méthode {method}")
                    return data
                except json.JSONDecodeError:
                    print(f"⚠️ Réponse n'est pas du JSON")
                    print(f"Contenu (premiers 500 chars): {response.text[:500]}")
            elif response.status_code == 404:
                print(f"❌ 404 - Endpoint non trouvé")
            else:
                print(f"❌ Erreur HTTP {response.status_code}")
                print(f"Réponse (premiers 500 chars): {response.text[:500]}")
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout - endpoint ne répond pas")
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("❌ Aucun endpoint valide trouvé pour récupérer les contacts")
    print(f"{'='*60}\n")
    return None

def test_get_all_contacts_from_db():
    """Test pour récupérer tous les contacts depuis la base de données MySQL"""
    try:
        import pymysql
        
        # Configuration de la base de données
        db_host = os.getenv("DB_HOST", "localhost")
        db_user = os.getenv("DB_USER", "admin_a")
        db_pass = os.getenv("DB_PASS", "Metadjer12")
        db_name = os.getenv("DB_NAME", "admin_a")
        
        print(f"\n{'='*60}")
        print("🧪 TEST: Récupération de TOUS les contacts depuis la BASE DE DONNÉES")
        print(f"{'='*60}")
        print(f"Host: {db_host}")
        print(f"User: {db_user}")
        print(f"Database: {db_name}")
        
        # Connexion à la base de données
        connection = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        try:
            with connection.cursor() as cursor:
                # Récupérer tous les contacts
                cursor.execute("SELECT name, number, contactsListID, subscribed, ID FROM Contact ORDER BY number")
                all_contacts = cursor.fetchall()
                
                print(f"\n✅ Nombre total de contacts: {len(all_contacts)}")
                print(f"\n📋 TOUS LES CONTACTS:")
                print(f"{'='*60}")
                
                for idx, contact in enumerate(all_contacts, 1):
                    print(f"\n  Contact #{idx}:")
                    print(f"    ID: {contact.get('ID')}")
                    print(f"    Nom: {contact.get('name') or '(sans nom)'}")
                    print(f"    Numéro: {contact.get('number')}")
                    print(f"    Liste ID: {contact.get('contactsListID')}")
                    print(f"    Abonné: {contact.get('subscribed')}")
                
                print(f"\n{'='*60}\n")
                
        finally:
            connection.close()
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

# Décommenter la ligne suivante pour tester au démarrage
# test_get_all_contacts()  # Test API (ne fonctionne probablement pas)
test_get_all_contacts_from_db()  # Test Base de données (devrait fonctionner)

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

def get_contact_name_from_db(number):
    """Récupère le nom du contact depuis la base de données MySQL"""
    try:
        import pymysql
        
        # Configuration de la base de données depuis les variables d'environnement ou valeurs par défaut
        db_host = os.getenv("DB_HOST", "localhost")
        db_user = os.getenv("DB_USER", "admin_a")
        db_pass = os.getenv("DB_PASS", "Metadjer12")
        db_name = os.getenv("DB_NAME", "admin_a")
        
        print(f"\n{'#'*60}")
        print(f"🔍 Connexion à la base de données MySQL")
        print(f"   Host: {db_host}")
        print(f"   User: {db_user}")
        print(f"   Database: {db_name}")
        print(f"   Recherche du numéro: {number}")
        print(f"{'#'*60}\n")
        
        # Connexion à la base de données
        connection = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        try:
            with connection.cursor() as cursor:
                # Rechercher le contact par numéro
                # Normaliser le numéro pour la recherche (enlever espaces, +, etc.)
                normalized_number = str(number).strip().replace("+", "").replace(" ", "").replace("-", "")
                
                # Essayer plusieurs formats de recherche
                queries = [
                    ("SELECT name, number FROM Contact WHERE number = %s LIMIT 1", [number]),
                    ("SELECT name, number FROM Contact WHERE number = %s LIMIT 1", [normalized_number]),
                    ("SELECT name, number FROM Contact WHERE REPLACE(REPLACE(REPLACE(number, '+', ''), ' ', ''), '-', '') = %s LIMIT 1", [normalized_number]),
                    ("SELECT name, number FROM Contact WHERE number LIKE %s LIMIT 1", [f"%{normalized_number}%"]),
                ]
                
                for query, params in queries:
                    cursor.execute(query, params)
                    result = cursor.fetchone()
                    if result:
                        name = result.get('name')
                        contact_number = result.get('number')
                        print(f"✅ Contact trouvé dans la DB:")
                        print(f"   Nom: {name}")
                        print(f"   Numéro: {contact_number}")
                        if name:
                            return name
                
                # Si aucun contact trouvé, afficher tous les contacts pour debug
                print(f"\n📋 Aucun contact trouvé pour {number}. Affichage de TOUS les contacts:")
                cursor.execute("SELECT name, number, contactsListID, subscribed FROM Contact ORDER BY number LIMIT 100")
                all_contacts = cursor.fetchall()
                print(f"   Nombre total de contacts (premiers 100): {len(all_contacts)}")
                for idx, contact in enumerate(all_contacts, 1):
                    print(f"   Contact #{idx}: name='{contact.get('name')}', number='{contact.get('number')}', listID={contact.get('contactsListID')}, subscribed={contact.get('subscribed')}")
                
        finally:
            connection.close()
            
    except Exception as e:
        print(f"❌ Erreur lors de la récupération depuis la DB: {e}")
        import traceback
        traceback.print_exc()
    
    return None

def get_contact_name(number):
    """Récupère le nom du contact depuis la base de données MySQL ou l'API"""
    # D'abord essayer la base de données (plus rapide et fiable)
    name = get_contact_name_from_db(number)
    if name:
        return name
    
    # Si pas trouvé dans la DB, essayer l'API (méthode de fallback)
    import requests
    print(f"\n{'#'*60}")
    print(f"🔍 get_contact_name() appelée pour le numéro: {number}")
    print(f"🔍 SERVER: {SERVER}")
    print(f"🔍 API_KEY: {API_KEY[:20]}..." if API_KEY else "🔍 API_KEY: None")
    print(f"{'#'*60}\n")
    try:
        # Essayer différents endpoints possibles pour récupérer les contacts
        endpoints_to_test = get_contact_endpoints_to_test()
        
        for endpoint, method, base_params in endpoints_to_test:
            try:
                print(f"\n{'='*60}")
                print(f"🔍 Tentative de récupération du contact pour {number} via {endpoint}")
                print(f"{'='*60}")
                log(f"🔍 Tentative de récupération du contact pour {number} via {endpoint}")
                
                # Ajouter le numéro aux paramètres
                if base_params is None:
                    params = {'number': number, 'key': API_KEY}
                else:
                    params = base_params.copy()
                    params['number'] = number
                
                if method == "POST":
                    response = requests.post(endpoint, data=params, timeout=10)
                else:  # GET
                    response = requests.get(endpoint, params=params, timeout=10)
                
                print(f"📡 Status Code: {response.status_code}")
                print(f"📡 URL: {endpoint}")
                print(f"📡 Request Data: key={API_KEY[:10]}..., number={number}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"\n📋 RÉPONSE BRUTE DE L'API:")
                    print(f"{json.dumps(data, indent=2, ensure_ascii=False)}")
                    log(f"📋 Réponse contacts : {data}")
                    
                    # Essayer différents formats de réponse
                    contacts = data.get("data") or data.get("contacts") or data
                    print(f"\n📋 CONTACTS EXTRACTÉS:")
                    print(f"Type: {type(contacts)}")
                    print(f"Contenu: {contacts}")
                    
                    if isinstance(contacts, list):
                        print(f"\n📋 TOUS LES CONTACTS ({len(contacts)} contacts):")
                        for idx, contact in enumerate(contacts, 1):
                            print(f"\n  Contact #{idx}:")
                            print(f"    {json.dumps(contact, indent=4, ensure_ascii=False)}")
                        print(f"\n{'='*60}\n")
                        
                        # Chercher le contact avec le numéro correspondant
                        for contact in contacts:
                            contact_number = str(contact.get("number") or contact.get("mobile") or contact.get("phone") or "").strip()
                            print(f"🔍 Comparaison: contact_number='{contact_number}' vs number='{number}'")
                            if contact_number == str(number).strip():
                                name = contact.get("name") or contact.get("contact_name") or ""
                                if name:
                                    print(f"✅ Nom trouvé pour {number} : {name}")
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
        
        # Si aucun endpoint n'a fonctionné, essayer de récupérer tous les contacts (sans filtre number)
        endpoints_to_test_all = get_contact_endpoints_to_test()
        for endpoint, method, base_params in endpoints_to_test_all:
            try:
                print(f"\n{'='*60}")
                print(f"🔍 Tentative de récupération de TOUS les contacts (sans filtre) via {endpoint}")
                print(f"{'='*60}")
                log(f"🔍 Tentative de récupération de tous les contacts via {endpoint}")
                
                # Ne pas ajouter 'number' pour récupérer tous les contacts
                if base_params is None:
                    params = {'key': API_KEY}
                else:
                    params = base_params.copy()
                
                if method == "POST":
                    response = requests.post(endpoint, data=params, timeout=10)
                else:  # GET
                    response = requests.get(endpoint, params=params, timeout=10)
                
                print(f"📡 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"\n📋 RÉPONSE BRUTE (tous contacts):")
                    print(f"{json.dumps(data, indent=2, ensure_ascii=False)}")
                    
                    contacts = data.get("data") or data.get("contacts") or []
                    print(f"\n📋 CONTACTS EXTRACTÉS (tous):")
                    print(f"Type: {type(contacts)}")
                    print(f"Nombre: {len(contacts) if isinstance(contacts, list) else 'N/A'}")
                    
                    if isinstance(contacts, list):
                        print(f"\n📋 TOUS LES CONTACTS ({len(contacts)} contacts):")
                        for idx, contact in enumerate(contacts, 1):
                            print(f"\n  Contact #{idx}:")
                            print(f"    {json.dumps(contact, indent=4, ensure_ascii=False)}")
                        print(f"\n{'='*60}\n")
                        
                        for contact in contacts:
                            contact_number = str(contact.get("number") or contact.get("mobile") or contact.get("phone") or "").strip()
                            normalized_number = str(number).strip().replace("+", "").replace(" ", "")
                            normalized_contact = contact_number.replace("+", "").replace(" ", "")
                            if normalized_contact == normalized_number or contact_number == str(number).strip():
                                name = contact.get("name") or contact.get("contact_name") or ""
                                if name:
                                    print(f"✅ Nom trouvé pour {number} : {name}")
                                    log(f"✅ Nom trouvé pour {number} : {name}")
                                    return name
            except Exception as e:
                print(f"⚠️ Erreur avec endpoint {endpoint}: {e}")
                continue
        
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
