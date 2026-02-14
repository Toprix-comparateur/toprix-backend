#!/usr/bin/env python
"""Utilitaire en ligne de commande Django pour les tâches administratives."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Vérifiez que Django est installé "
            "et que le virtualenv est activé."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
