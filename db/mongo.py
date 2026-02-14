"""
============================================
DB/MONGO.PY — Connexion MongoDB avec pooling
============================================
"""
import logging
import threading
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from django.conf import settings

logger = logging.getLogger(__name__)


class MongoDBPool:
    """Singleton — connexion poolée par store."""
    _instance = None
    _lock = threading.Lock()
    _clients = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_client(self, store_name: str) -> MongoClient:
        if store_name not in self._clients:
            with self._lock:
                if store_name not in self._clients:
                    config = settings.MONGODB_CONFIG[store_name]
                    try:
                        client = MongoClient(
                            config['uri'],
                            maxPoolSize=20,
                            minPoolSize=2,
                            maxIdleTimeMS=30000,
                            serverSelectionTimeoutMS=5000,
                            connectTimeoutMS=10000,
                            socketTimeoutMS=20000,
                            retryWrites=True,
                        )
                        client.admin.command('ping')
                        self._clients[store_name] = client
                        logger.info(f"MongoDB connecté : {store_name}")
                    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                        logger.error(f"MongoDB erreur {store_name}: {e}")
                        raise
        return self._clients[store_name]

    def get_collection(self, store_name: str):
        client = self.get_client(store_name)
        cfg = settings.MONGODB_CONFIG[store_name]
        return client[cfg['db']][cfg['collection']]


# Instance globale
_pool = MongoDBPool()


def get_tunisianet():
    return _pool.get_collection('tunisianet')

def get_mytek():
    return _pool.get_collection('mytek')

def get_spacenet():
    return _pool.get_collection('spacenet')

def get_comparatif():
    return _pool.get_collection('comparatif')

def get_all_stores():
    """Retourne [(fonction_collection, nom_store), ...]"""
    return [
        (get_tunisianet, 'Tunisianet'),
        (get_mytek, 'Mytek'),
        (get_spacenet, 'Spacenet'),
    ]
