import unittest
import json
from typing import Dict, List, Any, Optional
from flask import Flask, Response
from models import Game, Publisher, Category, db, init_db
from routes.games import games_bp

class TestGamesRoutes(unittest.TestCase):
    # Test data as complete objects
    TEST_DATA: Dict[str, Any] = {
        "publishers": [
            {"name": "DevGames Inc"},
            {"name": "Scrum Masters"}
        ],
        "categories": [
            {"name": "Strategy"},
            {"name": "Card Game"}
        ],
        "games": [
            {
                "title": "Pipeline Panic",
                "description": "Build your DevOps pipeline before chaos ensues",
                "publisher_index": 0,
                "category_index": 0,
                "star_rating": 4.5
            },
            {
                "title": "Agile Adventures",
                "description": "Navigate your team through sprints and releases",
                "publisher_index": 1,
                "category_index": 1,
                "star_rating": 4.2
            }
        ]
    }
    
    # API paths
    GAMES_API_PATH: str = '/api/games'

    def setUp(self) -> None:
        """Set up test database and seed data"""
        # Create a fresh Flask app for testing
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Register the games blueprint
        self.app.register_blueprint(games_bp)
        
        # Initialize the test client
        self.client = self.app.test_client()
        
        # Initialize in-memory database for testing
        init_db(self.app, testing=True)
        
        # Create tables and seed data
        with self.app.app_context():
            db.create_all()
            self._seed_test_data()

    def tearDown(self) -> None:
        """Clean up test database and ensure proper connection closure"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def _seed_test_data(self) -> None:
        """Helper method to seed test data"""
        # Create test publishers
        publishers = [
            Publisher(**publisher_data) for publisher_data in self.TEST_DATA["publishers"]
        ]
        db.session.add_all(publishers)
        
        # Create test categories
        categories = [
            Category(**category_data) for category_data in self.TEST_DATA["categories"]
        ]
        db.session.add_all(categories)
        
        # Commit to get IDs
        db.session.commit()
        
        # Create test games
        games = []
        for game_data in self.TEST_DATA["games"]:
            game_dict = game_data.copy()
            publisher_index = game_dict.pop("publisher_index")
            category_index = game_dict.pop("category_index")
            
            games.append(Game(
                **game_dict,
                publisher=publishers[publisher_index],
                category=categories[category_index]
            ))
            
        db.session.add_all(games)
        db.session.commit()

    def _get_response_data(self, response: Response) -> Any:
        """Helper method to parse response data"""
        if response.data and len(response.data) > 0:
            try:
                return json.loads(response.data)
            except json.JSONDecodeError:
                return None
        return None

    def test_get_games_success(self) -> None:
        """Test successful retrieval of multiple games"""
        # Act
        response = self.client.get(self.GAMES_API_PATH)
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), len(self.TEST_DATA["games"]))
        
        # Verify all games using loop instead of manual testing
        for i, game_data in enumerate(data):
            test_game = self.TEST_DATA["games"][i]
            test_publisher = self.TEST_DATA["publishers"][test_game["publisher_index"]]
            test_category = self.TEST_DATA["categories"][test_game["category_index"]]
            
            self.assertEqual(game_data['title'], test_game["title"])
            self.assertEqual(game_data['publisher']['name'], test_publisher["name"])
            self.assertEqual(game_data['category']['name'], test_category["name"])
            self.assertEqual(game_data['starRating'], test_game["star_rating"])

    def test_get_games_structure(self) -> None:
        """Test the response structure for games"""
        # Act
        response = self.client.get(self.GAMES_API_PATH)
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), len(self.TEST_DATA["games"]))
        
        required_fields = ['id', 'title', 'description', 'publisher', 'category', 'starRating']
        for field in required_fields:
            self.assertIn(field, data[0])

    def test_get_game_by_id_success(self) -> None:
        """Test successful retrieval of a single game by ID"""
        # Get the first game's ID from the list endpoint
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        
        # Act
        response = self.client.get(f'{self.GAMES_API_PATH}/{game_id}')
        data = self._get_response_data(response)
        
        # Assert
        first_game = self.TEST_DATA["games"][0]
        first_publisher = self.TEST_DATA["publishers"][first_game["publisher_index"]]
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['title'], first_game["title"])
        self.assertEqual(data['publisher']['name'], first_publisher["name"])
        
    def test_get_game_by_id_not_found(self) -> None:
        """Test retrieval of a non-existent game by ID"""
        # Act
        response = self.client.get(f'{self.GAMES_API_PATH}/999')
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['error'], "Game not found")

    def test_create_game_success(self) -> None:
        """Test successful creation of a new game"""
        # Arrange
        new_game_data = {
            "title": "Test Game Creation",
            "description": "This is a test game for creation endpoint",
            "category_id": 1,
            "publisher_id": 1,
            "star_rating": 3.8
        }
        
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            data=json.dumps(new_game_data),
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['title'], new_game_data['title'])
        self.assertEqual(data['description'], new_game_data['description'])
        self.assertEqual(data['category']['id'], new_game_data['category_id'])
        self.assertEqual(data['publisher']['id'], new_game_data['publisher_id'])
        self.assertEqual(data['starRating'], new_game_data['star_rating'])
        self.assertIsNotNone(data['id'])

    def test_create_game_minimal_fields(self) -> None:
        """Test successful creation of a new game with minimal required fields"""
        # Arrange
        new_game_data = {
            "title": "Minimal Game",
            "description": "This game has only required fields",
            "category_id": 1,
            "publisher_id": 2
        }
        
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            data=json.dumps(new_game_data),
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['title'], new_game_data['title'])
        self.assertEqual(data['description'], new_game_data['description'])
        self.assertIsNone(data['starRating'])

    def test_create_game_missing_required_field(self) -> None:
        """Test creation failure when required field is missing"""
        # Arrange
        incomplete_game_data = {
            "title": "Incomplete Game",
            "description": "Missing category_id and publisher_id"
        }
        
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            data=json.dumps(incomplete_game_data),
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
        self.assertIn('Missing required field', data['error'])

    def test_create_game_invalid_category_id(self) -> None:
        """Test creation failure with invalid category_id"""
        # Arrange
        invalid_game_data = {
            "title": "Invalid Category Game",
            "description": "This game has an invalid category_id",
            "category_id": 999,
            "publisher_id": 1
        }
        
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            data=json.dumps(invalid_game_data),
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], "Invalid category_id")

    def test_create_game_invalid_publisher_id(self) -> None:
        """Test creation failure with invalid publisher_id"""
        # Arrange
        invalid_game_data = {
            "title": "Invalid Publisher Game",
            "description": "This game has an invalid publisher_id",
            "category_id": 1,
            "publisher_id": 999
        }
        
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            data=json.dumps(invalid_game_data),
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], "Invalid publisher_id")

    def test_create_game_invalid_json(self) -> None:
        """Test creation failure with invalid JSON"""
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            data="invalid json",
            content_type='application/json'
        )
        
        # Assert - Flask returns HTML error page for invalid JSON
        self.assertEqual(response.status_code, 400)
        # Don't check response content since Flask returns HTML for parse errors

    def test_create_game_no_json_data(self) -> None:
        """Test creation failure with no JSON data"""
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        if data:  # Only check if we get valid JSON back
            self.assertEqual(data['error'], "No JSON data provided")

    def test_update_game_success(self) -> None:
        """Test successful update of an existing game"""
        # Get existing game ID
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        
        # Arrange update data
        update_data = {
            "title": "Updated Game Title",
            "star_rating": 4.9
        }
        
        # Act
        response = self.client.put(
            f'{self.GAMES_API_PATH}/{game_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['title'], update_data['title'])
        self.assertEqual(data['starRating'], update_data['star_rating'])
        # Original description should remain unchanged
        self.assertEqual(data['description'], self.TEST_DATA["games"][0]["description"])

    def test_update_game_not_found(self) -> None:
        """Test update failure for non-existent game"""
        # Arrange
        update_data = {"title": "Updated Title"}
        
        # Act
        response = self.client.put(
            f'{self.GAMES_API_PATH}/999',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['error'], "Game not found")

    def test_update_game_invalid_category_id(self) -> None:
        """Test update failure with invalid category_id"""
        # Get existing game ID
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        
        # Arrange
        update_data = {"category_id": 999}
        
        # Act
        response = self.client.put(
            f'{self.GAMES_API_PATH}/{game_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], "Invalid category_id")

    def test_update_game_invalid_publisher_id(self) -> None:
        """Test update failure with invalid publisher_id"""
        # Get existing game ID
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        
        # Arrange
        update_data = {"publisher_id": 999}
        
        # Act
        response = self.client.put(
            f'{self.GAMES_API_PATH}/{game_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], "Invalid publisher_id")

    def test_update_game_no_json_data(self) -> None:
        """Test update failure with no JSON data"""
        # Get existing game ID
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        
        # Act
        response = self.client.put(
            f'{self.GAMES_API_PATH}/{game_id}',
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        if data:  # Only check if we get valid JSON back
            self.assertEqual(data['error'], "No JSON data provided")

    def test_delete_game_success(self) -> None:
        """Test successful deletion of an existing game"""
        # Get existing game ID
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        initial_count = len(games)
        
        # Act
        response = self.client.delete(f'{self.GAMES_API_PATH}/{game_id}')
        
        # Assert
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b'')
        
        # Verify game is actually deleted
        response = self.client.get(self.GAMES_API_PATH)
        remaining_games = self._get_response_data(response)
        self.assertEqual(len(remaining_games), initial_count - 1)
        
        # Verify the specific game is gone
        response = self.client.get(f'{self.GAMES_API_PATH}/{game_id}')
        self.assertEqual(response.status_code, 404)

    def test_delete_game_not_found(self) -> None:
        """Test deletion failure for non-existent game"""
        # Act
        response = self.client.delete(f'{self.GAMES_API_PATH}/999')
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['error'], "Game not found")

if __name__ == '__main__':
    unittest.main()