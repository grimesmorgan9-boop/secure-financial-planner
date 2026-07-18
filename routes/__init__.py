"""
routes package
---------------
Each module defines one Flask Blueprint. Blueprints are registered
onto the app in app.py's `create_app()` factory. Keeping routes split
by concern (auth, dashboard, months, reviews, api) keeps each file
small and makes the URL map easy to reason about.
"""
