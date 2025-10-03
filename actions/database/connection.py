import os
import psycopg2
import psycopg2.extras
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Clase para manejar la conexión a PostgreSQL"""

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'rasa_chatbot'),
            'user': os.getenv('DB_USER', 'rasa_user'),
            'password': os.getenv('DB_PASSWORD', 'rasa_password_2024')
        }

    def get_connection(self):
        """Obtiene una conexión a la base de datos"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            return None

    def execute_query(self, query: str, params: tuple = None, fetch: bool = False):
        """Ejecuta una consulta en la base de datos"""
        conn = self.get_connection()
        if not conn:
            return None

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    result = cur.fetchall()
                    conn.commit()
                    return result
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error ejecutando consulta: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()


# Instancia global de conexión a BD
db = DatabaseConnection()
