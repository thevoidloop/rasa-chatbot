#!/usr/bin/env python3
"""
Script to generate diverse test conversations for populating the dashboard

This creates realistic conversations with multiple intents to test:
- Dashboard metrics
- Intent distribution
- Confidence scores
- Conversation flows
"""
import requests
import time
import random
from datetime import datetime

# RASA API endpoint
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

# Test conversations with different intents
CONVERSATIONS = [
    {
        "sender": "user_001",
        "messages": [
            "hola",
            "quiero ver el catálogo",
            "dame 5 camisas",
            "cómo son los envíos?"
        ]
    },
    {
        "sender": "user_002",
        "messages": [
            "buenos días",
            "cuáles son las formas de pago?",
            "gracias, adiós"
        ]
    },
    {
        "sender": "user_003",
        "messages": [
            "hola",
            "muéstrame los productos",
            "quiero 2 jeans",
            "info de envío",
            "ok gracias"
        ]
    },
    {
        "sender": "user_004",
        "messages": [
            "buenas tardes",
            "catálogo por favor",
            "agregar 3 blusas al carrito",
            "formas de pago?",
            "perfecto, gracias"
        ]
    },
    {
        "sender": "user_005",
        "messages": [
            "hola qué tal",
            "ver productos",
            "dame 1 vestido",
            "cómo pago?",
            "cuánto cuesta el envío?",
            "ok, hasta luego"
        ]
    },
    {
        "sender": "user_006",
        "messages": [
            "hola",
            "necesito ver la ropa disponible",
            "quiero 6 pantalones",
            "info de envío por favor"
        ]
    },
    {
        "sender": "user_007",
        "messages": [
            "buenas",
            "catálogo",
            "información de pagos",
            "gracias"
        ]
    },
    {
        "sender": "user_008",
        "messages": [
            "hola!",
            "quiero comprar ropa",
            "agrégame 4 camisas",
            "cómo hago el pago?",
            "perfecto, adiós"
        ]
    },
    {
        "sender": "user_009",
        "messages": [
            "buenas tardes",
            "mostrar productos",
            "2 jeans por favor",
            "costos de envío?",
            "ok, gracias"
        ]
    },
    {
        "sender": "user_010",
        "messages": [
            "hola",
            "ver catálogo completo",
            "dame 12 camisas",  # Precio mayorista
            "info de pagos",
            "hasta pronto"
        ]
    }
]


def send_message(sender_id: str, message: str) -> dict:
    """
    Send a message to RASA and return the response

    Args:
        sender_id: Unique identifier for the conversation
        message: Text message to send

    Returns:
        API response
    """
    try:
        response = requests.post(
            RASA_URL,
            json={"sender": sender_id, "message": message},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"   ❌ Error sending message: {e}")
        return []


def run_conversation(conversation: dict, delay: float = 1.5):
    """
    Run a complete conversation with RASA

    Args:
        conversation: Dict with sender and messages
        delay: Delay between messages in seconds
    """
    sender = conversation["sender"]
    messages = conversation["messages"]

    print(f"\n🗣️  Starting conversation for {sender}")
    print(f"   📝 {len(messages)} messages to send")

    for i, message in enumerate(messages, 1):
        print(f"   [{i}/{len(messages)}] User: {message}")

        responses = send_message(sender, message)

        if responses:
            for resp in responses:
                text = resp.get("text", "")
                # Truncate long responses
                if len(text) > 100:
                    text = text[:97] + "..."
                print(f"   ↳ Bot: {text}")

        # Wait between messages to simulate real conversation
        if i < len(messages):
            time.sleep(delay)

    print(f"   ✅ Conversation completed for {sender}")


def main():
    """Main execution"""
    print("=" * 70)
    print("🤖 RASA Test Conversation Generator")
    print("=" * 70)
    print(f"\n📊 Generating {len(CONVERSATIONS)} test conversations")
    print(f"🎯 Target intents: saludar, consultar_catalogo, agregar_al_carrito,")
    print(f"                  consultar_envios, consultar_pagos, despedir")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    success_count = 0
    error_count = 0

    for i, conversation in enumerate(CONVERSATIONS, 1):
        print(f"\n{'─' * 70}")
        print(f"Conversation {i}/{len(CONVERSATIONS)}")

        try:
            run_conversation(conversation, delay=1.0)
            success_count += 1
        except Exception as e:
            print(f"   ❌ Error in conversation: {e}")
            error_count += 1

        # Small delay between conversations
        if i < len(CONVERSATIONS):
            time.sleep(0.5)

    print(f"\n{'=' * 70}")
    print("📈 Summary")
    print(f"{'=' * 70}")
    print(f"✅ Successful conversations: {success_count}")
    print(f"❌ Failed conversations: {error_count}")
    print(f"📊 Total messages sent: {sum(len(c['messages']) for c in CONVERSATIONS)}")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("💡 Next steps:")
    print("   1. Check dashboard at http://localhost:8501")
    print("   2. Verify intent distribution")
    print("   3. Check conversation metrics")
    print()


if __name__ == "__main__":
    main()
