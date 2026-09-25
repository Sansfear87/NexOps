"""Canonical enums and domain constants for database entities."""
from enum import Enum


class AuthProvider(str, Enum):
    PASSWORD = "password"
    GITHUB = "github"
    GOOGLE = "google"


class ProjectRole(str, Enum):
    OWNER = "OWNER"
    MAINTAINER = "MAINTAINER"
    DEVELOPER = "DEVELOPER"
    VIEWER = "VIEWER"


class ActorType(str, Enum):
    USER = "USER"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"
    WEBHOOK = "WEBHOOK"


class AuditResult(str, Enum):
    SUCCESS = "SUCCESS"
    DENIED = "DENIED"
    ERROR = "ERROR"
