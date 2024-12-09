from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health", methods=["GET"])
def health():
    """
    Health endpoint to check the status of the application.
    """
    return jsonify({"status": "OK"}), 200

@app.route("/count", methods=["GET"])
def count():
    """
    Count endpoint to get the number of documents in the collection.
    """
    song_count = len(songs_list)
    return jsonify({"count": song_count}), 200

@app.route("/song", methods=["GET"])
def songs():
    """
    Endpoint to retrieve all songs from the database.
    """
    try:
        # Retrieve all documents from the songs collection
        song_documents = list(db.songs.find({}))
        
        # Convert MongoDB documents to JSON format
        songs_list = parse_json(song_documents)
        
        return jsonify({"songs": songs_list}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """
    Endpoint to retrieve a song by its ID.
    """
    try:
        # Find a single song with the specified ID
        song = db.songs.find_one({"id": id})
        
        if not song:
            return jsonify({"message": f"Песня с id {id} не найдена"}), 404
        
        # Convert MongoDB BSON format to JSON
        song_json = parse_json(song)
        return jsonify(song_json), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/song", methods=["POST"])
def create_song():
    """
    Endpoint to create a new song.
    """
    if not request.is_json:
        return jsonify({"Message": "Request body must be JSON"}), 400

    try:
        # Extract the song data from the request body
        new_song = request.get_json()

        # Check if a song with the same ID already exists
        existing_song = db.songs.find_one({"id": new_song["id"]})
        if existing_song:
            return jsonify({"Message": f"song with id {new_song['id']} already present"}), 302

        # Insert the new song into the database
        result = db.songs.insert_one(new_song)
        return jsonify({"inserted id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """
    Endpoint to update an existing song by its ID.
    """
    if not request.is_json:
        return jsonify({"message": "Request body must be JSON"}), 400

    try:
        # Extract the updated song data from the request body
        updated_data = request.get_json()

        # Find the existing song by ID
        existing_song = db.songs.find_one({"id": id})
        if not existing_song:
            return jsonify({"message": "песня не найдена"}), 404

        # Update the song in the database
        result = db.songs.update_one({"id": id}, {"$set": updated_data})

        # Check if any document was modified
        if result.modified_count > 0:
            # Retrieve the updated song to return it
            updated_song = db.songs.find_one({"id": id})
            return jsonify(parse_json(updated_song)), 201
        else:
            return jsonify({"message": "song found, but nothing updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """
    Endpoint to delete a song by its ID.
    """
    try:
        # Attempt to delete the song by ID
        result = db.songs.delete_one({"id": id})

        if result.deleted_count == 0:
            # No document was deleted, meaning the song was not found
            return jsonify({"message": "song not found"}), 404

        # Song successfully deleted
        return "", 204
    except Exception as e:
        return jsonify({"error": str(e)}), 500
