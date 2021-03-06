import logging
import base64
from log import *
from server_registry import *
from server_client import *
import json
from cc_utils import *
from crypto_utils import *
from M2Crypto import X509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import dh


class ServerActions:
    def __init__(self):

        self.messageTypes = {
            'all': self.processAll,
            'list': self.processList,
            'new': self.processNew,
            'send': self.processSend,
            'recv': self.processRecv,
            'create': self.processCreate,
            'receipt': self.processReceipt,
            'status': self.processStatus,
            'userdetails': self.getUserDetails
            #'connection': self.connection
        }

        self.registry = ServerRegistry()
        self.shared_secret = ""
        self.private_session_key = ""

    def handleRequest(self, s, request, client):
        """Handle a request from a client socket.
        """
        try:
            logging.info("HANDLING message from %s: %r" %
                         (client, repr(request)))

            try:
                req = json.loads(request)
            except:
                logging.exception("Invalid message from client")
                return

            if not isinstance(req, dict):
                log(logging.ERROR, "Invalid message format from client")
                return

            if 'type' not in req:
                log(logging.ERROR, "Message has no TYPE field")
                return

            if req['type'] in self.messageTypes:
                self.messageTypes[req['type']](req, client)
            else:
                log(logging.ERROR, "Invalid message type: " +
                    str(req['type']) + " Should be one of: " + str(self.messageTypes.keys()))
                client.sendResult({"error": "unknown request"})

        except Exception, e:
            logging.exception("Could not handle request")
    """
    def connection(self, data, client):
        #parameters = dh.generate_parameters(generator=2, key_size=512, backend=default_backend())
        pubkey_check_sign = base64.b64decode(data["pubk"])
        pubkey = serialization.load_pem_public_key(base64.b64decode(data["pubk"]), backend=default_backend())
        cert = data["cert"]
        pubkey_signed = base64.b64decode(data["pkey_signed"])
        parameters = serialization.load_pem_parameters(base64.b64decode(data["parameters"]), backend=default_backend())

        if not verify_signature(pubkey_check_sign, pubkey_signed, cert):
            log(logging.ERROR, "Signature not valid")
            client.sendResult({"error": "DH Pubk signature is not valid"})
            return


        private_session_key = parameters.generate_private_key()
        server_pubkey = parameters.generate_private_key().public_key()
        server_pubkey_to_send = base64.b64encode(server_pubkey.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo))
        print(server_pubkey.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo))
        shared_secret = private_session_key.exchange(pubkey)
        print(shared_secret)

        client.sendResult({"pubkey": server_pubkey_to_send})
        """

    def getUserDetails(self, data, client):
        if 'uid' not in data.keys():
            log(logging.ERROR, "No \"uid\" field in \"UserDetails\" message: " +
                json.dumps(data))
            client.sendResult({"error": "wrong message format"})
            return

        uid = int(data["uid"])

        user = self.registry.getUser(uid)
        print(user)
        pubk = user['description']['pubk']
        cert = user['description']['cert']
        pubk_hash = user['description']['pubk_hash']
        pubk_signature = user['description']['pubk_hash_sig']
        client.sendResult({"pubk": pubk, "cert": cert,
                           "pubk_hash": pubk_hash, "pubk_signature": pubk_signature, "checksum": data["checksum"]})

    def processCreate(self, data, client):
        log(logging.DEBUG, "%s" % json.dumps(data))

        if 'uuid' not in data.keys():
            log(logging.ERROR, "No \"uuid\" field in \"create\" message: " +
                json.dumps(data))
            client.sendResult({"error": "wrong message format"})
            return

        if 'cert' not in data.keys():
            log(logging.ERROR, "No \"cert\" field in \"create\" message: " +
                json.dumps(data))
            client.sendResult({"error": "wrong message format"})

        if 'pubk' not in data.keys():
            log(logging.ERROR, "No \"pubk\" field in \"create\" message " +
                json.dumps(data))
            client.sendResult({"error": "wrong message format"})

        if 'pubk_hash' not in data.keys():
            log(logging.ERROR, "No \"pubk_hash\" field in \"create\" message " +
                json.dumps(data))
            client.sendResult({"error": "wrong message format"})

        if 'pubk_hash_sig' not in data.keys():
            log(logging.ERROR, "No \"pubk_hash_sig\" field in \"create\" message " +
                json.dumps(data))
            client.sendResult({"error": "wrong message format"})

        if 'checksum' not in data.keys():
            log(logging.ERROR, "No \"checksum\" field in \"create\" message " +
                json.dumps(data))
            client.sendResult({"error": "wrong message format"})

        pubk_hash = base64.b64decode(data['pubk_hash'])
        pubk_hash_sig = base64.b64decode(data['pubk_hash_sig'])
        uuid = base64.b64decode(data['uuid'])
        pubk = data['pubk']
        cert = data['cert']

        pubk_hash_check = SHA256.new(pubk).hexdigest()

        if not (pubk_hash_check == pubk_hash):
            log(logging.ERROR, "Public key was corrupted")
            client.sendResult({"error": "Pub key was corrupted"})
            return

        if not verify_signature(pubk_hash, pubk_hash_sig, cert):
            log(logging.ERROR, "Signature not valid")
            client.sendResult({"error": "Pubk signature is not valid"})
            return

        if not isinstance(uuid, str):
            log(logging.ERROR, "No valid \"uuid\" field in \"create\" message: " +
                json.dumps(data))
            client.sendResult({"error": "wrong message format"})
            return

        if self.registry.userExists(uuid):
            log(logging.ERROR, "User already exists: " + json.dumps(data))
            client.sendResult({"error": "uuid already exists"})
            return

        me = self.registry.addUser(data)
        client.sendResult({"result": me.id, "checksum": data["checksum"]})

    def processList(self, data, client):
        log(logging.DEBUG, "%s" % json.dumps(data))

        user = 0  # 0 means all users
        userStr = "all users"
        if 'id' in data.keys():
            user = int(data['id'])
            userStr = "user%d" % user

        log(logging.DEBUG, "List %s" % userStr)

        userList = self.registry.getUsers()

        client.sendResult({"result": userList, "checksum": data["checksum"]})

    def processNew(self, data, client):
        log(logging.DEBUG, "%s" % json.dumps(data))

        user = -1
        if 'id' in data.keys():
            user = int(data['id'])

        if user < 0:
            log(logging.ERROR,
                "No valid \"id\" field in \"new\" message: " + json.dumps(data))
            client.sendResult({"error": "wrong message format"})
            return

        client.sendResult(
            {"result": self.registry.userNewMessages(user), "checksum": data["checksum"]})

    def processAll(self, data, client):
        log(logging.DEBUG, "%s" % json.dumps(data))

        user = -1
        if 'id' in data.keys():
            user = int(data['id'])

        if user < 0:
            log(logging.ERROR,
                "No valid \"id\" field in \"new\" message: " + json.dumps(data))
            client.sendResult({"error": "wrong message format"})
            return

        client.sendResult({"result": [self.registry.userAllMessages(
            user), self.registry.userSentMessages(user)], "checksum": data["checksum"]})

    def processSend(self, data, client):
        log(logging.DEBUG, "%s" % json.dumps(data))

        if not set(data.keys()).issuperset(set({'src', 'dst', 'msg', 'copy'})):
            log(logging.ERROR,
                "Badly formated \"send\" message: " + json.dumps(data))
            client.sendResult({"error": "wrong message format"})

        srcId = int(data['src'])
        dstId = int(data['dst'])
        msg = str(data['msg'])
        copy = data['copy']

        if not self.registry.userExists(srcId):
            log(logging.ERROR,
                "Unknown source id for \"send\" message: " + json.dumps(data))
            client.sendResult({"error": "wrong parameters"})
            return

        if not self.registry.userExists(dstId):
            log(logging.ERROR,
                "Unknown destination id for \"send\" message: " + json.dumps(data))
            client.sendResult({"error": "wrong parameters"})
            return

        # Save message and copy

        response = self.registry.sendMessage(srcId, dstId, data, copy)

        client.sendResult({"result": response, "checksum": data["checksum"]})

    def processRecv(self, data, client):
        log(logging.DEBUG, "%s" % json.dumps(data))

        if not set({'id', 'msg'}).issubset(set(data.keys())):
            log(logging.ERROR, "Badly formated \"recv\" message: " +
                json.dumps(data))
            client.sendResult({"error": "wrong message format"})

        fromId = int(data['id'])
        msg = str(data['msg'])

        if not self.registry.userExists(fromId):
            log(logging.ERROR,
                "Unknown source id for \"recv\" message: " + json.dumps(data))
            client.sendResult({"error": "wrong parameters"})
            return

        if not self.registry.messageExists(fromId, msg):
            log(logging.ERROR,
                "Unknown source msg for \"recv\" message: " + json.dumps(data))
            client.sendResult({"error": "wrong parameters"})
            return

        # Read message

        response = self.registry.recvMessage(fromId, msg)

        client.sendResult({"result": response, "checksum": data["checksum"]})

    def processReceipt(self, data, client):
        log(logging.DEBUG, "%s" % json.dumps(data))

        if not set({'id', 'msg', 'receipt'}).issubset(set(data.keys())):
            log(logging.ERROR, "Badly formated \"receipt\" message: " +
                json.dumps(data))
            client.sendResult({"error": "wrong request format"})

        fromId = int(data["id"])
        msg = str(data['msg'])
        receipt = (data['receipt'])

        if not self.registry.messageWasRed(str(fromId), msg):
            log(logging.ERROR, "Unknown, or not yet red, message for \"receipt\" request " + json.dumps(data))
            client.sendResult({"error": "wrong parameters"})
            return

        self.registry.storeReceipt(fromId, msg, receipt)

    def processStatus(self, data, client):
        log(logging.DEBUG, "%s" % json.dumps(data))

        if not set({'id', 'msg'}).issubset(set(data.keys())):
            log(logging.ERROR, "Badly formated \"status\" message: " +
                json.dumps(data))
            client.sendResult({"error": "wrong message format"})

        fromId = int(data['id'])
        msg = str(data["msg"])

        if(not self.registry.copyExists(fromId, msg)):
            log(logging.ERROR,
                "Unknown message for \"status\" request: " + json.dumps(data))
            client.sendResult({"error", "wrong parameters"})
            return

        response = self.registry.getReceipts(fromId, msg)
        client.sendResult({"result": response, "checksum": data["checksum"]})
