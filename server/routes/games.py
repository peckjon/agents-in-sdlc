from flask import jsonify, Response, Blueprint, request
from models import db, Game, Publisher, Category
from sqlalchemy.orm import Query
from sqlalchemy.exc import IntegrityError

# Create a Blueprint for games routes
games_bp = Blueprint('games', __name__)

def get_games_base_query() -> Query:
    return db.session.query(Game).join(
        Publisher, 
        Game.publisher_id == Publisher.id, 
        isouter=True
    ).join(
        Category, 
        Game.category_id == Category.id, 
        isouter=True
    )

@games_bp.route('/api/games', methods=['GET'])
def get_games() -> Response:
    # Use the base query for all games
    games_query = get_games_base_query().all()
    
    # Convert the results using the model's to_dict method
    games_list = [game.to_dict() for game in games_query]
    
    return jsonify(games_list)

@games_bp.route('/api/games/<int:id>', methods=['GET'])
def get_game(id: int) -> tuple[Response, int] | Response:
    # Use the base query and add filter for specific game
    game_query = get_games_base_query().filter(Game.id == id).first()
    
    # Return 404 if game not found
    if not game_query: 
        return jsonify({"error": "Game not found"}), 404
    
    # Convert the result using the model's to_dict method
    game = game_query.to_dict()
    
    return jsonify(game)

@games_bp.route('/api/games', methods=['POST'])
def create_game() -> tuple[Response, int]:
    # Get JSON data from request
    data = request.get_json()
    if data is None:
        return jsonify({"error": "No JSON data provided"}), 400
        
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Validate required fields
    required_fields = ['title', 'description', 'category_id', 'publisher_id']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Validate foreign key relationships
    category = db.session.query(Category).filter(Category.id == data['category_id']).first()
    if not category:
        return jsonify({"error": "Invalid category_id"}), 400
        
    publisher = db.session.query(Publisher).filter(Publisher.id == data['publisher_id']).first()
    if not publisher:
        return jsonify({"error": "Invalid publisher_id"}), 400
    
    try:
        # Create new game
        game = Game(
            title=data['title'],
            description=data['description'],
            category_id=data['category_id'],
            publisher_id=data['publisher_id'],
            star_rating=data.get('star_rating')  # Optional field
        )
        
        db.session.add(game)
        db.session.commit()
        
        # Return the created game with relationships
        created_game = get_games_base_query().filter(Game.id == game.id).first()
        return jsonify(created_game.to_dict()), 201
        
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create game"}), 500

@games_bp.route('/api/games/<int:id>', methods=['PUT'])
def update_game(id: int) -> tuple[Response, int] | Response:
    # Find existing game
    game = db.session.query(Game).filter(Game.id == id).first()
    if not game:
        return jsonify({"error": "Game not found"}), 404
    
    # Get JSON data from request
    data = request.get_json()
    if data is None:
        return jsonify({"error": "No JSON data provided"}), 400
        
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400
    
    try:
        # Update fields if provided
        if 'title' in data:
            game.title = data['title']
        if 'description' in data:
            game.description = data['description']
        if 'star_rating' in data:
            game.star_rating = data['star_rating']
            
        # Validate foreign key relationships if provided
        if 'category_id' in data:
            category = db.session.query(Category).filter(Category.id == data['category_id']).first()
            if not category:
                return jsonify({"error": "Invalid category_id"}), 400
            game.category_id = data['category_id']
            
        if 'publisher_id' in data:
            publisher = db.session.query(Publisher).filter(Publisher.id == data['publisher_id']).first()
            if not publisher:
                return jsonify({"error": "Invalid publisher_id"}), 400
            game.publisher_id = data['publisher_id']
        
        db.session.commit()
        
        # Return the updated game with relationships
        updated_game = get_games_base_query().filter(Game.id == id).first()
        return jsonify(updated_game.to_dict())
        
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update game"}), 500

@games_bp.route('/api/games/<int:id>', methods=['DELETE'])
def delete_game(id: int) -> tuple[Response, int]:
    # Find existing game
    game = db.session.query(Game).filter(Game.id == id).first()
    if not game:
        return jsonify({"error": "Game not found"}), 404
    
    try:
        db.session.delete(game)
        db.session.commit()
        return '', 204  # No content response
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete game"}), 500
