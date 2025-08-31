import secrets
from cryptography.fernet import Fernet

def generate_fitpro_keys():
    """Generate all secret keys needed for FitPro app"""
    
    print("🔐 Generating FitPro Secret Keys...")
    print("=" * 50)
    
    # JWT Secret Key (for user authentication)
    jwt_key = secrets.token_urlsafe(64)
    print(f'JWT_SECRET_KEY="{jwt_key}"')
    
    # Encryption Key (for OAuth tokens) 
    encryption_key = Fernet.generate_key().decode()
    print(f'ENCRYPTION_KEY="{encryption_key}"')
    
    print("=" * 50)
    print("✅ Copy these to your .env file")
    print("⚠️  Keep these secret and never commit to git!")

if __name__ == "__main__":
    generate_fitpro_keys()