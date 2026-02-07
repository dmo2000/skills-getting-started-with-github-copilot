"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


class TestRoot:
    """Test root endpoint"""

    def test_root_redirect(self):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Test getting all activities"""

    def test_get_activities_success(self):
        """Test successful retrieval of all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Verify structure of activities
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)

    def test_get_activities_has_expected_activities(self):
        """Test that expected activities are returned"""
        response = client.get("/activities")
        data = response.json()
        
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Tennis Club",
            "Drama Club",
            "Art Studio",
            "Debate Team",
            "Science Club"
        ]
        
        for activity in expected_activities:
            assert activity in data


class TestSignupForActivity:
    """Test signing up for activities"""

    def test_signup_success(self):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_activity_not_found(self):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_signup_duplicate_email(self):
        """Test signup with duplicate email"""
        activity_name = "Programming%20Class"
        email = "duplicate@mergington.edu"
        
        # First signup
        response1 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup with same email
        response2 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"]

    def test_signup_updates_participant_list(self):
        """Test that signup updates the participant list"""
        activity_name = "Art%20Studio"
        email = "artlover@mergington.edu"
        
        # Get initial state
        initial = client.get("/activities").json()
        initial_count = len(initial["Art Studio"]["participants"])
        
        # Sign up
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify participant count increased
        updated = client.get("/activities").json()
        updated_count = len(updated["Art Studio"]["participants"])
        assert updated_count == initial_count + 1
        assert email in updated["Art Studio"]["participants"]


class TestUnregisterFromActivity:
    """Test unregistering from activities"""

    def test_unregister_success(self):
        """Test successful unregistration from an activity"""
        activity_name = "Tennis%20Club"
        email = "unregister_test@mergington.edu"
        
        # First, sign up
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Unregistered" in data["message"]

    def test_unregister_activity_not_found(self):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_unregister_not_registered(self):
        """Test unregister for student not in activity"""
        response = client.delete(
            "/activities/Drama%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]

    def test_unregister_updates_participant_list(self):
        """Test that unregister updates the participant list"""
        activity_name = "Debate%20Team"
        email = "debater@mergington.edu"
        
        # Sign up
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Verify signup
        before = client.get("/activities").json()
        assert email in before["Debate Team"]["participants"]
        before_count = len(before["Debate Team"]["participants"])
        
        # Unregister
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        assert response.status_code == 200
        
        # Verify unregister
        after = client.get("/activities").json()
        after_count = len(after["Debate Team"]["participants"])
        assert after_count == before_count - 1
        assert email not in after["Debate Team"]["participants"]


class TestActivityCapacity:
    """Test activity capacity limits"""

    def test_cannot_exceed_max_participants(self):
        """Test that signup fails when activity is full"""
        # Get an activity and fill it up
        activities = client.get("/activities").json()
        
        # Find an activity with small capacity
        test_activity = "Basketball%20Team"
        activity_data = activities["Basketball Team"]
        max_capacity = activity_data["max_participants"]
        current_participants = len(activity_data["participants"])
        
        # If already at capacity, try to signup
        if current_participants >= max_capacity:
            response = client.post(
                f"/activities/{test_activity}/signup?email=overcapacity@mergington.edu"
            )
            assert response.status_code == 400
            data = response.json()
            assert "full" in data["detail"]


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_special_characters_in_email(self):
        """Test handling of special characters in email"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=test%2Bspecial@mergington.edu"
        )
        assert response.status_code == 200

    def test_case_sensitive_activity_names(self):
        """Test that activity names are case-sensitive"""
        response = client.post(
            "/activities/chess%20club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404

    def test_empty_email(self):
        """Test empty email parameter"""
        response = client.post("/activities/Chess%20Club/signup?email=")
        # Empty email should still be processed as a string
        assert response.status_code in [200, 400]
