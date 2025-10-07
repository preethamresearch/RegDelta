"""
RegDelta Configuration Loader
Loads and validates configuration from config.yml
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Singleton configuration loader"""
    
    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        if not self._config:  # Only load once
            self.load(config_path)
    
    def load(self, config_path: Optional[str] = None):
        """Load configuration from YAML file"""
        if config_path is None:
            # Default to config.yml in project root
            config_path = Path(__file__).parent.parent / "config.yml"
        else:
            config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
        
        logger.info(f"Loaded configuration from {config_path}")
        self._validate()
    
    def _validate(self):
        """Validate required configuration keys"""
        required_keys = ['storage', 'extract', 'controls', 'mapping', 'ui', 'scenario']
        for key in required_keys:
            if key not in self._config:
                raise ValueError(f"Missing required configuration key: {key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key (e.g., 'storage.mode')"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    @property
    def storage_mode(self) -> str:
        return self.get('storage.mode', 'json')
    
    @property
    def data_dir(self) -> Path:
        return Path(self.get('storage.data_dir', 'data'))
    
    @property
    def audit_dir(self) -> Path:
        return Path(self.get('storage.audit_dir', 'audit'))
    
    @property
    def catalog_dir(self) -> Path:
        return Path(self.get('controls.catalog_dir', 'catalogs'))
    
    @property
    def scenarios_dir(self) -> Path:
        return Path(self.get('scenario.scenarios_dir', 'scenarios'))
    
    @property
    def catalogs(self) -> list:
        return self.get('controls.catalogs', [])
    
    @property
    def lexicon_file(self) -> Path:
        return Path(self.get('lexicon.file', 'lexicon.yml'))
    
    @property
    def mapping_thresholds(self) -> dict:
        return {
            'high': self.get('mapping.thresholds.high', 0.75),
            'low': self.get('mapping.thresholds.low', 0.60)
        }
    
    @property
    def blend_weights(self) -> dict:
        return {
            'cosine': self.get('mapping.blend.cosine_weight', 0.7),
            'lexical': self.get('mapping.blend.lexical_weight', 0.3)
        }
    
    @property
    def top_k(self) -> int:
        return self.get('mapping.top_k', 5)
    
    @property
    def reviewer_identity_mode(self) -> str:
        return self.get('reviewer.identity', 'prompt')
    
    @property
    def evidence_mode(self) -> str:
        return self.get('evidence.mode', 'plan')
    
    @property
    def skip_on_error(self) -> bool:
        return self.get('extract.skip_on_error', True)
    
    @property
    def log_level(self) -> str:
        return self.get('logging.level', 'INFO')
    
    @property
    def log_file(self) -> Path:
        return Path(self.get('logging.file', 'logs/regdelta.log'))
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        dirs = [
            self.data_dir,
            self.audit_dir,
            self.catalog_dir,
            self.scenarios_dir,
            self.log_file.parent
        ]
        
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info("Ensured all required directories exist")


def get_config(config_path: Optional[str] = None) -> Config:
    """Get singleton Config instance"""
    return Config(config_path)


def setup_logging(config: Config):
    """Setup logging based on configuration"""
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger.info("Logging initialized")
