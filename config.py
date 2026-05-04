import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    SQLALCHEMY_DATABASE_URI = "sqlite:///advisor.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Twitter / X
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

    # Facebook / Instagram
    META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
    INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

    # LinkedIn
    LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
    LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN")