"""
services package
-----------------
Business logic that doesn't belong directly in a Flask route handler:
month calculations (totals/variance), and AI monthly review
generation. Keeping this separate from routes/ keeps route functions
thin (parse request -> call service -> return response), which makes
the logic independently testable.
"""
