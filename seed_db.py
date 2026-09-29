# Copyright 2026 Google LLC
# Seed script for Wanderlust AI Firestore database

import google.auth
from google.cloud import firestore

# Hardcode the GCP Project ID as a literal string to ensure compatibility on Agent Platform
FIRESTORE_PROJECT = "qwiklabs-gcp-02-a4ec6fc6c34a"

SEEDED_DESTINATIONS = [
    {
        "id": "kyoto-japan",
        "name": "Kyoto",
        "country": "Japan",
        "vibe": "culture",
        "budget_level": "moderate",
        "description": "Historical capital of Japan known for classical Buddhist temples, gardens, imperial palaces, and traditional wooden houses.",
        "rating": 4.9,
        "popular_activities": ["Temple tours", "Traditional tea ceremony", "Arashiyama bamboo grove walk", "Geisha district exploration"],
        "best_season": "Spring / Autumn"
    },
    {
        "id": "santorini-greece",
        "name": "Santorini",
        "country": "Greece",
        "vibe": "relaxation",
        "budget_level": "luxury",
        "description": "Stunning Cycladic island in the Aegean Sea featuring whitewashed cliffside towns, blue-domed churches, and famous caldera sunsets.",
        "rating": 4.8,
        "popular_activities": ["Sunset watching in Oia", "Catamaran caldera cruise", "Wine tasting", "Red Beach visit"],
        "best_season": "May to October"
    },
    {
        "id": "banff-canada",
        "name": "Banff National Park",
        "country": "Canada",
        "vibe": "adventure",
        "budget_level": "moderate",
        "description": "Canada's oldest national park nestled in the Rocky Mountains with turquoise glacial lakes, abundant wildlife, and scenic hiking trails.",
        "rating": 4.9,
        "popular_activities": ["Lake Louise kayaking", "Moraine Lake photography", "Sulfur Mountain gondola", "Hiking Sentinel Pass"],
        "best_season": "June to September"
    },
    {
        "id": "costa-rica-rainforest",
        "name": "Arenal & La Fortuna",
        "country": "Costa Rica",
        "vibe": "adventure",
        "budget_level": "budget",
        "description": "Lush tropical rainforest region featuring Arenal Volcano, hot springs, waterfalls, and canopy ziplining.",
        "rating": 4.7,
        "popular_activities": ["Rainforest canopy ziplining", "Natural hot springs soaking", "Arenal Volcano hike", "Sloth spotting tour"],
        "best_season": "December to April"
    },
    {
        "id": "reykjavik-iceland",
        "name": "Reykjavik & Golden Circle",
        "country": "Iceland",
        "vibe": "adventure",
        "budget_level": "luxury",
        "description": "Gateway to Iceland's dramatic volcanic landscape, hot springs, cascading waterfalls, geysers, and Northern Lights.",
        "rating": 4.8,
        "popular_activities": ["Northern Lights chase", "Blue Lagoon geothermal spa", "Golden Circle day trip", "Glacier hiking"],
        "best_season": "September to March (Aurora) / June to August (Midnight Sun)"
    }
]


def seed_firestore():
    print(f"Connecting to Firestore with project ID: '{FIRESTORE_PROJECT}'...")
    creds, _ = google.auth.default()
    if hasattr(creds, "with_scopes"):
        creds = creds.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
    db = firestore.Client(project=FIRESTORE_PROJECT, credentials=creds)
    collection_ref = db.collection("destinations")

    count = 0
    for dest in SEEDED_DESTINATIONS:
        doc_id = dest["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(dest)
        print(f"  ✓ Seeded destination: {dest['name']} ({dest['country']}) -> ID: '{doc_id}'")
        count += 1

    print(f"Successfully seeded {count} destinations into Firestore project '{FIRESTORE_PROJECT}'.")


if __name__ == "__main__":
    seed_firestore()
