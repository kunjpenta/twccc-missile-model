# tewa/management/commands/compute_threats.py

from django.core.management.base import BaseCommand

from tewa.models import DefendedAsset, Scenario
from tewa.services.threat_compute import batch_compute_for_scenario


class Command(BaseCommand):
    help = 'Computes threat scores for all or a specific scenario and defended asset'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scenario_id',
            type=int,
            help='ID of the scenario to compute threat scores for'
        )
        parser.add_argument(
            '--da_id',
            type=int,
            help='ID of the defended asset to compute threat scores for'
        )

    def handle(self, *args, **options):
        scenario_id = options['scenario_id']
        da_id = options['da_id']

        if scenario_id and da_id:
            # Compute for a specific scenario and defended asset
            scenario = Scenario.objects.get(id=scenario_id)
            da = DefendedAsset.objects.get(id=da_id)
            self.stdout.write(
                f"Computing threat scores for scenario {scenario.name} and DA {da.name}...")
            batch_compute_for_scenario(scenario_id, da_id)
            self.stdout.write(self.style.SUCCESS(
                f"Threat scores computed for scenario {scenario.name} and DA {da.name}"))
        else:
            # Compute for all scenarios and defended assets
            scenarios = Scenario.objects.all()
            das = DefendedAsset.objects.all()
            for scenario in scenarios:
                for da in das:
                    self.stdout.write(
                        f"Computing threat scores for scenario {scenario.name} and DA {da.name}...")
                    batch_compute_for_scenario(scenario.id, da.id)
                    self.stdout.write(self.style.SUCCESS(
                        f"Threat scores computed for scenario {scenario.name} and DA {da.name}"))
