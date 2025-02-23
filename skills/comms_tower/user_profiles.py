import json
import os
from datetime import datetime, timezone
from copy import deepcopy


# Define the default user profile
DEFAULT_USER_PROFILE = {
    "communication_style": "simple",
    "knowledge_level": 0,
    "background": "neutral",
    "age": 10,
    "language_tone": "neutral",
    "response_length": "medium",
    "temperament": "neutral",
    "interests": [],
    "dislikes": [],
    "motivations": "",
    "analysis_complete": False,
    "created_at": None,
    "updated_at": None,
}

# Valid value options
VALID_LANGUAGE_TONES = ["friendly", "formal", "neutral", "empathetic"]
VALID_RESPONSE_LENGTHS = ["short", "medium", "long"]

# File path for storing user profiles
USER_PROFILE_FILE = "user_profile.json"


def get_current_timestamp():
    """Returns the current UTC timestamp"""
    return datetime.now(timezone.utc).isoformat() + "Z"


# Load all user profiles
def load_user_profiles():
    if os.path.exists(USER_PROFILE_FILE):
        try:
            with open(USER_PROFILE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            print("Error: Unable to load user profiles. Returning empty data.")
            return {}
    return {}


# Save all user profiles
def save_user_profiles(profiles):
    try:
        with open(USER_PROFILE_FILE, "w") as f:
            json.dump(profiles, f, indent=4)
    except OSError as e:
        print(f"Error: Unable to save user profiles ({e}).")


# Retrieve a specific user's profile
def get_user_profile(user_id):
    profiles = load_user_profiles()
    return profiles.get(user_id, deepcopy(DEFAULT_USER_PROFILE))


# Validate and sanitize profile data
def validate_user_profile_data(data):
    """Validates and sanitizes user profile data."""
    if "language_tone" in data and data["language_tone"] not in VALID_LANGUAGE_TONES:
        data.pop("language_tone", None)
    if "response_length" in data and data["response_length"] not in VALID_RESPONSE_LENGTHS:
        data.pop("response_length", None)
    return data


# Update or create a user's profile
def update_user_profile(user_id, updated_data):
    profiles = load_user_profiles()
    user_profile = profiles.get(user_id, deepcopy(DEFAULT_USER_PROFILE))

    # Set timestamp for created_at if it's a new profile
    if user_id not in profiles:
        user_profile["created_at"] = get_current_timestamp()

    # Validate updated data and merge with the existing profile
    updated_data = validate_user_profile_data(updated_data)
    user_profile.update(updated_data)

    # Update the timestamp for modifications
    user_profile["updated_at"] = get_current_timestamp()

    profiles[user_id] = user_profile

    # Save profiles back to persistent storage
    save_user_profiles(profiles)
    return user_profile


# Delete a user's profile
def delete_user_profile(user_id):
    profiles = load_user_profiles()

    if user_id in profiles:
        del profiles[user_id]
        save_user_profiles(profiles)
        return True
    return False


# Export a user's profile to a file
def export_user_profile(user_id, filepath):
    profiles = load_user_profiles()
    profile = profiles.get(user_id)
    if profile:
        try:
            with open(filepath, "w") as f:
                json.dump(profile, f, indent=4)
            return True
        except OSError as e:
            print(f"Error: Unable to export user profile ({e}).")
    return False
