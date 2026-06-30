"""
Test LLM Client - TDD approach
"""
import os
import sys
sys.path.insert(0, '.')

def test_client_creation():
    """Test that LLM client can be created without 'proxies' error"""
    from agents.skills.llm_skills import _client, _get_config
    
    # Setup
    os.environ['LLM_BASE_URL'] = 'http://localhost:20128/v1'
    os.environ['LLM_API_KEY'] = 'sk-test'
    os.environ['LLM_MODEL'] = 'gpt-4o-mini'
    
    # Act
    try:
        config = _get_config()
        print(f"✓ Config loaded: {config}")
        
        client = _client()
        print(f"✓ Client created: {type(client)}")
        
        # Verify client has expected attributes
        assert hasattr(client, 'chat')
        print("✓ Client has 'chat' attribute")
        
        return True
    except TypeError as e:
        if 'proxies' in str(e):
            print(f"✗ FAILED: {e}")
            return False
        raise
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def test_call_llm():
    """Test that LLM call works without errors"""
    from agents.skills.llm_skills import _call_llm
    
    # This test expects LLM to be available
    # For now, just test it doesn't crash with proxies error
    try:
        response = _call_llm("test", temperature=0.5, max_tokens=5)
        if response:
            print(f"✓ LLM call succeeded: {response}")
        else:
            print("✓ LLM call returned None (might be unavailable, but no proxies error)")
        return True
    except TypeError as e:
        if 'proxies' in str(e):
            print(f"✗ FAILED: {e}")
            return False
        raise

if __name__ == '__main__':
    print("=" * 60)
    print("TDD: Testing LLM Client")
    print("=" * 60)
    
    print("\n[TEST 1] Client Creation")
    test1 = test_client_creation()
    
    print("\n[TEST 2] LLM Call")
    test2 = test_call_llm()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ TESTS FAILED")
        sys.exit(1)
