"""
Tests for admin routes
"""
import pytest
from datetime import datetime, timedelta


class TestAdminLogin:
    """Test admin login endpoint"""

    def test_successful_login(self, client):
        """Test successful admin login"""
        response = client.post("/admin/login", json={
            "username": "admin",
            "password": "bilhetinho2024"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert data["token"] == "admin-session-token"

    def test_invalid_username(self, client):
        """Test login with invalid username"""
        response = client.post("/admin/login", json={
            "username": "wrong",
            "password": "bilhetinho2024"
        })
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_invalid_password(self, client):
        """Test login with invalid password"""
        response = client.post("/admin/login", json={
            "username": "admin",
            "password": "wrong"
        })
        assert response.status_code == 401

    def test_missing_credentials(self, client):
        """Test login with missing credentials"""
        response = client.post("/admin/login", json={})
        assert response.status_code == 422  # Validation error


class TestCreateEvent:
    """Test event creation endpoint"""

    def test_create_event_success(self, client):
        """Test successful event creation"""
        start = datetime.utcnow() + timedelta(hours=1)
        end = start + timedelta(hours=5)

        response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "event" in data
        assert len(data["event"]["code"]) == 6
        assert data["event"]["number_of_tables"] == 10
        assert "qr_code" in data["event"]
        assert data["event"]["qr_code"].startswith("data:image/png;base64,")

    def test_create_multiple_events_only_one_active(self, client):
        """Test that only one event can be active"""
        start1 = datetime.utcnow()
        end1 = start1 + timedelta(hours=5)

        # Create first event
        response1 = client.post("/admin/events", params={
            "start_date": start1.isoformat(),
            "end_date": end1.isoformat(),
            "number_of_tables": 10
        })
        assert response1.status_code == 200

        start2 = datetime.utcnow() + timedelta(days=1)
        end2 = start2 + timedelta(hours=5)

        # Create second event
        response2 = client.post("/admin/events", params={
            "start_date": start2.isoformat(),
            "end_date": end2.isoformat(),
            "number_of_tables": 15
        })
        assert response2.status_code == 200

        # Check only second is active
        list_response = client.get("/admin/events")
        events = list_response.json()["events"]
        active_events = [e for e in events if e["status"] == "active"]
        assert len(active_events) <= 1

    def test_invalid_dates_start_after_end(self, client):
        """Test event creation with start date after end date"""
        start = datetime.utcnow() + timedelta(hours=5)
        end = datetime.utcnow() + timedelta(hours=1)

        response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })

        assert response.status_code == 400
        assert "Start date must be before end date" in response.json()["detail"]

    def test_invalid_table_count_too_low(self, client):
        """Test event creation with invalid table count (too low)"""
        start = datetime.utcnow()
        end = start + timedelta(hours=5)

        response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 0
        })

        assert response.status_code == 400

    def test_invalid_table_count_too_high(self, client):
        """Test event creation with invalid table count (too high)"""
        start = datetime.utcnow()
        end = start + timedelta(hours=5)

        response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 51
        })

        assert response.status_code == 400

    def test_event_creates_room_and_tables(self, client, db_session):
        """Test that event creation also creates room and tables"""
        from models.room import Room
        from models.table import Table

        start = datetime.utcnow()
        end = start + timedelta(hours=5)

        response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })

        assert response.status_code == 200
        event_code = response.json()["event"]["code"]

        # Check room was created
        room = db_session.query(Room).filter(Room.event_code == event_code).first()
        assert room is not None
        assert room.is_active is True

        # Check tables were created
        tables = db_session.query(Table).filter(Table.room_id == room.id).all()
        assert len(tables) == 10
        assert all(t.number in range(1, 11) for t in tables)


class TestListEvents:
    """Test list events endpoint"""

    def test_list_empty_events(self, client):
        """Test listing events when none exist"""
        response = client.get("/admin/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) == 0

    def test_list_events_ordered_by_creation(self, client):
        """Test events are ordered by creation date (newest first)"""
        start = datetime.utcnow()

        # Create multiple events
        for i in range(3):
            client.post("/admin/events", params={
                "start_date": (start + timedelta(hours=i)).isoformat(),
                "end_date": (start + timedelta(hours=i+3)).isoformat(),
                "number_of_tables": 5 + i
            })

        response = client.get("/admin/events")
        events = response.json()["events"]
        assert len(events) == 3

        # Check they're ordered (newest first means highest table count first)
        assert events[0]["number_of_tables"] == 7  # Last created
        assert events[1]["number_of_tables"] == 6
        assert events[2]["number_of_tables"] == 5  # First created


class TestValidateEventCode:
    """Test event code validation endpoint"""

    def test_validate_valid_code(self, client):
        """Test validating a valid, active event code"""
        start = datetime.utcnow() - timedelta(hours=1)  # Started 1 hour ago
        end = start + timedelta(hours=5)  # Ends in 4 hours

        # Create event
        create_response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })
        code = create_response.json()["event"]["code"]

        # Validate code
        response = client.get(f"/events/validate/{code}")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["event"]["code"] == code
        assert "room_id" in data["event"]

    def test_validate_invalid_code(self, client):
        """Test validating a non-existent code"""
        response = client.get("/events/validate/INVALID")
        assert response.status_code == 404
        assert "Invalid event code" in response.json()["detail"]

    def test_validate_expired_event(self, client):
        """Test validating an expired event"""
        start = datetime.utcnow() - timedelta(hours=10)  # Started 10 hours ago
        end = start + timedelta(hours=5)  # Ended 5 hours ago

        # Create expired event
        create_response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })
        code = create_response.json()["event"]["code"]

        # Try to validate
        response = client.get(f"/events/validate/{code}")
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_validate_future_event(self, client):
        """Test validating an event that hasn't started"""
        start = datetime.utcnow() + timedelta(hours=5)  # Starts in 5 hours
        end = start + timedelta(hours=3)

        # Create future event
        create_response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })
        code = create_response.json()["event"]["code"]

        # Try to validate
        response = client.get(f"/events/validate/{code}")
        assert response.status_code == 400
        assert "not started" in response.json()["detail"].lower()

    def test_validate_code_case_insensitive(self, client):
        """Test that code validation is case-insensitive"""
        start = datetime.utcnow()
        end = start + timedelta(hours=5)

        # Create event
        create_response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })
        code = create_response.json()["event"]["code"]

        # Validate with lowercase
        response = client.get(f"/events/validate/{code.lower()}")
        assert response.status_code == 200
        assert response.json()["valid"] is True


class TestEventCodeGeneration:
    """Test event code generation uniqueness"""

    def test_codes_are_unique(self, client):
        """Test that generated codes are unique"""
        start = datetime.utcnow()
        codes = set()

        # Create multiple events
        for i in range(5):
            response = client.post("/admin/events", params={
                "start_date": (start + timedelta(days=i)).isoformat(),
                "end_date": (start + timedelta(days=i, hours=5)).isoformat(),
                "number_of_tables": 10
            })
            code = response.json()["event"]["code"]
            codes.add(code)

        # All codes should be unique
        assert len(codes) == 5

    def test_code_format(self, client):
        """Test that generated codes have correct format"""
        start = datetime.utcnow()
        end = start + timedelta(hours=5)

        response = client.post("/admin/events", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "number_of_tables": 10
        })

        code = response.json()["event"]["code"]

        # Check format: 6 chars, uppercase letters and digits only
        assert len(code) == 6
        assert code.isupper()
        assert code.isalnum()
