"""
RegDelta Streamlit UI
Dark-themed interface for compliance impact analysis
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
import json
from datetime import datetime

from utils.config import get_config, setup_logging
from utils.audit import get_audit_logger
from agents.planner import PlannerAgent
from agents.actions import create_actions_agent
import subprocess
import yaml
import os

# Page config
st.set_page_config(
    page_title="RegDelta - Local Compliance Impact Analysis",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Light theme CSS with better visibility
st.markdown("""
<style>
    .main {
        background-color: #f5f7fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e0e4e8;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric label {
        color: #4a5568 !important;
        font-weight: 600 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #1a202c !important;
        font-size: 2rem !important;
    }
    .stButton>button {
        background-color: #16a34a !important;
        color: white !important;
        font-weight: 600 !important;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        background-color: #15803d !important;
    }
    .stDownloadButton>button {
        background-color: #dc2626 !important;
        color: white !important;
        font-weight: 600 !important;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .stDownloadButton>button:hover {
        background-color: #b91c1c !important;
    }
    .severity-high {
        color: #dc2626;
        font-weight: bold;
    }
    .severity-medium {
        color: #d97706;
        font-weight: bold;
    }
    .severity-low {
        color: #059669;
        font-weight: bold;
    }
    h1, h2, h3 {
        color: #1a202c;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #4a5568;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #4CAF50;
    }
    div[data-testid="stExpander"] {
        background-color: #ffffff;
        border: 1px solid #e0e4e8;
        border-radius: 8px;
    }
    .stTextInput>div>div>input {
        background-color: #ffffff;
        color: #1a202c;
    }
    .stSelectbox>div>div>div {
        background-color: #ffffff;
        color: #1a202c;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_system():
    """Initialize configuration and logging"""
    config = get_config()
    setup_logging(config)
    config.ensure_directories()
    audit_logger = get_audit_logger()
    return config, audit_logger


@st.cache_resource
def init_planner(_config, _audit_logger):
    """Initialize planner agent (cached)"""
    planner = PlannerAgent(_config, _audit_logger)
    return planner


def get_available_scenarios(scenarios_dir: Path):
    """Get list of available scenarios from scenarios directory"""
    if not scenarios_dir.exists():
        return []
    
    scenarios = []
    for item in scenarios_dir.iterdir():
        if item.is_dir():
            scenarios.append(item.name)
    
    return sorted(scenarios)


def get_scenario_documents(scenarios_dir: Path, scenario_name: str):
    """Get baseline and new documents for a scenario"""
    scenario_path = scenarios_dir / scenario_name
    
    documents = {
        'baseline': [],
        'new': []
    }
    
    for bucket in ['baseline', 'new']:
        bucket_path = scenario_path / bucket
        if bucket_path.exists():
            for pdf in bucket_path.glob('*.pdf'):
                documents[bucket].append(pdf)
    
    return documents


def fetch_real_circulars():
    """Run the fetch_documents.py script"""
    try:
        result = subprocess.run(
            [sys.executable, 'fetch_documents.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def main():
    config, audit_logger = init_system()
    
    # Header
    st.title("📋 RegDelta")
    st.subheader("Local Compliance Impact Analysis")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Fetch real circulars button
        st.subheader("📥 Fetch Real Circulars")
        
        if st.button("🌐 Fetch Real Circulars", use_container_width=True):
            with st.spinner("Downloading regulatory documents..."):
                success, stdout, stderr = fetch_real_circulars()
                
                if success:
                    st.success("✓ Documents fetched successfully!")
                    st.text(stdout[-500:] if len(stdout) > 500 else stdout)  # Show last 500 chars
                    st.rerun()  # Reload to show new scenarios
                else:
                    st.error("✗ Fetch failed")
                    if stderr:
                        st.error(stderr)
        
        st.divider()
        
        # Scenario picker
        st.subheader("📂 Choose Scenario")
        
        available_scenarios = get_available_scenarios(config.scenarios_dir)
        
        if available_scenarios:
            scenario = st.selectbox(
                "Select Scenario",
                options=available_scenarios,
                index=0
            )
            
            # Get documents for selected scenario
            scenario_docs = get_scenario_documents(config.scenarios_dir, scenario)
            
            # Baseline PDF selector
            baseline_file = None
            baseline_path = None
            
            if scenario_docs['baseline']:
                baseline_options = ["None"] + [f.name for f in scenario_docs['baseline']]
                baseline_choice = st.selectbox(
                    "Baseline PDF",
                    options=baseline_options,
                    index=1 if len(baseline_options) > 1 else 0
                )
                
                if baseline_choice != "None":
                    baseline_path = next(f for f in scenario_docs['baseline'] if f.name == baseline_choice)
                    st.caption(f"📄 {baseline_path.name}")
            else:
                st.caption("ℹ️ No baseline PDFs in this scenario")
            
            # New PDF selector
            new_file = None
            new_path = None
            
            if scenario_docs['new']:
                new_options = [f.name for f in scenario_docs['new']]
                new_choice = st.selectbox(
                    "New PDF",
                    options=new_options,
                    index=0
                )
                
                new_path = next(f for f in scenario_docs['new'] if f.name == new_choice)
                st.caption(f"📄 {new_path.name}")
            else:
                st.warning("⚠️ No new PDFs in this scenario")
            
        else:
            st.warning("No scenarios found. Click 'Fetch Real Circulars' above or upload PDFs below.")
            scenario = st.text_input("Custom Scenario Name", value=config.get('scenario.default', 'demo'))
            baseline_path = None
            new_path = None
        
        st.divider()
        
        # Manual file upload (fallback)
        st.subheader("� Or Upload PDFs")
        
        uploaded_baseline = st.file_uploader(
            "Baseline PDF (optional)",
            type=['pdf'],
            key='baseline_upload'
        )
        
        uploaded_new = st.file_uploader(
            "New PDF",
            type=['pdf'],
            key='new_upload'
        )
        
        st.divider()
        
        # System info
        st.subheader("ℹ️ System Info")
        st.info(f"""
        **Storage:** {config.storage_mode}  
        **Controls:** {len(config.catalogs)} catalogs  
        **Evidence Mode:** {config.evidence_mode}  
        **Reviewer:** {config.reviewer_identity_mode}
        """)
        
        st.divider()
        
        # Helper text
        with st.expander("📖 Quick Guide"):
            st.markdown("""
            ### How to Use RegDelta
            
            1. **Fetch Real Circulars**
               - Click "Fetch Real Circulars" button
               - Downloads PCI, RBI, SEBI documents
            
            2. **Choose Scenario**
               - Select from dropdown
               - Pick baseline and new PDFs
            
            3. **Or Upload Custom PDFs**
               - Use manual upload section
            
            4. **Run Analysis**
               - Click "🚀 Run Diff • Extract • Map"
               - Wait for processing
            
            5. **Review Results**
               - Check obligations, mappings, actions
               - Export data as needed
            """)
    
    # Main content area
    # Determine which files to use (scenario files or uploaded files)
    final_baseline_path = None
    final_new_path = None
    final_scenario = scenario if 'scenario' in locals() else config.get('scenario.default', 'demo')
    
    # Priority: uploaded files > scenario files
    if uploaded_new:
        # Save uploaded files
        final_new_path = Path(config.scenarios_dir) / final_scenario / "new" / uploaded_new.name
        final_new_path.parent.mkdir(parents=True, exist_ok=True)
        with open(final_new_path, 'wb') as f:
            f.write(uploaded_new.read())
        
        if uploaded_baseline:
            final_baseline_path = Path(config.scenarios_dir) / final_scenario / "baseline" / uploaded_baseline.name
            final_baseline_path.parent.mkdir(parents=True, exist_ok=True)
            with open(final_baseline_path, 'wb') as f:
                f.write(uploaded_baseline.read())
    elif 'new_path' in locals() and new_path:
        # Use scenario files
        final_new_path = new_path
        final_baseline_path = baseline_path if 'baseline_path' in locals() else None
    
    if not final_new_path:
        st.info("👈 Select a scenario or upload a new PDF document to begin analysis")
        return
    
    # Run analysis button
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        run_analysis = st.button("🚀 Run Diff • Extract • Map", type="primary", use_container_width=True)
    
    with col2:
        if st.button("🔄 Reload Data", use_container_width=True):
            st.cache_resource.clear()
            st.session_state.clear()
            st.rerun()
    
    with col3:
        if st.button("🗑️ Clear Results", use_container_width=True):
            if 'results' in st.session_state:
                del st.session_state['results']
            st.rerun()
    
    # Run pipeline
    if run_analysis or 'planner' in st.session_state:
        
        if 'planner' not in st.session_state:
            with st.spinner("Initializing agents..."):
                planner = init_planner(config, audit_logger)
                st.session_state.planner = planner
        else:
            planner = st.session_state.planner
        
        if run_analysis:
            # Clear old results first
            if 'results' in st.session_state:
                del st.session_state['results']
            
            with st.spinner("Running full pipeline..."):
                results = planner.run_full_pipeline(
                    baseline_pdf=baseline_path,
                    new_pdf=new_path,
                    scenario_name=scenario
                )
                st.session_state.results = results
                st.session_state.planner = planner
                
                # Save state
                planner.save_state(config.data_dir)
                
                # Show success message with duration
                if results.get('status') == 'success':
                    st.success(f"✅ Analysis complete in {results.get('duration_seconds', 0):.1f}s!")
                else:
                    st.error(f"❌ Analysis failed: {results.get('error', 'Unknown error')}")
        
        # Display results
        if 'results' in st.session_state:
            display_results(st.session_state.planner, st.session_state.results, config)


def display_results(planner, results, config):
    """Display analysis results"""
    
    # Metrics
    st.header("📊 Analysis Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        duration = results.get('duration_seconds', 0)
        if duration > 0:
            st.metric("Duration", f"{duration:.1f}s")
        else:
            st.metric("Duration", "N/A", help="Run a new analysis to see duration")
    
    with col2:
        obligations_count = len(planner.obligations)
        st.metric("Obligations", obligations_count)
    
    with col3:
        mappings_count = sum(len(m) for m in planner.mappings.values())
        st.metric("Mappings", mappings_count)
    
    with col4:
        status = results.get('status', 'unknown')
        st.metric("Status", status.upper())
    
    st.divider()
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Obligations",
        "🔗 Mappings",
        "📊 Diff Summary",
        "✅ Actions",
        "💾 Exports"
    ])
    
    with tab1:
        display_obligations(planner)
    
    with tab2:
        display_mappings(planner, config)
    
    with tab3:
        display_diff(planner)
    
    with tab4:
        display_actions(planner, config)
    
    with tab5:
        display_exports(planner, config)


def display_obligations(planner):
    """Display obligations table"""
    st.subheader("Extracted Obligations")
    
    if not planner.obligations:
        st.warning("No obligations extracted")
        return
    
    # Filter by severity
    severity_filter = st.multiselect(
        "Filter by Severity",
        options=['high', 'medium', 'low'],
        default=['high', 'medium', 'low']
    )
    
    # Build dataframe
    data = []
    for ob in planner.obligations:
        if ob.severity in severity_filter:
            data.append({
                'Section': ob.section_id,
                'Severity': ob.severity.upper(),
                'Text': ob.text[:200] + '...',
                'Modal Phrases': ', '.join(ob.modal_phrases[:3]),
                'Deadline': '✓' if ob.has_deadline else '✗',
                'Citations': ', '.join(ob.citations[:2]) if ob.citations else '-'
            })
    
    df = pd.DataFrame(data)
    
    # Style severity column with better visibility
    def highlight_severity(row):
        if row['Severity'] == 'HIGH':
            # Light red background with dark text
            return [
                'background-color: rgba(254, 226, 226, 0.8); color: #991b1b; font-weight: 600;'
            ] * len(row)
        elif row['Severity'] == 'MEDIUM':
            # Light orange background with dark text
            return [
                'background-color: rgba(254, 243, 199, 0.8); color: #92400e; font-weight: 600;'
            ] * len(row)
        else:
            # Light green background with dark text
            return [
                'background-color: rgba(220, 252, 231, 0.8); color: #065f46; font-weight: 600;'
            ] * len(row)
    
    st.dataframe(
        df.style.apply(highlight_severity, axis=1),
        use_container_width=True,
        height=400
    )
    
    # Stats
    st.caption(f"Showing {len(data)} of {len(planner.obligations)} obligations")


def display_mappings(planner, config):
    """Display control mappings"""
    st.subheader("Control Mappings")
    
    if not planner.mappings:
        st.warning("No mappings available")
        return
    
    # Build flat list
    all_mappings = []
    for section_id, mappings in planner.mappings.items():
        for mapping in mappings:
            all_mappings.append({
                'Section': section_id,
                'Obligation': mapping.obligation_text[:100] + '...',
                'Control ID': mapping.control_id,
                'Control Title': mapping.control_title,
                'Score': f"{mapping.score:.3f}",
                'Cosine': f"{mapping.cosine_score:.3f}",
                'Lexical': f"{mapping.lexical_score:.3f}",
                'Status': mapping.status
            })
    
    df = pd.DataFrame(all_mappings)
    
    # Filter by status
    status_filter = st.multiselect(
        "Filter by Status",
        options=['accepted', 'review', 'rejected'],
        default=['accepted', 'review']
    )
    
    df_filtered = df[df['Status'].isin(status_filter)]
    
    st.dataframe(df_filtered, use_container_width=True, height=400)
    
    # Interactive review (simplified for PoC)
    st.caption(f"Showing {len(df_filtered)} of {len(all_mappings)} mappings")
    
    with st.expander("📝 Review Mapping (Demo)"):
        st.info("Full interactive review will be available in Alpha release")
        reviewer_name = st.text_input("Reviewer Name")
        action = st.radio("Action", ["Accept", "Override", "Reject"])
        comment = st.text_area("Comment")
        if st.button("Submit Review"):
            st.success(f"Review recorded: {action} by {reviewer_name}")


def display_diff(planner):
    """Display diff summary"""
    st.subheader("Document Diff Summary")
    
    if not planner.diff_result:
        st.warning("No diff available (baseline not provided)")
        return
    
    summary = planner.diff_result.get_summary()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Added", summary['paragraphs_added'])
    
    with col2:
        st.metric("Removed", summary['paragraphs_removed'])
    
    with col3:
        st.metric("Unchanged", summary['paragraphs_unchanged'])
    
    with col4:
        st.metric("Total Ops", summary['total_ops'])
    
    # Show changed sections
    st.subheader("Changed Sections")
    
    changed = planner.diff_result.get_changed_sections()
    
    for i, op in enumerate(changed[:10]):  # Limit to 10
        with st.expander(f"{op.op.upper()} - Section {i+1}"):
            if op.old_text:
                st.markdown("**Old:**")
                st.text('\n'.join(op.old_text[:3]))
            
            if op.new_text:
                st.markdown("**New:**")
                st.text('\n'.join(op.new_text[:3]))


def display_actions(planner, config):
    """Display action plan"""
    st.subheader("Action Plan & Evidence Schedule")
    
    # Generate actions
    actions_agent = create_actions_agent(config.get('planner.default_due_days', 30))
    
    actions = actions_agent.generate_actions(
        planner.obligations,
        planner.mappings,
        planner.mapper.controls
    )
    
    # Actions table
    st.markdown("### 📋 Action Items")
    
    actions_data = []
    for action in actions:
        actions_data.append({
            'Summary': action.summary,
            'Control ID': action.control_id,
            'Owner': action.owner,
            'Priority': action.priority.upper(),
            'Due Date': action.due_date,
            'System': action.system,
            'Status': action.status
        })
    
    df_actions = pd.DataFrame(actions_data)
    st.dataframe(df_actions, use_container_width=True, height=300)
    
    # Evidence schedules
    st.markdown("### 📅 Evidence Collection Schedule")
    
    # Get unique control IDs that are mapped
    mapped_control_ids = set()
    for maps in planner.mappings.values():
        for m in maps:
            if m.status in ['accepted', 'review']:
                mapped_control_ids.add(m.control_id)
    
    # Get the actual Control objects for those IDs
    controls_used = [
        ctrl for ctrl in planner.mapper.controls
        if ctrl.control_id in mapped_control_ids
    ]
    
    if not controls_used:
        st.info("No controls mapped yet. Evidence schedules will be generated once controls are mapped.")
    else:
        evidence_runs = actions_agent.generate_evidence_schedules(
            controls_used[:10],  # Limit for demo
            cadence_preset='quarterly'
        )
        
        evidence_data = []
        for run in evidence_runs:
            evidence_data.append({
                'Control': run.control_id,
                'Artefact': run.artefact,
                'Owner': run.owner,
                'Cadence': run.cadence_cron,
                'Next Run': run.next_run_at
            })
        
        df_evidence = pd.DataFrame(evidence_data)
        st.dataframe(df_evidence, use_container_width=True, height=250)


def display_exports(planner, config):
    """Display export options"""
    st.subheader("Export Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        obligations_json = json.dumps(
            [ob.to_dict() for ob in planner.obligations],
            indent=2
        )
        st.download_button(
            "📥 Download Obligations (JSON)",
            obligations_json,
            file_name=f"{planner.current_scenario}_obligations.json",
            mime="application/json",
            use_container_width=True,
            type="primary"
        )
    
    with col2:
        mappings_json = json.dumps(
            {
                section_id: [m.to_dict() for m in maps]
                for section_id, maps in planner.mappings.items()
            },
            indent=2
        )
        st.download_button(
            "📥 Download Mappings (JSON)",
            mappings_json,
            file_name=f"{planner.current_scenario}_mappings.json",
            mime="application/json",
            use_container_width=True,
            type="primary"
        )
    
    with col3:
        audit_file = config.audit_dir / "audit.jsonl"
        if audit_file.exists():
            with open(audit_file, 'r') as f:
                audit_data = f.read()
            st.download_button(
                "📥 Download Audit Trail",
                audit_data,
                file_name="audit.jsonl",
                mime="application/x-ndjson",
                use_container_width=True,
                type="primary"
            )
        else:
            st.info("No audit trail available yet")
    
    st.divider()
    
    # Audit verification
    st.subheader("🔒 Audit Trail Verification")
    
    if st.button("Verify Audit Chain"):
        from utils.audit import get_audit_logger
        audit = get_audit_logger()
        is_valid, line_num = audit.verify_chain()
        
        if is_valid:
            st.success("✓ Audit chain verified - No tampering detected")
        else:
            st.error(f"✗ Audit chain broken at line {line_num}")


if __name__ == "__main__":
    main()
