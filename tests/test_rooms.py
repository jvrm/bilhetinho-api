"""
Tests for room routes
"""
import pytest
from datetime import datetime, timedelta


class TestRoomRoutes:
    """Test room management endpoints"""

    def setup_event_and_room(self, client):
        """Helper to create an active event and room"""
        start = datetime.utcnow()
        end = start + timedelta(hours=5)

        response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })

        return response.json()["event"]

    def test_get_active_room(self, client, db_session):
        """Test getting active room"""
        event = self.setup_event_and_room(client)

        response = client.get("/room/active")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        assert data["event_code"] == event["code"]

    def test_get_room_tables(self, client, db_session):
        """Test getting tables for a room"""
        event = self.setup_event_and_room(client)

        # Get the room
        room_response = client.get("/room/active")
        room_id = room_response.json()["id"]

        # Get tables
        tables_response = client.get(f"/room/{room_id}/tables")
        assert tables_response.status_code == 200
        tables = tables_response.json()
        assert len(tables) == 10
        assert all("number" in t for t in tables)
        assert all(t["room_id"] == room_id for t in tables)

    def test_create_room(self, client):
        """Test creating a new room"""
        response = client.post("/room", json={
            "name": "Test Room",
            "event_code": "TEST12"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Room"
        assert data["is_active"] is False  # New rooms start inactive

    def test_activate_room(self, client):
        """Test activating a room"""
        # Create room
        create_response = client.post("/room", json={
            "name": "Test Room",
            "event_code": "TEST12"
        })
        room_id = create_response.json()["id"]

        # Activate room
        activate_response = client.patch(f"/room/{room_id}/activate")
        assert activate_response.status_code == 200
        data = activate_response.json()
        assert data["is_active"] is True

    def test_activate_room_deactivates_others(self, client, db_session):
        """Test that activating a room deactivates other rooms"""
        from models.room import Room

        # Create and activate first room
        room1_response = client.post("/room", json={
            "name": "Room 1",
            "event_code": "TEST01"
        })
        room1_id = room1_response.json()["id"]
        client.patch(f"/room/{room1_id}/activate")

        # Create and activate second room
        room2_response = client.post("/room", json={
            "name": "Room 2",
            "event_code": "TEST02"
        })
        room2_id = room2_response.json()["id"]
        client.patch(f"/room/{room2_id}/activate")

        # Check that only room2 is active
        room1 = db_session.query(Room).filter(Room.id == room1_id).first()
        room2 = db_session.query(Room).filter(Room.id == room2_id).first()

        assert room1.is_active is False
        assert room2.is_active is True
