import os
from pathlib import Path
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


def test_alembic_migration_upgrade_and_downgrade(tmp_path):
    """Verify that Alembic migrations upgrade and downgrade cleanly without errors."""
    db_file = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{db_file}"
    os.environ["SYNC_DATABASE_URL"] = db_url

    backend_dir = Path(__file__).resolve().parent.parent
    ini_path = backend_dir / "alembic.ini"
    script_loc = backend_dir / "alembic"

    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(script_loc))
    cfg.set_main_option("sqlalchemy.url", db_url)

    try:
        # 1. Upgrade to head
        command.upgrade(cfg, "head")

        # Verify tables created
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = {
            "users",
            "auth_accounts",
            "sessions",
            "projects",
            "project_members",
            "audit_logs",
            "alembic_version"
        }
        assert expected_tables.issubset(set(tables)), f"Missing tables in {tables}"

        # Verify indexes and absence of redundant PK indexes
        user_indexes = [idx["name"] for idx in inspector.get_indexes("users")]
        assert "ix_users_id" not in user_indexes, "Redundant primary key index found!"
        assert "ix_users_email" in user_indexes

        # Verify check constraints
        audit_checks = [c["name"] for c in inspector.get_check_constraints("audit_logs")]
        assert "ck_audit_logs_actor_type" in audit_checks
        assert "ck_audit_logs_result" in audit_checks

        # 2. Downgrade to base
        command.downgrade(cfg, "base")

        # Verify tables removed
        inspector_post = inspect(engine)
        post_tables = inspector_post.get_table_names()
        assert "users" not in post_tables
        assert "projects" not in post_tables
        assert "auth_accounts" not in post_tables

        # 3. Re-upgrade to head
        command.upgrade(cfg, "head")
        inspector_re = inspect(engine)
        assert "users" in inspector_re.get_table_names()
        assert "projects" in inspector_re.get_table_names()

    finally:
        os.environ.pop("SYNC_DATABASE_URL", None)
