import secrets

# Generate your API secret key
api_key = secrets.token_urlsafe(32)

print("="*50)
print("🔑 Your FET API Secret Key:")
print(f"   {api_key}")
print("="*50)
print("\n📋 Next steps:")
print(f"1. Set environment: export FET_API_SECRET='{api_key}'")
print("2. Start API: python fet_api.py")
print("3. Add to Salesforce Custom Settings")
print(f"4. Test: curl -H 'Authorization: Bearer {api_key}' http://localhost:8000/health")