import random
import logging
from typing import Dict, Optional
from user_profiles import get_user_profile, update_user_profile
import yaml

# Load the YAML configuration file
with open('skills/comms_tower/default_config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Ensure config is a dictionary
if not isinstance(config, dict):
    raise ValueError("Config should be a dictionary")

# Log the type of config to ensure it's a dictionary
logging.info(f"Config type: {type(config)}")

# Initialize logging
logging.basicConfig(level=logging.INFO)

def adjust_response(response: str, user_profile: Dict[str, str]) -> str:
    """
    Adjusts the response's tone and length based on the user's preferences.
    """
    tone = user_profile.get("language_tone", "neutral")
    length = user_profile.get("response_length", "medium")

    # Tone adjustment
    if tone == "friendly":
        response = f"😊 {response}"
    elif tone == "formal":
        response = f"Dear user, {response}"

    # Length adjustment
    if length == "short":
        response = response.split(".")[0] + "."
    elif length == "long":
        response += " Please let me know if you’d like more details!"

    return response

def perform_analysis_step(user_response: str, session_state: Dict[str, Optional[str]]) -> str:
    """
    Conversational analysis that refines findings and persists updates
    to the user profile across sessions.
    """
    user_id = session_state.get("user_id")
    if not user_id:
        logging.error("User ID not found in session state.")
        return "I’m sorry, I couldn’t identify you. Please restart the session."

    try:
        user_profile = get_user_profile(user_id) or {}
    except Exception as e:
        logging.error(f"Error retrieving user profile: {e}")
        return "I’m sorry, there was an error retrieving your profile. Please try again later."

    if "analysis_stage" not in session_state:
        session_state["analysis_stage"] = 1
        return random.choice([
            "What’s a topic you could talk about all day long?",
            "Let’s start easy—what interests you the most?"
        ])

    stage = session_state["analysis_stage"]

    try:
        if stage == 1:
            user_profile["background"] = user_response
            update_user_profile(user_id, {"background": user_response})
            session_state["analysis_stage"] += 1
            return adjust_response(
                random.choice([
                    f"Interesting! {user_response} sounds great. When learning about it, "
                    "do you prefer step-by-step explanations or just high-level overviews?"
                ]),
                user_profile
            )

        if stage == 2:
            communication_style = "simple"
            if "step-by-step" in user_response.lower():
                communication_style = "step-by-step"
            elif "high-level" in user_response.lower():
                communication_style = "high-level"

            update_user_profile(user_id, {"communication_style": communication_style})
            session_state["analysis_stage"] += 1
            return adjust_response(
                "Gotcha! How much do you already know about this topic? A little, a lot, or somewhere in between?",
                user_profile
            )

        if stage == 3:
            knowledge_level = 2
            if "little" in user_response.lower():
                knowledge_level = 1
            elif "a lot" in user_response.lower():
                knowledge_level = 4

            update_user_profile(user_id, {"knowledge_level": knowledge_level})
            session_state["analysis_stage"] += 1
            return adjust_response(
                "Great, that helps me understand! One last question—what’s something you’ve always wanted to learn more about?",
                user_profile
            )

        if stage == 4:
            user_profile["temperament"] = user_response
            update_user_profile(user_id, {"temperament": user_response})
            session_state["analysis_stage"] += 1
            return adjust_response(
                "Amazing! Finally, what keeps you motivated to keep learning?",
                user_profile
            )

        if stage == 5:
            user_profile["motivations"] = user_response
            update_user_profile(user_id, {
                "motivations": user_response,
                "analysis_complete": True
            })
            session_state["analysis_stage"] += 1
            return adjust_response(
                f"Cool! {user_response} seems interesting. Thanks for chatting with me—I’ve learned a lot about you!",
                user_profile
            )

    except Exception as e:
        logging.error(f"Error during analysis step {stage}: {e}")
        return "I’m sorry, there was an error processing your response. Please try again later."

    return adjust_response("Let’s keep chatting!", user_profile)