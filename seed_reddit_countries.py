"""
Seed script to populate initial countries for Reddit communities - Firebase Version
Run this script to create the 12 default countries in Firestore
"""
from firebase_db import get_firestore
from datetime import datetime

# 12 countries to seed
COUNTRIES_DATA = [
    {"iso_code": "US", "name": "United States", "flag_emoji": "🇺🇸", "description": "Connect with wellness enthusiasts from the United States"},
    {"iso_code": "IN", "name": "India", "flag_emoji": "🇮🇳", "description": "Join the wellness community in India"},
    {"iso_code": "GB", "name": "United Kingdom", "flag_emoji": "🇬🇧", "description": "Wellness discussions from the UK"},
    {"iso_code": "CA", "name": "Canada", "flag_emoji": "🇨🇦", "description": "Canadian wellness community"},
    {"iso_code": "AU", "name": "Australia", "flag_emoji": "🇦🇺", "description": "Australia's wellness network"},
    {"iso_code": "DE", "name": "Germany", "flag_emoji": "🇩🇪", "description": "German wellness community"},
    {"iso_code": "FR", "name": "France", "flag_emoji": "🇫🇷", "description": "French wellness discussions"},
    {"iso_code": "JP", "name": "Japan", "flag_emoji": "🇯🇵", "description": "Japanese wellness community"},
    {"iso_code": "BR", "name": "Brazil", "flag_emoji": "🇧🇷", "description": "Brazilian wellness network"},
    {"iso_code": "CN", "name": "China", "flag_emoji": "🇨🇳", "description": "China's wellness community"},
    {"iso_code": "MX", "name": "Mexico", "flag_emoji": "🇲🇽", "description": "Mexican wellness discussions"},
    {"iso_code": "IT", "name": "Italy", "flag_emoji": "🇮🇹", "description": "Italian wellness community"},
]


def seed_countries():
    """Seed countries into Firebase Firestore"""
    try:
        db = get_firestore()
        countries_ref = db.collection('countries')
        
        created_count = 0
        updated_count = 0
        
        for country_data in COUNTRIES_DATA:
            # Check if country already exists
            query = countries_ref.where('iso_code', '==', country_data["iso_code"]).limit(1)
            existing_docs = list(query.stream())
            
            now = datetime.utcnow().isoformat()
            
            if existing_docs:
                # Update existing country
                country_doc = existing_docs[0]
                country_ref = countries_ref.document(country_doc.id)
                country_ref.update({
                    "name": country_data["name"],
                    "flag_emoji": country_data["flag_emoji"],
                    "description": country_data["description"],
                    "is_active": True,
                    "updated_at": now,
                })
                updated_count += 1
                print(f"✅ Updated: {country_data['name']} ({country_data['iso_code']})")
            else:
                # Create new country
                country_data_with_meta = {
                    **country_data,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
                countries_ref.add(country_data_with_meta)
                created_count += 1
                print(f"✅ Created: {country_data['name']} ({country_data['iso_code']})")
        
        print(f"\n🎉 Seeding complete!")
        print(f"   Created: {created_count} countries")
        print(f"   Updated: {updated_count} countries")
        print(f"   Total: {created_count + updated_count} countries")
        
    except Exception as e:
        print(f"\n❌ Error seeding countries: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("🌍 Seeding Reddit countries to Firebase...\n")
    try:
        seed_countries()
    except Exception as e:
        print(f"\n❌ Error seeding countries: {e}")
        import traceback
        traceback.print_exc()
