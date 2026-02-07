"""
Tests for user routes
"""
import pytest
from datetime import datetime, timedelta


class TestUserRoutes:
    """Test user management endpoints"""

    def setup_event_room_table(self, client):
        """Helper to create event, room, and get a table"""
        start = datetime.utcnow()
        end = start + timedelta(hours=5)

        event_response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })

        event = event_response.json()["event"]
        room_response = client.get("/room/active")
        room = room_response.json()

        tables_response = client.get(f"/room/{room['id']}/tables")
        table = tables_response.json()[0]

        return {"event": event, "room": room, "table": table}

    def test_create_user(self, client):
        """Test creating a new user"""
        setup = self.setup_event_room_table(client)

        response = client.post("/users", json={
            "nickname": "TestUser",
            "table_id": setup["table"]["id"]
        })

        assert response.status_code == 200
        data = response.json()
        assert data["nickname"] == "TestUser"
        assert data["table_id"] == setup["table"]["id"]
        assert "id" in data

    def test_get_user(self, client):
        """Test getting a user by ID"""
        setup = self.setup_event_room_table(client)

        # Create user
        create_response = client.post("/users", json={
            "nickname": "TestUser",
            "table_id": setup["table"]["id"]
        })
        user_id = create_response.json()["id"]

        # Get user
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["nickname"] == "TestUser"

    def test_get_users_at_table(self, client):
        """Test getting all users at a specific table"""
        setup = self.setup_event_room_table(client)
        table_id = setup["table"]["id"]

        # Create multiple users at same table
        nicknames = ["User1", "User2", "User3"]
        for nickname in nicknames:
            client.post("/users", json={
                "nickname": nickname,
                "table_id": table_id
            })

        # Get users at table
        response = client.get(f"/tables/{table_id}/users")
        assert response.status_code == 200
        users = response.json()
        assert len(users) == 3
        assert all(u["table_id"] == table_id for u in users)

    def test_create_user_with_empty_nickname(self, client):
        """Test that empty nickname is rejected"""
        setup = self.setup_event_room_table(client)

        response = client.post("/users", json={
            "nickname": "",
            "table_id": setup["table"]["id"]
        })

        assert response.status_code == 422  # Validation error

    def test_get_nonexistent_user(self, client):
        """Test getting a user that doesn't exist"""
        response = client.get("/users/nonexistent-id")
        assert response.status_code == 404
