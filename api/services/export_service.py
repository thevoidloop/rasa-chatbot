"""
Export Service

Handles conversion of approved annotations to RASA NLU format (YAML).
Provides validation and preview capabilities before exporting.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
import yaml
import re

from api.schemas.db_models import Annotation


# ============================================
# Helper Functions
# ============================================

def _format_entity_in_text(text: str, entities: List[Dict[str, Any]]) -> str:
    """
    Format text with entities in RASA markdown format: [entity_text](entity_type)

    Args:
        text: Original message text
        entities: List of entity dicts with keys: entity, value, start, end

    Returns:
        Formatted text with entity annotations

    Example:
        Input: "quiero 2 camisas", entities=[{entity: "cantidad", value: "2", start: 7, end: 8}, ...]
        Output: "quiero [2](cantidad) [camisas](producto)"
    """
    if not entities:
        return text

    # Sort entities by start position (reverse order for replacement)
    sorted_entities = sorted(entities, key=lambda e: e['start'], reverse=True)

    result = text
    for entity in sorted_entities:
        start = entity['start']
        end = entity['end']
        entity_type = entity['entity']

        # Extract entity text from original
        entity_text = text[start:end]

        # Replace with markdown format
        markdown_entity = f"[{entity_text}]({entity_type})"
        result = result[:start] + markdown_entity + result[end:]

    return result


def _validate_intent_exists(intent: str, existing_intents: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate if intent exists in domain or NLU data.

    Args:
        intent: Intent name to validate
        existing_intents: List of known intents

    Returns:
        Tuple of (is_valid, warning_message)
    """
    if intent in existing_intents:
        return True, None
    else:
        return False, f"Intent '{intent}' not found in domain.yml. This will create a new intent."


def _validate_entities(entities: List[Dict[str, Any]], existing_entities: List[str]) -> List[str]:
    """
    Validate entities and return list of warnings.

    Args:
        entities: List of entity dicts
        existing_entities: List of known entity types

    Returns:
        List of warning messages
    """
    warnings = []

    for entity in entities:
        entity_type = entity.get('entity')
        if entity_type and entity_type not in existing_entities:
            warnings.append(f"Entity '{entity_type}' not found in domain.yml")

    return warnings


# ============================================
# Main Service Functions
# ============================================

def get_approved_annotations(
    db: Session,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    intent_filter: Optional[str] = None
) -> List[Annotation]:
    """
    Get approved annotations ready for export.

    Args:
        db: Database session
        from_date: Optional start date filter
        to_date: Optional end date filter
        intent_filter: Optional filter by corrected intent

    Returns:
        List of approved annotations
    """
    query = db.query(Annotation).filter(Annotation.status == 'approved')

    # Apply date filters
    if from_date:
        query = query.filter(Annotation.approved_at >= from_date)

    if to_date:
        # Add one day to include the entire end date
        query = query.filter(Annotation.approved_at < to_date)

    # Apply intent filter
    if intent_filter:
        query = query.filter(Annotation.corrected_intent == intent_filter)

    # Order by intent and then by date
    query = query.order_by(Annotation.corrected_intent, Annotation.approved_at)

    return query.all()


def convert_annotations_to_nlu_dict(annotations: List[Annotation]) -> Dict[str, List[str]]:
    """
    Convert annotations to NLU format dictionary grouped by intent.

    Args:
        annotations: List of Annotation objects

    Returns:
        Dictionary with intent names as keys and lists of formatted examples as values

    Example:
        {
            "consultar_catalogo": [
                "quiero ver productos",
                "muéstrame el [catálogo](producto)"
            ],
            "agregar_al_carrito": [
                "añadir [2](cantidad) [camisas](producto)"
            ]
        }
    """
    nlu_dict = {}

    for annotation in annotations:
        intent = annotation.corrected_intent

        if not intent:
            continue  # Skip if no corrected intent

        # Initialize intent list if not exists
        if intent not in nlu_dict:
            nlu_dict[intent] = []

        # Format example with entities
        formatted_example = _format_entity_in_text(
            annotation.message_text,
            annotation.corrected_entities or []
        )

        # Add to list (avoid duplicates)
        if formatted_example not in nlu_dict[intent]:
            nlu_dict[intent].append(formatted_example)

    return nlu_dict


def convert_to_rasa_nlu_yaml(nlu_dict: Dict[str, List[str]]) -> str:
    """
    Convert NLU dictionary to RASA 3.x YAML format.

    Args:
        nlu_dict: Dictionary with intents and examples

    Returns:
        YAML string in RASA format
    """
    # Build NLU data structure
    nlu_data = []

    for intent, examples in sorted(nlu_dict.items()):
        # Format examples with leading dash and proper indentation
        examples_text = "\n".join([f"    - {example}" for example in examples])

        nlu_data.append({
            'intent': intent,
            'examples': examples_text  # Will be formatted as literal block
        })

    # Create final structure
    output = {
        'version': '3.1',
        'nlu': nlu_data
    }

    # Convert to YAML with proper formatting
    # We need custom formatting for the examples block
    yaml_str = "version: \"3.1\"\n\nnlu:\n"

    for item in nlu_data:
        yaml_str += f"- intent: {item['intent']}\n"
        yaml_str += f"  examples: |\n"
        yaml_str += f"{item['examples']}\n\n"

    return yaml_str


