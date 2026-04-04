"""
API Utilities - Standardized Response & Error Handling for FixLink-V1
"""
import os
import traceback
import logging
from functools import wraps
from flask import jsonify, request

logger = logging.getLogger(__name__)

def api_response(success=True, data=None, error=None, message=None, status=200):
    """
    Returns a standardized JSON response format.
    Format:
    {
        "success": bool,
        "data": mixed|null,
        "error": str|null,
        "message": str|null
    }
    """
    response = {'success': success}
    if data is not None:
        response['data'] = data
    if error is not None:
        response['error'] = error
    if message is not None:
        response['message'] = message
    return jsonify(response), status

def handle_api_errors(f):
    """
    Decorator to handle exceptions in API routes and return a standardized JSON error response.
    In DEBUG mode, returns the full traceback. In production, returns a generic error message.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # Determine if we are in debug mode
            is_debug = os.environ.get('FLASK_DEBUG') == 'True'
            
            # Log the error with traceback
            logger.error(f"API Exception in {f.__name__}: {str(e)}")
            if is_debug:
                logger.error(traceback.format_exc())
            
            error_message = str(e) if is_debug else "An unexpected internal server error occurred."
            return api_response(success=False, error=error_message, status=500)
            
    return decorated_function

def validate_json(required_fields):
    """
    Helper to check if required fields are present in the JSON request body.
    Returns (data, error_response) tuple.
    """
    data = request.get_json()
    if not data:
        return None, api_response(success=False, error="Missing JSON request body", status=400)
    
    missing = [field for field in required_fields if field not in data]
    if missing:
        return None, api_response(success=False, error=f"Missing required fields: {', '.join(missing)}", status=400)
        
    return data, None
