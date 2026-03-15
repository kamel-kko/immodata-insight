"""
db_manager.py — Gestionnaire SQLite (SQLAlchemy)
Mémoire persistante par Projet pour BOOMERANG

Double rôle :
  1. Historique messages par projet (sidebar Streamlit)
  2. Registre des outils forgés (audit trail)

NB : distinct du SqliteSaver LangGraph qui gère l'état du graphe
"""

import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, Index
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/boomerang.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Message(Base):
    __tablename__ = "messages"
    id         = Column(Integer, primary_key=True, index=True)
    id_projet  = Column(String(120), nullable=False, index=True)
    role       = Column(String(20),  nullable=False)
    content    = Column(Text,        nullable=False)
    created_at = Column(DateTime,    default=datetime.utcnow)
    __table_args__ = (
        Index("ix_messages_projet_date", "id_projet", "created_at"),
    )


class ForgedTool(Base):
    __tablename__ = "forged_tools"
    id          = Column(Integer,     primary_key=True, index=True)
    id_projet   = Column(String(120), nullable=False, index=True)
    nom_fichier = Column(String(256), nullable=False)
    besoin      = Column(Text,        nullable=False)
    statut      = Column(String(30),  default="validated")
    created_at  = Column(DateTime,    default=datetime.utcnow)


class PortRegistre(Base):
    __tablename__ = "port_registre"
    id          = Column(Integer, primary_key=True)
    nom_outil   = Column(String(256), nullable=False, unique=True)
    port        = Column(Integer,     nullable=False, unique=True)
    created_at  = Column(DateTime,    default=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_prochain_port() -> int:
    """Alloue le prochain port libre à partir de 8010.

    Vérifie à la fois la table port_registre ET si le port
    est réellement libre sur l'hôte (évite les conflits après
    suppression manuelle d'outils ou fichiers .DS_Store).

    Returns:
        Premier port libre >= 8010 non déjà enregistré et non occupé.
    """
    import socket
    with SessionLocal() as db:
        ports_utilises = {r.port for r in db.query(PortRegistre).all()}
    port = 8010
    while True:
        if port not in ports_utilises:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                libre = s.connect_ex(("localhost", port)) != 0
            if libre:
                return port
        port += 1


def enregistrer_port(nom_outil: str, port: int) -> None:
    """Persiste l'association outil <-> port dans la DB.

    Args:
        nom_outil: Nom court de l'outil (ex: 'recherche_plu').
        port: Port TCP alloué au container.
    """
    with SessionLocal() as db:
        existing = db.query(PortRegistre).filter(PortRegistre.nom_outil == nom_outil).first()
        if existing:
            existing.port = port
        else:
            db.add(PortRegistre(nom_outil=nom_outil, port=port))
        db.commit()


def lister_ports() -> dict[str, int]:
    """Retourne le registre complet {nom_outil: port}.

    Returns:
        Dictionnaire des outils avec leur port assigné.
    """
    with SessionLocal() as db:
        return {r.nom_outil: r.port for r in db.query(PortRegistre).all()}


def lister_projets() -> List[str]:
    with SessionLocal() as db:
        rows = db.query(Message.id_projet).distinct().all()
        return [r[0] for r in rows]


def sauvegarder_message(id_projet: str, role: str, content: str) -> None:
    with SessionLocal() as db:
        db.add(Message(id_projet=id_projet, role=role, content=content))
        db.commit()


def charger_historique(id_projet: str, limite: int = 50) -> List[Dict]:
    with SessionLocal() as db:
        rows = (
            db.query(Message)
            .filter(Message.id_projet == id_projet)
            .order_by(Message.created_at.asc())
            .limit(limite)
            .all()
        )
        return [{"role": r.role, "content": r.content} for r in rows]


def supprimer_historique(id_projet: str) -> int:
    with SessionLocal() as db:
        count = db.query(Message).filter(Message.id_projet == id_projet).delete()
        db.commit()
        return count


def enregistrer_outil_forge(
    id_projet: str, nom_fichier: str, besoin: str, statut: str = "validated"
) -> None:
    with SessionLocal() as db:
        db.add(ForgedTool(
            id_projet=id_projet, nom_fichier=nom_fichier,
            besoin=besoin, statut=statut,
        ))
        db.commit()


def lister_outils_projet(id_projet: str) -> List[Dict]:
    with SessionLocal() as db:
        rows = (
            db.query(ForgedTool)
            .filter(ForgedTool.id_projet == id_projet)
            .order_by(ForgedTool.created_at.desc())
            .all()
        )
        return [
            {"nom_fichier": r.nom_fichier, "besoin": r.besoin,
             "statut": r.statut, "created_at": r.created_at.isoformat()}
            for r in rows
        ]


init_db()
