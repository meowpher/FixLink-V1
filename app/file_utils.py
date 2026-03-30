"""
Shared file upload utilities used by both routes.py and auth_routes.py.
Extracted here to avoid circular imports.
"""

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    """Return True if *filename* has an allowed image extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
