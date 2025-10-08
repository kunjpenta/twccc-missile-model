# tewa/management/commands/import_tracks.py
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from tewa.models import Scenario
from tewa.services.csv_import import import_csv  # keeps file-like support

class Command(BaseCommand):
    help = "Import Track/TrackSample rows from a CSV file. Use a file path, '-' for stdin, or pipe data."

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            nargs="?",
            help="Path to CSV, '-' for stdin. If the path doesn't exist, stdin is used.",
        )
        parser.add_argument("--scenario-id", type=int, help="Scenario ID to attach tracks to")

    def handle(self, *args, **options):
        # Resolve scenario (optional)
        scenario: Optional[Scenario] = None
        scenario_id = options.get("scenario_id")
        if scenario_id is not None:
            try:
                scenario = Scenario.objects.get(pk=int(scenario_id))
            except Scenario.DoesNotExist:
                raise CommandError(f"Scenario {scenario_id} not found")

        file_opt = options.get("file")

        # Determine the input source
        if not file_opt or file_opt == "-":
            file_arg = sys.stdin                                  # read from stdin
        else:
            p = Path(file_opt)
            if p.exists():
                file_arg = str(p)                                 # real path
            else:
                # Django test often passes a StringIO which becomes a string repr.
                # Fall back to stdin so tests can set sys.stdin = StringIO(data).
                file_arg = sys.stdin

        result = import_csv(file_arg, scenario=scenario)
        msg = result.get("message", "ok")
        self.stdout.write(self.style.SUCCESS(
            f"{msg} (tracks={result.get('tracks_created')}, "
            f"samples={result.get('samples_created')}, rows={result.get('rows_processed')})"
        ))
