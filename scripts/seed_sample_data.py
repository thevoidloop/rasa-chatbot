#!/usr/bin/env python3
"""
Script to seed sample data for testing dashboard
"""
import sys
import os
from datetime import datetime, timedelta
import random
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.database.connection import SessionLocal
from sqlalchemy import text


def seed_rasa_conversations():
    """Seed rasa_conversations table with sample data"""
    db = SessionLocal()

    try:
        print("🌱 Seeding rasa_conversations...")

        # Generate sample conversations for the last 30 days
        base_date = datetime.utcnow()

        sample_data = []
        for i in range(100):
            days_ago = random.randint(0, 30)
            timestamp = base_date - timedelta(days=days_ago, hours=random.randint(0, 23))

            sample_data.append({
                'sender_id': f'user_{random.randint(1, 50)}',
                'timestamp': timestamp,
                'message_count': random.randint(1, 20),
                'status': random.choice(['resolved', 'pending', 'escalated']),
                'needs_review': random.choice([True, False])
            })

        # Insert data
        for data in sample_data:
            db.execute(text("""
                INSERT INTO rasa_conversations (sender_id, timestamp, message_count, status, needs_review)
                VALUES (:sender_id, :timestamp, :message_count, :status, :needs_review)
                ON CONFLICT DO NOTHING
            """), data)

        db.commit()
        print(f"✅ Inserted {len(sample_data)} conversations")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding rasa_conversations: {e}")

    finally:
        db.close()


def seed_events():
    """Seed events table with sample intents and entities"""
    db = SessionLocal()

    try:
        print("🌱 Seeding events table...")

        intents = [
            'saludar', 'despedir', 'consultar_catalogo',
            'agregar_al_carrito', 'consultar_envios', 'consultar_pagos',
            'consultar_precios', 'consultar_stock', 'ayuda'
        ]

        entities_examples = [
            {'producto': 'camisa'},
            {'producto': 'pantalon'},
            {'cantidad': '3'},
            {'color': 'azul'}
        ]

        base_date = datetime.utcnow()

        sample_events = []
        for i in range(200):
            days_ago = random.randint(0, 30)
            timestamp = base_date - timedelta(days=days_ago, hours=random.randint(0, 23))

            intent = random.choice(intents)
            confidence = random.uniform(0.5, 0.99)

            event_data = {
                'parse_data': {
                    'intent': {
                        'name': intent,
                        'confidence': confidence
                    },
                    'intent_ranking': [{
                        'name': intent,
                        'confidence': confidence
                    }],
                    'entities': random.choice([[], entities_examples[:random.randint(1, 2)]])
                }
            }

            sample_events.append({
                'sender_id': f'user_{random.randint(1, 50)}',
                'type_name': 'user',
                'timestamp': timestamp,
                'intent_name': intent,
                'action_name': None,
                'data': json.dumps(event_data)
            })

        # Insert events
        for event in sample_events:
            db.execute(text("""
                INSERT INTO events (sender_id, type_name, timestamp, intent_name, action_name, data)
                VALUES (:sender_id, :type_name, :timestamp, :intent_name, :action_name, CAST(:data AS jsonb))
            """), event)

        db.commit()
        print(f"✅ Inserted {len(sample_events)} events")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding events: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def seed_deployed_models():
    """Seed deployed_models table"""
    db = SessionLocal()

    try:
        print("🌱 Seeding deployed_models...")

        model_data = {
            'model_name': '20250107-initial-model',
            'model_path': '/app/models/20250107-initial-model.tar.gz',
            'trained_at': datetime.utcnow() - timedelta(days=5),
            'deployed_at': datetime.utcnow() - timedelta(days=5),
            'deployed_by': 1,  # admin user
            'accuracy': 0.87,
            'f1_score': 0.85,
            'is_active': True,
            'training_config': json.dumps({
                'pipeline': 'supervised',
                'epochs': 100
            })
        }

        db.execute(text("""
            INSERT INTO deployed_models
            (model_name, model_path, trained_at, deployed_at, deployed_by, accuracy, f1_score, is_active, training_config)
            VALUES
            (:model_name, :model_path, :trained_at, :deployed_at, :deployed_by, :accuracy, :f1_score, :is_active, CAST(:training_config AS jsonb))
            ON CONFLICT DO NOTHING
        """), model_data)

        db.commit()
        print("✅ Inserted deployed model")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding deployed_models: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Starting data seeding...")
    print()

    seed_rasa_conversations()
    seed_events()
    seed_deployed_models()

    print()
    print("✅ Data seeding completed!")
    print()
    print("📊 You can now view the dashboard with sample data")
