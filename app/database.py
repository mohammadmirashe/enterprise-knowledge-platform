from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from config import settings


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.sqlite_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def rows(sql: str, args: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as connection:
        return [dict(row) for row in connection.execute(sql, args)]


def one(sql: str, args: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(sql, args).fetchone()
        return dict(row) if row else None


def _ensure_column(connection: sqlite3.Connection, table: str, name: str, column_type: str) -> None:
    existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if name not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")


def init_db() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                full_name TEXT,
                role TEXT,
                unit TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge_domains(
                id INTEGER PRIMARY KEY,
                name TEXT,
                parent_id INTEGER,
                owner_user_id INTEGER,
                review_days INTEGER DEFAULT 180,
                access_level TEXT DEFAULT 'internal',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge_items(
                id INTEGER PRIMARY KEY,
                title TEXT,
                summary TEXT,
                content TEXT,
                structured_data TEXT,
                knowledge_type TEXT,
                domain_id INTEGER,
                unit TEXT,
                project TEXT,
                equipment_tag TEXT,
                tags TEXT,
                sensitivity TEXT,
                owner_user_id INTEGER,
                owner_text TEXT,
                expert_user_id INTEGER,
                reviewer_user_id INTEGER,
                status TEXT DEFAULT 'draft',
                version INTEGER DEFAULT 1,
                quality_score REAL DEFAULT 0,
                completeness_score REAL DEFAULT 0,
                evidence_score REAL DEFAULT 0,
                confidence_score REAL DEFAULT 0,
                effectiveness_score REAL DEFAULT 0,
                review_due_at TEXT,
                created_by INTEGER,
                created_at TEXT,
                updated_at TEXT,
                published_at TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge_versions(
                id INTEGER PRIMARY KEY,
                knowledge_id INTEGER,
                version INTEGER,
                snapshot TEXT,
                change_reason TEXT,
                created_by INTEGER,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS reviews(
                id INTEGER PRIMARY KEY,
                knowledge_id INTEGER,
                reviewer_user_id INTEGER,
                decision TEXT,
                comment TEXT,
                field_comments TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS attachments(
                id INTEGER PRIMARY KEY,
                knowledge_id INTEGER,
                session_id TEXT,
                filename TEXT,
                stored_path TEXT,
                mime_type TEXT,
                category TEXT,
                created_by INTEGER,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge_entities(
                id INTEGER PRIMARY KEY,
                knowledge_id INTEGER,
                entity_type TEXT,
                label TEXT,
                normalized_label TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge_relations(
                id INTEGER PRIMARY KEY,
                knowledge_id INTEGER,
                source_label TEXT,
                relation_type TEXT,
                target_label TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS capture_sessions(
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                mode TEXT,
                status TEXT,
                state TEXT,
                form_data TEXT,
                conversation TEXT,
                missing_fields TEXT,
                completion_score REAL,
                quality_score REAL,
                evidence_score REAL,
                confidence_score REAL,
                question_count INTEGER DEFAULT 0,
                max_questions INTEGER DEFAULT 3,
                knowledge_id INTEGER,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS feedback(
                id INTEGER PRIMARY KEY,
                knowledge_id INTEGER,
                user_id INTEGER,
                feedback_type TEXT,
                comment TEXT,
                applied_context TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge_gaps(
                id INTEGER PRIMARY KEY,
                question TEXT,
                domain_id INTEGER,
                assigned_expert_id INTEGER,
                status TEXT DEFAULT 'open',
                priority TEXT DEFAULT 'medium',
                answer TEXT,
                created_by INTEGER,
                created_at TEXT,
                resolved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS documents(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                stored_path TEXT UNIQUE,
                mime_type TEXT,
                category TEXT,
                tags TEXT,
                status TEXT,
                page_count INTEGER DEFAULT 0,
                quality_score REAL,
                knowledge_id INTEGER,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                action TEXT,
                entity TEXT,
                entity_id TEXT,
                details TEXT,
                created_at TEXT
            );
            """
        )
        # Safe migrations from v0.7 databases.
        for name, col_type in (
            ("completeness_score", "REAL DEFAULT 0"),
            ("evidence_score", "REAL DEFAULT 0"),
            ("confidence_score", "REAL DEFAULT 0"),
        ):
            _ensure_column(connection, "knowledge_items", name, col_type)
        for name, col_type in (
            ("state", "TEXT DEFAULT 'new'"),
            ("quality_score", "REAL DEFAULT 0"),
            ("evidence_score", "REAL DEFAULT 0"),
            ("confidence_score", "REAL DEFAULT 0"),
            ("question_count", "INTEGER DEFAULT 0"),
            ("max_questions", "INTEGER DEFAULT 3"),
        ):
            _ensure_column(connection, "capture_sessions", name, col_type)

        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO users(username,full_name,role,unit,created_at) VALUES(?,?,?,?,?)",
                [
                    ("admin", "مدیر سیستم", "admin", "فناوری اطلاعات", now()),
                    ("km_manager", "مدیر دانش", "knowledge_manager", "مدیریت دانش", now()),
                    ("expert", "کارشناس خبره", "expert", "تعمیرات مکانیک", now()),
                    ("user", "کاربر عادی", "user", "عملیات", now()),
                ],
            )
        if connection.execute("SELECT COUNT(*) FROM knowledge_domains").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO knowledge_domains(name,parent_id,owner_user_id,review_days,access_level,created_at) VALUES(?,?,?,?,?,?)",
                [
                    ("بهره‌برداری", None, 2, 180, "internal", now()),
                    ("نگهداری و تعمیرات", None, 2, 180, "internal", now()),
                    ("تجهیزات دوار", 2, 3, 120, "internal", now()),
                    ("ایمنی و HSE", None, 2, 90, "restricted", now()),
                ],
            )

        # General organizational domains are ensured even when upgrading an existing database.
        for domain_name in (
            "منابع انسانی",
            "مالی و حسابداری",
            "فناوری اطلاعات و نرم‌افزار",
            "مدیریت پروژه",
            "حقوقی و قراردادها",
            "فروش و بازاریابی",
            "زنجیره تأمین و تدارکات",
            "مدیریت و راهبرد",
        ):
            if connection.execute("SELECT 1 FROM knowledge_domains WHERE name=?", (domain_name,)).fetchone() is None:
                connection.execute(
                    "INSERT INTO knowledge_domains(name,parent_id,owner_user_id,review_days,access_level,created_at) VALUES(?,?,?,?,?,?)",
                    (domain_name, None, 2, 180, "internal", now()),
                )


def audit(action: str, entity: str, entity_id: Any = "", details: str = "", actor_id: int = 1) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO audit_log(actor_id,action,entity,entity_id,details,created_at) VALUES(?,?,?,?,?,?)",
            (actor_id, action, entity, str(entity_id), details, now()),
        )


def list_users() -> list[dict[str, Any]]:
    return rows("SELECT * FROM users WHERE active=1 ORDER BY full_name")


def list_domains() -> list[dict[str, Any]]:
    return rows(
        """
        SELECT d.*, p.name parent_name, u.full_name owner_name,
               (SELECT COUNT(*) FROM knowledge_items k WHERE k.domain_id=d.id) item_count
        FROM knowledge_domains d
        LEFT JOIN knowledge_domains p ON p.id=d.parent_id
        LEFT JOIN users u ON u.id=d.owner_user_id
        ORDER BY COALESCE(p.name,''), d.name
        """
    )


def create_domain(data: dict[str, Any]) -> int:
    with connect() as connection:
        domain_id = connection.execute(
            "INSERT INTO knowledge_domains(name,parent_id,owner_user_id,review_days,access_level,created_at) VALUES(?,?,?,?,?,?)",
            (
                data["name"],
                data.get("parent_id"),
                data.get("owner_user_id"),
                data.get("review_days", 180),
                data.get("access_level", "internal"),
                now(),
            ),
        ).lastrowid
    audit("CREATE", "domain", domain_id, data["name"])
    return int(domain_id)


def _sync_graph(connection: sqlite3.Connection, knowledge_id: int, data: dict[str, Any]) -> None:
    """Rebuild a general-purpose graph for any organizational knowledge type."""
    connection.execute("DELETE FROM knowledge_entities WHERE knowledge_id=?", (knowledge_id,))
    connection.execute("DELETE FROM knowledge_relations WHERE knowledge_id=?", (knowledge_id,))

    title = str(data.get("title") or data.get("problem") or f"دانش {knowledge_id}")[:500]
    field_types = (
        ("__knowledge__", "knowledge", title),
        ("knowledge_type", "knowledge_type", data.get("knowledge_type")),
        ("unit", "unit", data.get("unit")),
        ("problem", "topic", data.get("problem")),
        ("initial_hypothesis", "option", data.get("initial_hypothesis")),
        ("root_cause", "rationale", data.get("root_cause")),
        ("action_taken", "method", data.get("action_taken")),
        ("result", "outcome", data.get("result")),
        ("project", "context", data.get("project")),
        ("equipment_tag", "asset", data.get("equipment_tag")),
    )
    labels: dict[str, str] = {}
    values: list[tuple[Any, ...]] = []
    for field, entity_type, value in field_types:
        if value not in (None, "", [], {}):
            label = str(value)[:500]
            labels[field] = label
            values.append((knowledge_id, entity_type, label, label.strip().lower(), now()))
    if values:
        connection.executemany(
            "INSERT INTO knowledge_entities(knowledge_id,entity_type,label,normalized_label,created_at) VALUES(?,?,?,?,?)",
            values,
        )

    relations = (
        ("__knowledge__", "knowledge_type", "HAS_TYPE"),
        ("__knowledge__", "unit", "BELONGS_TO_UNIT"),
        ("__knowledge__", "problem", "COVERS_TOPIC"),
        ("problem", "initial_hypothesis", "CONSIDERS"),
        ("problem", "root_cause", "EXPLAINED_BY"),
        ("__knowledge__", "action_taken", "DESCRIBES"),
        ("action_taken", "result", "PRODUCES"),
        ("__knowledge__", "project", "RELATED_TO"),
        ("equipment_tag", "__knowledge__", "RELATED_ASSET"),
    )
    for source, target, relation in relations:
        if source in labels and target in labels:
            connection.execute(
                "INSERT INTO knowledge_relations(knowledge_id,source_label,relation_type,target_label,created_at) VALUES(?,?,?,?,?)",
                (knowledge_id, labels[source], relation, labels[target], now()),
            )


def create_knowledge(data: dict[str, Any], actor_id: int = 1) -> tuple[int, float]:
    review_days = int(data.get("review_days", 180))
    due = (datetime.now(timezone.utc) + timedelta(days=review_days)).isoformat()
    structured = data.get("structured_data", data)
    quality = float(data.get("quality_score", 0))
    completeness = float(data.get("completeness_score", 0))
    evidence = float(data.get("evidence_score", 0))
    confidence = float(data.get("confidence_score", 0))
    with connect() as connection:
        knowledge_id = connection.execute(
            """
            INSERT INTO knowledge_items(
                title,summary,content,structured_data,knowledge_type,domain_id,unit,project,equipment_tag,tags,
                sensitivity,owner_user_id,owner_text,expert_user_id,reviewer_user_id,status,quality_score,
                completeness_score,evidence_score,confidence_score,review_due_at,created_by,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                data.get("title") or "پیش‌نویس دانش بدون عنوان",
                data.get("summary", ""),
                data.get("content", ""),
                json.dumps(structured, ensure_ascii=False),
                data.get("knowledge_type", "lesson_learned"),
                data.get("domain_id"),
                data.get("unit", ""),
                data.get("project", ""),
                data.get("equipment_tag", ""),
                data.get("tags", ""),
                data.get("sensitivity", "internal"),
                data.get("owner_user_id"),
                data.get("owner_text", ""),
                data.get("expert_user_id"),
                data.get("reviewer_user_id"),
                data.get("status", "draft"),
                quality,
                completeness,
                evidence,
                confidence,
                due,
                actor_id,
                now(),
                now(),
            ),
        ).lastrowid
        connection.execute(
            "INSERT INTO knowledge_versions(knowledge_id,version,snapshot,change_reason,created_by,created_at) VALUES(?,?,?,?,?,?)",
            (knowledge_id, 1, json.dumps(structured, ensure_ascii=False), "نسخه اولیه", actor_id, now()),
        )
        _sync_graph(connection, int(knowledge_id), structured)
    audit("CREATE", "knowledge", knowledge_id, data.get("title", ""), actor_id)
    return int(knowledge_id), quality


def list_knowledge(status: str | None = None) -> list[dict[str, Any]]:
    sql = """
        SELECT k.id,k.title,k.summary,k.knowledge_type,k.unit,k.project,k.equipment_tag,k.tags,k.sensitivity,
               k.status,k.version,k.quality_score,k.completeness_score,k.evidence_score,k.confidence_score,
               k.review_due_at,k.created_at,k.updated_at,d.name domain_name,o.full_name owner_name,k.owner_text,
               e.full_name expert_name,r.full_name reviewer_name
        FROM knowledge_items k
        LEFT JOIN knowledge_domains d ON d.id=k.domain_id
        LEFT JOIN users o ON o.id=k.owner_user_id
        LEFT JOIN users e ON e.id=k.expert_user_id
        LEFT JOIN users r ON r.id=k.reviewer_user_id
    """
    args: tuple[Any, ...] = ()
    if status:
        sql += " WHERE k.status=?"
        args = (status,)
    return rows(sql + " ORDER BY k.updated_at DESC", args)


def get_knowledge(knowledge_id: int) -> dict[str, Any] | None:
    item = one(
        """
        SELECT k.*,d.name domain_name,o.full_name owner_name,e.full_name expert_name,r.full_name reviewer_name
        FROM knowledge_items k
        LEFT JOIN knowledge_domains d ON d.id=k.domain_id
        LEFT JOIN users o ON o.id=k.owner_user_id
        LEFT JOIN users e ON e.id=k.expert_user_id
        LEFT JOIN users r ON r.id=k.reviewer_user_id
        WHERE k.id=?
        """,
        (knowledge_id,),
    )
    if not item:
        return None
    try:
        item["structured_data"] = json.loads(item.get("structured_data") or "{}")
    except json.JSONDecodeError:
        item["structured_data"] = {}
    item["attachments"] = list_attachments(knowledge_id)
    item["reviews"] = rows(
        "SELECT r.*,u.full_name reviewer_name FROM reviews r LEFT JOIN users u ON u.id=r.reviewer_user_id WHERE knowledge_id=? ORDER BY created_at",
        (knowledge_id,),
    )
    item["versions"] = rows(
        "SELECT id,version,change_reason,created_by,created_at FROM knowledge_versions WHERE knowledge_id=? ORDER BY version DESC",
        (knowledge_id,),
    )
    return item


def update_knowledge(
    knowledge_id: int, data: dict[str, Any], actor_id: int = 1, reason: str = "ویرایش"
) -> dict[str, Any] | None:
    old = get_knowledge(knowledge_id)
    if not old:
        return None
    structured = {**old["structured_data"], **data.get("structured_data", data)}
    version = int(old["version"]) + 1
    with connect() as connection:
        connection.execute(
            """
            UPDATE knowledge_items SET title=?,summary=?,content=?,structured_data=?,knowledge_type=?,domain_id=?,unit=?,
                project=?,equipment_tag=?,tags=?,sensitivity=?,owner_user_id=?,owner_text=?,expert_user_id=?,reviewer_user_id=?,
                quality_score=?,completeness_score=?,evidence_score=?,confidence_score=?,version=?,updated_at=? WHERE id=?
            """,
            (
                data.get("title", structured.get("title", old["title"])),
                data.get("summary", structured.get("summary", old["summary"])),
                data.get("content", old["content"]),
                json.dumps(structured, ensure_ascii=False),
                data.get("knowledge_type", old["knowledge_type"]),
                data.get("domain_id", old["domain_id"]),
                data.get("unit", structured.get("unit", old["unit"])),
                data.get("project", structured.get("project", old["project"])),
                data.get("equipment_tag", structured.get("equipment_tag", old["equipment_tag"])),
                data.get("tags", structured.get("tags", old["tags"])),
                data.get("sensitivity", structured.get("sensitivity", old["sensitivity"])),
                data.get("owner_user_id", old["owner_user_id"]),
                data.get("owner_text", structured.get("owner_text", old["owner_text"])),
                data.get("expert_user_id", old["expert_user_id"]),
                data.get("reviewer_user_id", old["reviewer_user_id"]),
                data.get("quality_score", old["quality_score"]),
                data.get("completeness_score", old.get("completeness_score", 0)),
                data.get("evidence_score", old.get("evidence_score", 0)),
                data.get("confidence_score", old.get("confidence_score", 0)),
                version,
                now(),
                knowledge_id,
            ),
        )
        connection.execute(
            "INSERT INTO knowledge_versions(knowledge_id,version,snapshot,change_reason,created_by,created_at) VALUES(?,?,?,?,?,?)",
            (knowledge_id, version, json.dumps(structured, ensure_ascii=False), reason, actor_id, now()),
        )
        _sync_graph(connection, knowledge_id, structured)
    audit("UPDATE", "knowledge", knowledge_id, reason, actor_id)
    return get_knowledge(knowledge_id)


def submit_knowledge(knowledge_id: int, actor_id: int = 1) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE knowledge_items SET status='pending_review',updated_at=? WHERE id=?", (now(), knowledge_id)
        )
    audit("SUBMIT", "knowledge", knowledge_id, "ارسال برای بازبینی", actor_id)


def review_knowledge(
    knowledge_id: int,
    decision: str,
    comment: str,
    reviewer: int = 2,
    field_comments: dict[str, Any] | None = None,
) -> str:
    status = {"approve": "published", "reject": "rejected", "changes": "needs_changes"}.get(decision, "pending_review")
    with connect() as connection:
        connection.execute(
            "INSERT INTO reviews(knowledge_id,reviewer_user_id,decision,comment,field_comments,created_at) VALUES(?,?,?,?,?,?)",
            (knowledge_id, reviewer, decision, comment, json.dumps(field_comments or {}, ensure_ascii=False), now()),
        )
        connection.execute(
            "UPDATE knowledge_items SET status=?,reviewer_user_id=?,published_at=CASE WHEN ?='published' THEN ? ELSE published_at END,updated_at=? WHERE id=?",
            (status, reviewer, status, now(), now(), knowledge_id),
        )
        if status == "published":
            row = connection.execute(
                "SELECT structured_data,title,knowledge_type,unit,project,equipment_tag FROM knowledge_items WHERE id=?",
                (knowledge_id,),
            ).fetchone()
            if row:
                try:
                    structured = json.loads(row[0] or "{}")
                except json.JSONDecodeError:
                    structured = {}
                structured.setdefault("title", row[1])
                structured.setdefault("knowledge_type", row[2])
                structured.setdefault("unit", row[3])
                structured.setdefault("project", row[4])
                structured.setdefault("equipment_tag", row[5])
                _sync_graph(connection, knowledge_id, structured)
    audit("REVIEW", "knowledge", knowledge_id, decision, reviewer)
    return status


def create_capture_session(session_id: str, user_id: int, mode: str) -> dict[str, Any]:
    mode = mode if mode in {"fast", "expert"} else "fast"
    max_questions = 3 if mode == "fast" else 12
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO capture_sessions(
                id,user_id,mode,status,state,form_data,conversation,missing_fields,completion_score,quality_score,
                evidence_score,confidence_score,question_count,max_questions,knowledge_id,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                session_id,
                user_id,
                mode,
                "new",
                "new",
                "{}",
                "[]",
                "[]",
                0,
                0,
                0,
                0,
                0,
                max_questions,
                None,
                now(),
                now(),
            ),
        )
    return get_capture_session(session_id) or {}


def get_capture_session(session_id: str) -> dict[str, Any] | None:
    session = one("SELECT * FROM capture_sessions WHERE id=?", (session_id,))
    if not session:
        return None
    for field in ("form_data", "conversation", "missing_fields"):
        try:
            session[field] = json.loads(session[field] or ("{}" if field == "form_data" else "[]"))
        except json.JSONDecodeError:
            session[field] = {} if field == "form_data" else []
    session["attachments"] = list_session_attachments(session_id)
    return session


def update_capture_session(session_id: str, **updates: Any) -> dict[str, Any] | None:
    if not updates:
        return get_capture_session(session_id)
    assignments: list[str] = []
    values: list[Any] = []
    for key, value in updates.items():
        assignments.append(f"{key}=?")
        values.append(
            json.dumps(value, ensure_ascii=False) if key in {"form_data", "conversation", "missing_fields"} else value
        )
    assignments.append("updated_at=?")
    values.append(now())
    values.append(session_id)
    with connect() as connection:
        connection.execute(f"UPDATE capture_sessions SET {','.join(assignments)} WHERE id=?", values)
    return get_capture_session(session_id)


def add_attachment(
    filename: str,
    path: str,
    mime: str | None,
    knowledge_id: int | None = None,
    session_id: str | None = None,
    category: str = "evidence",
    actor: int = 4,
) -> int:
    with connect() as connection:
        attachment_id = connection.execute(
            "INSERT INTO attachments(knowledge_id,session_id,filename,stored_path,mime_type,category,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (knowledge_id, session_id, filename, path, mime, category, actor, now()),
        ).lastrowid
    audit("UPLOAD", "attachment", attachment_id, filename, actor)
    return int(attachment_id)


def list_attachments(knowledge_id: int) -> list[dict[str, Any]]:
    return rows("SELECT * FROM attachments WHERE knowledge_id=? ORDER BY created_at", (knowledge_id,))


def list_session_attachments(session_id: str) -> list[dict[str, Any]]:
    return rows("SELECT * FROM attachments WHERE session_id=? ORDER BY created_at", (session_id,))


def bind_session_attachments(session_id: str, knowledge_id: int) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE attachments SET knowledge_id=?,session_id=NULL WHERE session_id=?", (knowledge_id, session_id)
        )


def map_data() -> dict[str, Any]:
    """Return only approved knowledge in the public organizational map."""
    return {
        "domains": rows(
            """
            SELECT d.*,p.name parent_name,u.full_name owner_name,
                   (SELECT COUNT(*) FROM knowledge_items k WHERE k.domain_id=d.id AND k.status='published') item_count
            FROM knowledge_domains d
            LEFT JOIN knowledge_domains p ON p.id=d.parent_id
            LEFT JOIN users u ON u.id=d.owner_user_id
            ORDER BY COALESCE(p.name,''),d.name
            """
        ),
        "knowledge": rows(
            """
            SELECT k.id,k.title,k.summary,k.knowledge_type,k.status,k.unit,k.project,k.tags,
                   d.name domain_name
            FROM knowledge_items k
            LEFT JOIN knowledge_domains d ON d.id=k.domain_id
            WHERE k.status='published'
            ORDER BY k.updated_at DESC
            """
        ),
        "entities": rows(
            """
            SELECT e.*,k.title,k.status,d.name domain_name
            FROM knowledge_entities e
            JOIN knowledge_items k ON k.id=e.knowledge_id
            LEFT JOIN knowledge_domains d ON d.id=k.domain_id
            WHERE k.status='published'
            """
        ),
        "relations": rows(
            """
            SELECT r.*,k.title,k.status
            FROM knowledge_relations r
            JOIN knowledge_items k ON k.id=r.knowledge_id
            WHERE k.status='published'
            """
        ),
        "risk": rows(
            """
            SELECT d.id,d.name,
                   SUM(CASE WHEN k.status='published' THEN 1 ELSE 0 END) knowledge_count,
                   SUM(CASE WHEN k.status='published' AND k.owner_user_id IS NULL AND COALESCE(k.owner_text,'')='' THEN 1 ELSE 0 END) without_owner,
                   SUM(CASE WHEN k.status='published' THEN 1 ELSE 0 END) published,
                   ROUND(AVG(CASE WHEN k.status='published' THEN COALESCE(k.quality_score,0) END),1) avg_quality,
                   SUM(CASE WHEN k.status='published' AND k.review_due_at < ? THEN 1 ELSE 0 END) overdue
            FROM knowledge_domains d
            LEFT JOIN knowledge_items k ON k.domain_id=d.id
            GROUP BY d.id,d.name
            """,
            (now(),),
        ),
    }


def dashboard() -> dict[str, Any]:
    with connect() as connection:
        count = lambda sql, args=(): connection.execute(sql, args).fetchone()[0]
        return {
            "knowledge_total": count("SELECT COUNT(*) FROM knowledge_items"),
            "published": count("SELECT COUNT(*) FROM knowledge_items WHERE status='published'"),
            "pending_review": count("SELECT COUNT(*) FROM knowledge_items WHERE status='pending_review'"),
            "stale_or_due": count("SELECT COUNT(*) FROM knowledge_items WHERE review_due_at<?", (now(),)),
            "without_owner": count(
                "SELECT COUNT(*) FROM knowledge_items WHERE owner_user_id IS NULL AND COALESCE(owner_text,'')=''"
            ),
            "open_gaps": count("SELECT COUNT(*) FROM knowledge_gaps WHERE status='open'"),
            "feedback_total": count("SELECT COUNT(*) FROM feedback"),
            "documents": count("SELECT COUNT(*) FROM documents"),
        }


def add_document(
    filename: str,
    stored_path: str,
    mime_type: str | None,
    category: str,
    tags: str,
    status: str,
    page_count: int,
    quality_score: float,
    knowledge_id: int | None = None,
) -> int:
    """Insert or update a document so publishing the same knowledge is idempotent."""
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO documents(filename,stored_path,mime_type,category,tags,status,page_count,quality_score,knowledge_id,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(stored_path) DO UPDATE SET
                filename=excluded.filename,
                mime_type=excluded.mime_type,
                category=excluded.category,
                tags=excluded.tags,
                status=excluded.status,
                page_count=excluded.page_count,
                quality_score=excluded.quality_score,
                knowledge_id=excluded.knowledge_id
            """,
            (filename, stored_path, mime_type, category, tags, status, page_count, quality_score, knowledge_id, now()),
        )
        row = connection.execute("SELECT id FROM documents WHERE stored_path=?", (stored_path,)).fetchone()
        return int(row[0])


def update_document_status(document_id: int, status: str) -> None:
    with connect() as connection:
        connection.execute("UPDATE documents SET status=? WHERE id=?", (status, document_id))


def list_documents() -> list[dict[str, Any]]:
    return rows("SELECT * FROM documents ORDER BY created_at DESC")


def list_gaps() -> list[dict[str, Any]]:
    return rows("SELECT * FROM knowledge_gaps ORDER BY created_at DESC")


def create_gap(data: dict[str, Any], actor_id: int = 4) -> int:
    with connect() as connection:
        return int(
            connection.execute(
                "INSERT INTO knowledge_gaps(question,domain_id,assigned_expert_id,status,priority,created_by,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    data["question"],
                    data.get("domain_id"),
                    data.get("assigned_expert_id"),
                    "open",
                    data.get("priority", "medium"),
                    actor_id,
                    now(),
                ),
            ).lastrowid
        )


def list_audit() -> list[dict[str, Any]]:
    return rows("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 500")


def add_feedback(data: dict[str, Any], actor_id: int = 4) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO feedback(knowledge_id,user_id,feedback_type,comment,applied_context,created_at) VALUES(?,?,?,?,?,?)",
            (
                data["knowledge_id"],
                actor_id,
                data["feedback_type"],
                data.get("comment", ""),
                data.get("applied_context", ""),
                now(),
            ),
        )
