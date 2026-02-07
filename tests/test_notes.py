"""
Tests for note routes
"""
import pytest
from datetime import datetime, timedelta


class TestNoteRoutes:
    """Test note (bilhetinho) management endpoints"""

    def setup_full_environment(self, client):
        """Helper to create event, room, tables, and users"""
        start = datetime.utcnow()
        end = start + timedelta(hours=5)

        # Create event
        event_response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })

        # Get room and tables
        room_response = client.get("/room/active")
        room = room_response.json()

        tables_response = client.get(f"/room/{room['id']}/tables")
        tables = tables_response.json()

        # Create users at different tables
        user1_response = client.post("/users", json={
            "nickname": "Sender",
            "table_id": tables[0]["id"]
        })
        user1 = user1_response.json()

        user2_response = client.post("/users", json={
            "nickname": "Receiver",
            "table_id": tables[1]["id"]
        })
        user2 = user2_response.json()

        return {
            "room": room,
            "table1": tables[0],
            "table2": tables[1],
            "user1": user1,
            "user2": user2
        }

    def test_create_note(self, client):
        """Test creating a new note"""
        setup = self.setup_full_environment(client)

        response = client.post("/notes", json={
            "from_table_id": setup["table1"]["id"],
            "to_table_id": setup["table2"]["id"],
            "message": "Olá! Tudo bem?",
            "is_anonymous": False
        })

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Olá! Tudo bem?"
        assert data["status"] == "sent"
        assert data["is_anonymous"] is False

    def test_create_anonymous_note(self, client):
        """Test creating an anonymous note"""
        setup = self.setup_full_environment(client)

        response = client.post("/notes", json={
            "from_table_id": setup["table1"]["id"],
            "to_table_id": setup["table2"]["id"],
            "message": "Mensagem anônima",
            "is_anonymous": True
        })

        assert response.status_code == 200
        data = response.json()
        assert data["is_anonymous"] is True

    def test_create_note_max_length(self, client):
        """Test note message max length (140 chars)"""
        setup = self.setup_full_environment(client)

        # Message with exactly 140 chars
        message = "a" * 140
        response = client.post("/notes", json={
            "from_table_id": setup["table1"]["id"],
            "to_table_id": setup["table2"]["id"],
            "message": message,
            "is_anonymous": False
        })

        assert response.status_code == 200

        # Message with 141 chars should fail
        long_message = "a" * 141
        response2 = client.post("/notes", json={
            "from_table_id": setup["table1"]["id"],
            "to_table_id": setup["table2"]["id"],
            "message": long_message,
            "is_anonymous": False
        })

        assert response2.status_code == 422  # Validation error

    def test_accept_note(self, client):
        """Test accepting a note"""
        setup = self.setup_full_environment(client)

        # Create note
        note_response = client.post("/notes", json={
            "from_table_id": setup["table1"]["id"],
            "to_table_id": setup["table2"]["id"],
            "message": "Test message",
            "is_anonymous": False
        })
        note_id = note_response.json()["id"]

        # Accept note
        response = client.post(f"/notes/{note_id}/accept")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_ignore_note(self, client):
        """Test ignoring a note"""
        setup = self.setup_full_environment(client)

        # Create note
        note_response = client.post("/notes", json={
            "from_table_id": setup["table1"]["id"],
            "to_table_id": setup["table2"]["id"],
            "message": "Test message",
            "is_anonymous": False
        })
        note_id = note_response.json()["id"]

        # Ignore note
        response = client.post(f"/notes/{note_id}/ignore")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    def test_get_pending_notes(self, client):
        """Test getting pending notes for a table"""
        setup = self.setup_full_environment(client)

        # Create multiple notes
        for i in range(3):
            client.post("/notes", json={
                "from_table_id": setup["table1"]["id"],
                "to_table_id": setup["table2"]["id"],
                "message": f"Message {i}",
                "is_anonymous": False
            })

        # Get pending notes for table2
        response = client.get(f"/tables/{setup['table2']['id']}/notes")
        assert response.status_code == 200
        notes = response.json()
        assert len(notes) == 3
        assert all(n["status"] == "sent" for n in notes)

    def test_get_sent_notes(self, client):
        """Test getting sent notes from a table"""
        setup = self.setup_full_environment(client)

        # Create notes
        client.post("/notes", json={
            "from_table_id": setup["table1"]["id"],
            "to_table_id": setup["table2"]["id"],
            "message": "Sent message",
            "is_anonymous": False
        })

        # Get sent notes from table1
        response = client.get(f"/tables/{setup['table1']['id']}/notes/sent")
        assert response.status_code == 200
        notes = response.json()
        assert len(notes) >= 1
        assert all(n["from_table_id"] == setup["table1"]["id"] for n in notes)

    def test_get_accepted_notes(self, client):
        """Test getting accepted notes"""
        setup = self.setup_full_environment(client)

        # Create and accept note
        note_response = client.post("/notes", json={
            "from_table_id": setup["table1"]["id"],
            "to_table_id": setup["table2"]["id"],
            "message": "Test message",
            "is_anonymous": False
        })
        note_id = note_response.json()["id"]
        client.post(f"/notes/{note_id}/accept")

        # Get accepted notes
        response = client.get(f"/tables/{setup['table2']['id']}/notes/accepted")
        assert response.status_code == 200
        notes = response.json()
        assert len(notes) == 1
        assert notes[0]["status"] == "accepted"

    def test_get_ignored_notes(self, client):
        """Test getting ignored notes"""
        setup = self.setup_full_environment(client)

        # Create and ignore note
        note_response = client.post("/notes", json={
            "from_table_id": setup["table1"]["id"],
            "to_table_id": setup["table2"]["id"],
            "message": "Test message",
            "is_anonymous": False
        })
        note_id = note_response.json()["id"]
        client.post(f"/notes/{note_id}/ignore")

        # Get ignored notes
        response = client.get(f"/tables/{setup['table2']['id']}/notes/ignored")
        assert response.status_code == 200
        notes = response.json()
        assert len(notes) == 1
        assert notes[0]["status"] == "ignored"

    def test_note_to_same_table_should_fail(self, client):
        """Test that sending note to same table fails"""
        setup = self.setup_full_environment(client)

        response = client.post("/notes", json={
            "from_table_id": setup["table1"]["id"],
            "to_table_id": setup["table1"]["id"],  # Same table
            "message": "Self message",
            "is_anonymous": False
        })

        # Should either fail validation or be prevented by business logic
        assert response.status_code in [400, 422]
