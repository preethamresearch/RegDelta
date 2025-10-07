"""
RegDelta CLI Runner
Quick command-line interface for testing
"""

import argparse
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.config import get_config, setup_logging
from utils.audit import get_audit_logger
from agents.planner import PlannerAgent


def main():
    parser = argparse.ArgumentParser(description='RegDelta - Local Compliance Impact Analysis')
    parser.add_argument('--baseline', type=str, help='Path to baseline PDF')
    parser.add_argument('--new', type=str, required=True, help='Path to new PDF')
    parser.add_argument('--scenario', type=str, default='cli-run', help='Scenario name')
    parser.add_argument('--output-dir', type=str, default='data', help='Output directory')
    
    args = parser.parse_args()
    
    # Initialize
    print("=" * 60)
    print("RegDelta - Local Compliance Impact Analysis")
    print("=" * 60)
    
    config = get_config()
    setup_logging(config)
    config.ensure_directories()
    
    audit_logger = get_audit_logger()
    
    # Create planner
    planner = PlannerAgent(config, audit_logger)
    
    # Get file paths
    baseline_path = Path(args.baseline) if args.baseline else None
    new_path = Path(args.new)
    
    if not new_path.exists():
        print(f"Error: New PDF not found: {new_path}")
        sys.exit(1)
    
    if baseline_path and not baseline_path.exists():
        print(f"Error: Baseline PDF not found: {baseline_path}")
        sys.exit(1)
    
    # Run pipeline
    print("\nRunning full pipeline...")
    results = planner.run_full_pipeline(
        baseline_pdf=baseline_path,
        new_pdf=new_path,
        scenario_name=args.scenario
    )
    
    # Save results
    output_dir = Path(args.output_dir)
    planner.save_state(output_dir)
    
    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Status: {results['status']}")
    print(f"Duration: {results.get('duration_seconds', 0):.2f}s")
    print(f"Obligations: {len(planner.obligations)}")
    print(f"Mappings: {sum(len(m) for m in planner.mappings.values())}")
    print(f"\nOutputs saved to: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
