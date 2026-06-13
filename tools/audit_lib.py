# tools/audit_lib.py
"""Append-only audit trail writes for governance state transitions."""
from psycopg.types.json import Jsonb


def write_trail(conn, actor_person_id, action, entity_type, entity_id,
                before, after, reason=None):
    conn.execute(
        "INSERT INTO doc_mgmt.audit_trail_entry (actor_person_id, action,"
        " entity_type, entity_id, before_state, after_state, reason)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (actor_person_id, action, entity_type, str(entity_id),
         Jsonb(before) if before is not None else None,
         Jsonb(after) if after is not None else None, reason))
