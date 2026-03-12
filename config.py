import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared across environments."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ITEMS_PER_PAGE = 50


class DevelopmentConfig(Config):
    """Development — uses local SQLite file."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'blanks_erp.db')


class ProductionConfig(Config):
    """
    Production — uses PostgreSQL if DATABASE_URL is set,
    otherwise saves SQLite to /data (Render persistent disk).
    """
    DEBUG = False

    @staticmethod
    def _build_db_url():
        url = os.environ.get('DATABASE_URL', '')
        # Fix Render's postgres:// prefix — SQLAlchemy needs postgresql://
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        if url:
            return url
        # Fall back to persistent disk path on Render
        data_dir = '/data'
        if os.path.exists(data_dir):
            return 'sqlite:///' + os.path.join(data_dir, 'blanks_erp.db')
        # Final fallback for local testing
        return 'sqlite:///' + os.path.join(basedir, 'blanks_erp.db')

    SQLALCHEMY_DATABASE_URI = _build_db_url.__func__()


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
