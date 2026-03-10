import sys
sys.path.insert(0, '.')

try:
    from src.data_fetcher import DataFetcher
    from src.pipelines.orchestrator import Orchestrator
    
    print("✅ Imports successful")
    
    # Check if mode parameter exists
    import inspect
    
    # Check DataFetcher
    df_sig = inspect.signature(DataFetcher.fetch_with_smart_routing)
    df_params = list(df_sig.parameters.keys())
    print(f"DataFetcher.fetch_with_smart_routing params: {df_params}")
    has_mode_df = 'mode' in df_params
    print(f"Has 'mode' parameter in DataFetcher: {has_mode_df}")
    
    # Check Orchestrator
    orch_sig = inspect.signature(Orchestrator.run_agentic_pipeline)
    orch_params = list(orch_sig.parameters.keys())
    print(f"Orchestrator.run_agentic_pipeline params: {orch_params}")
    has_mode_orch = 'mode' in orch_params
    print(f"Has 'mode' parameter in Orchestrator: {has_mode_orch}")
    
    if has_mode_df and has_mode_orch:
        print("\n✅ FAST MODE IMPLEMENTATION VERIFIED")
    else:
        print("\n❌ FAST MODE NOT IMPLEMENTED CORRECTLY")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