def validate_nlu_yaml(yaml_content: str) -> Tuple[bool, List[str], List[str]]:
    """
    Validate RASA NLU YAML format.

    Args:
        yaml_content: YAML string to validate

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    try:
        # Parse YAML
        data = yaml.safe_load(yaml_content)

        # Check version
        if 'version' not in data:
            errors.append("Missing 'version' field")

        # Check nlu section
        if 'nlu' not in data:
            errors.append("Missing 'nlu' section")
        elif not isinstance(data['nlu'], list):
            errors.append("'nlu' section must be a list")
        else:
            # Validate each intent
            seen_intents = set()
            for idx, item in enumerate(data['nlu']):
                if not isinstance(item, dict):
                    errors.append(f"NLU item {idx} must be a dictionary")
                    continue

                # Check required fields
                if 'intent' not in item:
                    errors.append(f"NLU item {idx} missing 'intent' field")
                elif 'examples' not in item:
                    errors.append(f"Intent '{item['intent']}' missing 'examples' field")
                else:
                    intent_name = item['intent']

                    # Check for duplicates
                    if intent_name in seen_intents:
                        warnings.append(f"Duplicate intent '{intent_name}' found")
                    seen_intents.add(intent_name)

                    # Validate examples format
                    examples = item['examples']
                    if not isinstance(examples, str):
                        errors.append(f"Examples for '{intent_name}' must be a string")
                    elif not examples.strip():
                        warnings.append(f"Intent '{intent_name}' has no examples")

        is_valid = len(errors) == 0

    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error: {str(e)}")
        is_valid = False

    return is_valid, errors, warnings


def get_existing_intents_from_db(db: Session) -> List[str]:
    """
    Get list of unique intents from events table (RASA data).

    Args:
        db: Database session

    Returns:
        List of unique intent names
    """
    query = text("""
        SELECT DISTINCT data::jsonb->'parse_data'->'intent'->>'name' as intent_name
        FROM events
        WHERE type_name = 'user'
          AND data::jsonb->'parse_data'->'intent'->>'name' IS NOT NULL
        ORDER BY intent_name
    """)

    result = db.execute(query)
    intents = [row[0] for row in result if row[0]]

    return intents


def get_existing_entities_from_db(db: Session) -> List[str]:
    """
    Get list of unique entity types from events table (RASA data).

    Args:
        db: Database session

    Returns:
        List of unique entity type names
    """
    query = text("""
        SELECT DISTINCT jsonb_array_elements(data::jsonb->'parse_data'->'entities')->>'entity' as entity_type
        FROM events
        WHERE type_name = 'user'
          AND jsonb_array_length(data::jsonb->'parse_data'->'entities') > 0
        ORDER BY entity_type
    """)

    result = db.execute(query)
    entities = [row[0] for row in result if row[0]]

    return entities


def get_nlu_export_stats(nlu_dict: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Calculate statistics for NLU export.

    Args:
        nlu_dict: Dictionary with intents and examples

    Returns:
        Dictionary with statistics
    """
    total_intents = len(nlu_dict)
    total_examples = sum(len(examples) for examples in nlu_dict.values())

    # Calculate entity usage
    entity_count = {}
    for examples in nlu_dict.values():
        for example in examples:
            # Find all entities in format [text](entity_type)
            entities = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', example)
            for _, entity_type in entities:
                entity_count[entity_type] = entity_count.get(entity_type, 0) + 1

    return {
        'total_intents': total_intents,
        'total_examples': total_examples,
        'total_entities_used': len(entity_count),
        'entity_usage': entity_count,
        'avg_examples_per_intent': round(total_examples / total_intents, 2) if total_intents > 0 else 0
    }


def validate_annotations_export(
    db: Session,
    nlu_dict: Dict[str, List[str]]
) -> Tuple[List[str], List[str]]:
    """
    Validate annotations against existing RASA data.

    Args:
        db: Database session
        nlu_dict: Dictionary with intents and examples

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    # Get existing intents and entities from database
    existing_intents = get_existing_intents_from_db(db)
    existing_entities = get_existing_entities_from_db(db)

    # Validate each intent
    for intent, examples in nlu_dict.items():
        # Check if intent exists
        is_valid, warning = _validate_intent_exists(intent, existing_intents)
        if warning:
            warnings.append(warning)

        # Validate entities in examples
        for example in examples:
            # Extract entities from markdown format
            entities_in_example = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', example)
            for _, entity_type in entities_in_example:
                if entity_type not in existing_entities:
                    warning_msg = f"Entity '{entity_type}' in intent '{intent}' not found in existing data"
                    if warning_msg not in warnings:
                        warnings.append(warning_msg)

    return errors, warnings
