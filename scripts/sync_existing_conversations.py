#!/usr/bin/env python3
"""
Script to sync existing events data into rasa_conversations table

This script:
1. Reads all unique sender_ids from events table
2. Creates/updates records in rasa_conversations
3. Sets proper timestamps based on first/last event
4. Links to customer_id if available

Run this after applying the trigger SQL migration to backfill existing data.
"""
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from api.database.connection import SessionLocal


def get_sender_stats_from_events(db) -> List[Dict]:
    """
    Get statistics for each sender_id from events table

    Returns:
        List of dicts with sender_id, first_event, last_event, event_count
    """
    query = text("""
        SELECT
            sender_id,
            MIN(timestamp) as first_event,
            MAX(timestamp) as last_event,
            COUNT(*) as event_count,
            COUNT(CASE WHEN type_name = 'user' THEN 1 END) as user_messages
        FROM events
        GROUP BY sender_id
        ORDER BY first_event DESC
    """)

    result = db.execute(query).fetchall()

    return [
        {
            'sender_id': row[0],
            'first_event': row[1],
            'last_event': row[2],
            'event_count': row[3],
            'user_messages': row[4]
        }
        for row in result
    ]


def get_customer_id_for_sender(db, sender_id: str) -> Optional[int]:
    """
    Try to find customer_id for sender_id

    Args:
        db: Database session
        sender_id: Sender ID to look up

    Returns:
        customer_id if found, None otherwise
    """
    # Try to match by phone number only
    # Telegram IDs are numeric, so we only check if sender_id matches phone
    query = text("""
        SELECT id
        FROM customers
        WHERE phone = :sender_id
        LIMIT 1
    """)

    result = db.execute(query, {'sender_id': sender_id}).fetchone()
    return result[0] if result else None


def sync_conversation(db, sender_data: Dict) -> bool:
    """
    Sync a single conversation to rasa_conversations

    Args:
        db: Database session
        sender_data: Dict with sender statistics

    Returns:
        True if successful, False otherwise
    """
    sender_id = sender_data['sender_id']
    created_at = datetime.fromtimestamp(sender_data['first_event'])
    updated_at = datetime.fromtimestamp(sender_data['last_event'])

    # Try to find customer_id
    customer_id = get_customer_id_for_sender(db, sender_id)

    # Check if conversation already exists
    check_query = text("""
        SELECT COUNT(*) FROM rasa_conversations WHERE sender_id = :sender_id
    """)
    exists = db.execute(check_query, {'sender_id': sender_id}).fetchone()[0] > 0

    if exists:
        # Update existing
        update_query = text("""
            UPDATE rasa_conversations
            SET
                customer_id = :customer_id,
                created_at = LEAST(created_at, :created_at),
                updated_at = GREATEST(updated_at, :updated_at),
                active = true
            WHERE sender_id = :sender_id
        """)

        db.execute(update_query, {
            'sender_id': sender_id,
            'customer_id': customer_id,
            'created_at': created_at,
            'updated_at': updated_at
        })

        return True
    else:
        # Insert new
        insert_query = text("""
            INSERT INTO rasa_conversations (
                sender_id, customer_id, events, created_at, updated_at, active
            )
            VALUES (
                :sender_id, :customer_id, '[]', :created_at, :updated_at, true
            )
        """)

        db.execute(insert_query, {
            'sender_id': sender_id,
            'customer_id': customer_id,
            'created_at': created_at,
            'updated_at': updated_at
        })

        return True


def main():
    """Main execution function"""
    print("🔄 Starting rasa_conversations sync from events table...")
    print()

    db = SessionLocal()

    try:
        # Get all sender stats from events
        print("📊 Analyzing events table...")
        sender_stats = get_sender_stats_from_events(db)

        if not sender_stats:
            print("⚠️  No events found in database. Nothing to sync.")
            return

        print(f"✅ Found {len(sender_stats)} unique senders in events table")
        print()

        # Display summary
        print("📋 Sender Summary:")
        print(f"{'Sender ID':<20} {'Events':<10} {'User Msgs':<12} {'First Event':<20} {'Last Event':<20}")
        print("-" * 90)

        for stats in sender_stats:
            first = datetime.fromtimestamp(stats['first_event']).strftime('%Y-%m-%d %H:%M:%S')
            last = datetime.fromtimestamp(stats['last_event']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{stats['sender_id']:<20} {stats['event_count']:<10} {stats['user_messages']:<12} {first:<20} {last:<20}")

        print()
        print(f"🔄 Syncing {len(sender_stats)} conversations...")

        # Sync each conversation
        synced_count = 0
        updated_count = 0

        for stats in sender_stats:
            # Check if exists before sync
            check_query = text("""
                SELECT COUNT(*) FROM rasa_conversations WHERE sender_id = :sender_id
            """)
            existed = db.execute(check_query, {'sender_id': stats['sender_id']}).fetchone()[0] > 0

            if sync_conversation(db, stats):
                if existed:
                    updated_count += 1
                else:
                    synced_count += 1

        db.commit()

        print()
        print("✅ Sync completed successfully!")
        print(f"   📝 Created: {synced_count} new conversations")
        print(f"   🔄 Updated: {updated_count} existing conversations")
        print()

        # Display final state
        final_count_query = text("SELECT COUNT(*) FROM rasa_conversations")
        total_conversations = db.execute(final_count_query).fetchone()[0]

        print(f"📊 Total conversations in database: {total_conversations}")
        print()
        print("💡 Tip: Future events will be automatically synced via database trigger")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during sync: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
