#!/usr/bin/env python3
"""
Quick validation test for Phase 1 Alert Bot
Tests core functionality without requiring Slack connection
"""

import sys
import json
from alert_store import AlertStore
from slack_formatter import format_alert_message, format_app_home_view


def test_alert_store():
    """Test alert storage functionality."""
    print("Testing AlertStore...")
    store = AlertStore()
    
    # Test adding alerts
    alert1 = store.add_alert("api", "high", "Test alert 1")
    assert alert1['id'] == 1
    assert alert1['service'] == "api"
    assert alert1['severity'] == "high"
    
    alert2 = store.add_alert("database", "critical", "Test alert 2")
    assert alert2['id'] == 2
    
    # Test retrieval
    all_alerts = store.get_all_alerts()
    assert len(all_alerts) == 2
    assert all_alerts[0]['id'] == 2  # Newest first
    
    active_alerts = store.get_active_alerts()
    assert len(active_alerts) == 2
    
    # Test counts
    assert store.get_alert_count() == 2
    assert store.get_active_count() == 2
    
    # Test get by ID
    found = store.get_alert_by_id(1)
    assert found['service'] == "api"
    
    print("AlertStore tests passed")
    return True


def test_slack_formatter():
    """Test Block Kit formatting."""
    print("\nTesting Slack Formatter...")
    
    alert = {
        'id': 123,
        'service': 'api',
        'severity': 'critical',
        'message': 'Response time critical',
        'timestamp': '2026-01-05T10:30:00Z',
        'status': 'active'
    }
    
    # Test alert message formatting
    blocks = format_alert_message(alert)
    assert isinstance(blocks, list)
    assert len(blocks) > 0
    assert blocks[0]['type'] == 'header'
    
    # Test App Home formatting
    view = format_app_home_view([alert])
    assert view['type'] == 'home'
    assert 'blocks' in view
    assert len(view['blocks']) > 0
    
    # Test empty alerts
    empty_view = format_app_home_view([])
    assert 'No active alerts' in json.dumps(empty_view)
    
    print("Slack Formatter tests passed")
    return True


def test_severity_mappings():
    """Test severity emoji and color mappings."""
    print("\nTesting Severity Mappings...")
    
    from slack_formatter import get_severity_emoji, get_severity_color
    
    severities = ['critical', 'high', 'medium', 'low', 'info']
    
    for severity in severities:
        emoji = get_severity_emoji(severity)
        color = get_severity_color(severity)
        assert emoji is not None
        assert color.startswith('#')
        print(f"  {severity}: {emoji} ({color})")
    
    print("Severity mapping tests passed")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 1 ALERT BOT - VALIDATION TESTS")
    print("=" * 60)
    
    tests = [
        test_alert_store,
        test_slack_formatter,
        test_severity_mappings
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n🎉 All validation tests passed!")
        print("\nNext steps:")
        print("1. Set environment variables (SLACK_BOT_TOKEN, etc.)")
        print("2. Run: python app.py")
        print("3. Test with: /alert service=api severity=high message=test")
        print("4. Or use: ./scripts/send_alert.sh")
        sys.exit(0)


if __name__ == "__main__":
    main()
