from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os

from database.connection import get_db
from models.note import Note, NoteStatus
from models.table import Table
from schemas.note import NoteCreate, NoteResponse

router = APIRouter()

MAX_NOTES_PER_USER = int(os.getenv("MAX_NOTES_PER_USER", 10))

@router.post("/notes", response_model=NoteResponse)
def create_note(note: NoteCreate, db: Session = Depends(get_db)):
    from models.room import Room

    from_table = db.query(Table).filter(Table.id == note.from_table_id).first()
    to_table = db.query(Table).filter(Table.id == note.to_table_id).first()

    if not from_table or not to_table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    # Check if room is still active
    room = db.query(Room).filter(Room.id == from_table.room_id).first()
    if not room or not room.is_active:
        raise HTTPException(status_code=403, detail="Evento foi encerrado pelo administrador")

    if from_table.room_id != to_table.room_id:
        raise HTTPException(status_code=400, detail="Mesas precisam estar na mesma sala")

    if note.from_table_id == note.to_table_id:
        raise HTTPException(status_code=400, detail="Não pode enviar bilhete para si mesmo")

    sent_count = db.query(Note).filter(Note.from_table_id == note.from_table_id).count()
    if sent_count >= MAX_NOTES_PER_USER:
        raise HTTPException(status_code=429, detail=f"Limite de {MAX_NOTES_PER_USER} bilhetes atingido")

    db_note = Note(
        room_id=from_table.room_id,
        from_table_id=note.from_table_id,
        to_table_id=note.to_table_id,
        message=note.message,
        is_anonymous=note.is_anonymous
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

@router.get("/tables/{table_id}/notes", response_model=list[NoteResponse])
def get_table_notes(table_id: str, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    notes = db.query(Note).filter(
        Note.to_table_id == table_id,
        Note.status == NoteStatus.SENT
    ).order_by(Note.created_at.desc()).all()

    return notes

@router.post("/notes/{note_id}/accept", response_model=NoteResponse)
def accept_note(note_id: str, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Bilhete não encontrado")

    if note.status != NoteStatus.SENT:
        raise HTTPException(status_code=400, detail="Bilhete já foi processado")

    note.status = NoteStatus.ACCEPTED
    db.commit()
    db.refresh(note)
    return note

@router.post("/notes/{note_id}/ignore", response_model=NoteResponse)
def ignore_note(note_id: str, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Bilhete não encontrado")

    if note.status != NoteStatus.SENT:
        raise HTTPException(status_code=400, detail="Bilhete já foi processado")

    note.status = NoteStatus.IGNORED
    db.commit()
    db.refresh(note)
    return note

@router.get("/tables/{table_id}/notes/ignored", response_model=list[NoteResponse])
def get_ignored_notes(table_id: str, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    notes = db.query(Note).filter(
        Note.to_table_id == table_id,
        Note.status == NoteStatus.IGNORED
    ).order_by(Note.created_at.desc()).all()

    return notes

@router.get("/tables/{table_id}/notes/sent", response_model=list[NoteResponse])
def get_sent_notes(table_id: str, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    notes = db.query(Note).filter(
        Note.from_table_id == table_id
    ).order_by(Note.created_at.desc()).all()

    return notes

@router.get("/tables/{table_id}/notes/accepted", response_model=list[NoteResponse])
def get_accepted_notes(table_id: str, db: Session = Depends(get_db)):
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa não encontrada")

    notes = db.query(Note).filter(
        Note.to_table_id == table_id,
        Note.status == NoteStatus.ACCEPTED
    ).order_by(Note.created_at.desc()).all()

    return notes
