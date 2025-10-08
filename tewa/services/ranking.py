# tewa/services/ranking.py

from typing import Dict, List, Optional

from tewa.models import DefendedAsset, ThreatScore


def rank_threats(
    scenario_id: int,
    da_id: Optional[int] = None,
    top_n: Optional[int] = 10
) -> List[Dict]:
    """
    Returns threat rankings for a given scenario.
    - da_id: if provided, rank threats for this DA only; otherwise global ranking.
    - top_n: limit the number of threats returned
    """
    threat_rankings = []

    # If da_id is provided, rank threats for the specific DA
    if da_id:
        # Fetch the ThreatScores specific to the DA and scenario
        qs = ThreatScore.objects.filter(scenario_id=scenario_id, da_id=da_id)
        # Sort by threat score in descending order and by computed_at to ensure proper ranking
        sorted_threats = qs.order_by('-score', 'computed_at')[:top_n]
        threat_rankings.append({
            # Get the DA name
            'da_name': DefendedAsset.objects.get(id=da_id).name,
            'threats': [
                {
                    'track_id': ts.track.track_id,
                    'score': ts.score,
                    'computed_at': ts.computed_at.isoformat()
                }
                for ts in sorted_threats
            ]
        })
    else:
        # If no da_id is provided, rank threats globally (across all DAs)
        # Get all DAs associated with the scenario
        dAs = DefendedAsset.objects.all()

        # Loop through each DA and compute rankings
        for da in dAs:
            threat_scores = ThreatScore.objects.filter(
                scenario_id=scenario_id, da=da)
            # Sort threats based on score (highest to lowest)
            sorted_threats = threat_scores.order_by(
                '-score', 'computed_at')[:top_n]

            # Add to rankings
            threat_rankings.append({
                'da_name': da.name,
                'threats': [
                    {
                        'track_id': ts.track.track_id,
                        'score': ts.score,
                        'computed_at': ts.computed_at.isoformat()
                    }
                    for ts in sorted_threats
                ]
            })

    return threat_rankings
