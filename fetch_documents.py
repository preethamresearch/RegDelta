"""
RegDelta Document Fetcher
Downloads regulatory documents from configured URLs
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import yaml
import requests
from urllib.parse import urlparse
import logging
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_fetch_config(config_file: Path) -> Dict:
    """Load fetch configuration from YAML"""
    if not config_file.exists():
        raise FileNotFoundError(f"Fetch config not found: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def download_file(url: str, output_path: Path) -> bool:
    """
    Download a file from URL to output path
    
    Args:
        url: URL to download from
        output_path: Path to save the file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Downloading: {url}")
        
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download with streaming
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        # Save to file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = output_path.stat().st_size
        logger.info(f"✓ Downloaded {file_size:,} bytes to {output_path.name}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ Download failed: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False


def fetch_scenario(scenario: Dict, scenarios_dir: Path) -> Dict:
    """
    Fetch all documents for a scenario
    
    Args:
        scenario: Scenario configuration
        scenarios_dir: Base scenarios directory
    
    Returns:
        Summary of download results
    """
    scenario_name = scenario['name']
    logger.info(f"\n{'='*60}")
    logger.info(f"Scenario: {scenario_name}")
    logger.info('='*60)
    
    # Create scenario directory (sanitize name)
    safe_name = scenario_name.replace('/', '_').replace('\\', '_').replace(':', '_')
    scenario_dir = scenarios_dir / safe_name
    
    results = {
        'scenario': scenario_name,
        'documents': [],
        'success': 0,
        'failed': 0
    }
    
    for doc in scenario.get('documents', []):
        label = doc['label']
        bucket = doc['bucket']
        url = doc['url']
        
        # Generate filename from URL
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name
        
        # If no filename in URL, generate one
        if not filename or '.' not in filename:
            filename = f"{bucket}_{safe_name}.pdf"
        
        # Output path
        output_path = scenario_dir / bucket / filename
        
        logger.info(f"\n{label} ({bucket}):")
        
        # Skip if already exists
        if output_path.exists():
            logger.info(f"  ⚠ Already exists: {output_path.name}")
            results['documents'].append({
                'label': label,
                'bucket': bucket,
                'status': 'exists',
                'path': str(output_path)
            })
            results['success'] += 1
            continue
        
        # Download
        success = download_file(url, output_path)
        
        if success:
            results['documents'].append({
                'label': label,
                'bucket': bucket,
                'status': 'downloaded',
                'path': str(output_path)
            })
            results['success'] += 1
        else:
            results['documents'].append({
                'label': label,
                'bucket': bucket,
                'status': 'failed',
                'url': url
            })
            results['failed'] += 1
    
    return results


def main():
    """Main fetcher function"""
    logger.info("RegDelta Document Fetcher")
    logger.info("=" * 60)
    
    # Paths
    project_root = Path(__file__).parent
    fetch_config_file = project_root / "data" / "fetch_config.yml"
    scenarios_dir = project_root / "scenarios"
    
    # Load config
    try:
        config = load_fetch_config(fetch_config_file)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return 1
    
    scenarios = config.get('scenarios', [])
    if not scenarios:
        logger.warning("No scenarios found in config")
        return 1
    
    logger.info(f"Found {len(scenarios)} scenarios to fetch\n")
    
    # Fetch each scenario
    all_results = []
    
    for scenario in scenarios:
        results = fetch_scenario(scenario, scenarios_dir)
        all_results.append(results)
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("FETCH SUMMARY")
    logger.info("=" * 60)
    
    total_success = sum(r['success'] for r in all_results)
    total_failed = sum(r['failed'] for r in all_results)
    
    for result in all_results:
        logger.info(f"\n{result['scenario']}:")
        logger.info(f"  ✓ Success: {result['success']}")
        if result['failed'] > 0:
            logger.info(f"  ✗ Failed: {result['failed']}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Total: {total_success} successful, {total_failed} failed")
    logger.info(f"Documents saved to: {scenarios_dir}")
    logger.info("=" * 60)
    
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
