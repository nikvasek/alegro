#!/usr/bin/env python3
"""
WSGI entry point для production запуска с gunicorn
"""

from telegram_bot import app

if __name__ == "__main__":
    app.run()