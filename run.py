#!/usr/bin/env python3
"""
MIT-WPU Vyas Smart-Room Maintenance Tracker
Run script to start the Flask development server.
"""
import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    print("=" * 60)
    print("MIT-WPU Vyas Smart-Room Maintenance Tracker")
    print("=" * 60)
    print(f"Server: http://localhost:{port}")
    print(f"Student Portal: http://localhost:{port}/report")
    print(f"Admin Dashboard: http://localhost:{port}/admin")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=debug)
