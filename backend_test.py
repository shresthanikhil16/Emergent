import requests
import time
import uuid
import json
from datetime import datetime

class MarioGameAPITester:
    def __init__(self, base_url="https://4c174090-18d8-4969-b19c-4e4bc8ad08ae.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.player_id = None
        self.test_results = {}

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            
            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"Response: {json.dumps(response_data, indent=2)}")
                    self.test_results[name] = {
                        "status": "PASSED",
                        "response": response_data
                    }
                    return True, response_data
                except:
                    print(f"Response: {response.text}")
                    self.test_results[name] = {
                        "status": "PASSED",
                        "response": response.text
                    }
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                self.test_results[name] = {
                    "status": "FAILED",
                    "error": f"Expected status {expected_status}, got {response.status_code}",
                    "response": response.text
                }
                return False, None

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results[name] = {
                "status": "ERROR",
                "error": str(e)
            }
            return False, None

    def test_create_player(self):
        """Test creating a new player"""
        test_name = "Create Player"
        player_name = f"TestPlayer_{uuid.uuid4().hex[:8]}"
        
        success, response = self.run_test(
            test_name,
            "POST",
            "player",
            200,  # Expected status code
            data={"name": player_name}
        )
        
        if success and response and "id" in response:
            self.player_id = response["id"]
            print(f"Created player with ID: {self.player_id}")
            return True
        return False

    def test_get_player(self):
        """Test getting player by ID"""
        if not self.player_id:
            print("❌ Cannot test get_player: No player ID available")
            return False
        
        return self.run_test(
            "Get Player",
            "GET",
            f"player/{self.player_id}",
            200
        )[0]

    def test_update_player(self):
        """Test updating player data"""
        if not self.player_id:
            print("❌ Cannot test update_player: No player ID available")
            return False
        
        return self.run_test(
            "Update Player",
            "PUT",
            f"player/{self.player_id}",
            200,
            data={"score": 500, "lives": 2}
        )[0]

    def test_level_config(self):
        """Test getting level configuration"""
        if not self.player_id:
            print("❌ Cannot test level_config: No player ID available")
            return False
        
        return self.run_test(
            "Get Level Config",
            "GET",
            f"level/1/config",
            200,
            params={"player_id": self.player_id}
        )[0]

    def test_create_game_session(self):
        """Test recording a game session"""
        if not self.player_id:
            print("❌ Cannot test create_game_session: No player ID available")
            return False
        
        session_data = {
            "player_id": self.player_id,
            "level": 1,
            "score": 1000,
            "deaths": 2,
            "completion_time": 60.5,
            "difficulty_level": 1.2,
            "performance_metrics": {
                "final_score": 1000,
                "lives_remaining": 1
            }
        }
        
        return self.run_test(
            "Create Game Session",
            "POST",
            "game-session",
            200,
            data=session_data
        )[0]

    def test_player_performance(self):
        """Test getting player performance analytics"""
        if not self.player_id:
            print("❌ Cannot test player_performance: No player ID available")
            return False
        
        return self.run_test(
            "Get Player Performance",
            "GET",
            f"player/{self.player_id}/performance",
            200
        )[0]

    def test_save_game_state(self):
        """Test saving game state"""
        if not self.player_id:
            print("❌ Cannot test save_game_state: No player ID available")
            return False
        
        game_state = {
            "player_id": self.player_id,
            "current_level": 1,
            "score": 1500,
            "lives": 2,
            "mario_position": {"x": 100, "y": 400},
            "enemies": [
                {"x": 300, "y": 500, "alive": True},
                {"x": 450, "y": 500, "alive": False}
            ],
            "power_ups": [],
            "difficulty_settings": {"enemy_speed": 1.2}
        }
        
        return self.run_test(
            "Save Game State",
            "POST",
            "game-state",
            200,
            data=game_state
        )[0]

    def test_get_game_state(self):
        """Test getting saved game state"""
        if not self.player_id:
            print("❌ Cannot test get_game_state: No player ID available")
            return False
        
        return self.run_test(
            "Get Game State",
            "GET",
            f"game-state/{self.player_id}",
            200
        )[0]

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Mario Game API Tests")
        
        # Create player first to get player_id for other tests
        if not self.test_create_player():
            print("❌ Failed to create player, stopping tests")
            return False
        
        # Run all other tests
        self.test_get_player()
        self.test_update_player()
        self.test_level_config()
        self.test_create_game_session()
        self.test_player_performance()
        self.test_save_game_state()
        self.test_get_game_state()
        
        # Print results
        print(f"\n📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    tester = MarioGameAPITester()
    tester.run_all_tests()