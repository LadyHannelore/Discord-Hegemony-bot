#!/usr/bin/env python3
"""
Test script to validate Discord Hegemony Bot setup
"""

import sys
import os

def test_python_version():
    """Test if Python version is sufficient."""
    print("Testing Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def test_imports():
    """Test if required packages can be imported."""
    print("\nTesting package imports...")
    
    try:
        import discord
        print(f"✅ discord.py {discord.__version__}")
    except ImportError:
        print("❌ discord.py not installed. Run: pip install discord.py")
        return False
    
    try:
        import aiofiles
        print("✅ aiofiles available")
    except ImportError:
        print("❌ aiofiles not installed. Run: pip install aiofiles")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv available")
    except ImportError:
        print("❌ python-dotenv not installed. Run: pip install python-dotenv")
        return False
    
    return True

def test_bot_modules():
    """Test if bot modules can be imported."""
    print("\nTesting bot modules...")
    
    try:
        from models import BrigadeType, GENERAL_TRAITS
        print("✅ models.py imports successfully")
    except ImportError as e:
        print(f"❌ models.py import failed: {e}")
        return False
    
    try:
        from json_data_manager import JsonDataManager
        print("✅ json_data_manager.py imports successfully")
    except ImportError as e:
        print(f"❌ json_data_manager.py import failed: {e}")
        return False
    
    try:
        from war_justifications import WAR_JUSTIFICATIONS
        print("✅ war_justifications.py imports successfully")
    except ImportError as e:
        print(f"❌ war_justifications.py import failed: {e}")
        return False
    
    try:
        from battle_system import BattleSystem
        print("✅ battle_system.py imports successfully")
    except ImportError as e:
        print(f"❌ battle_system.py import failed: {e}")
        return False
    
    return True

def test_env_file():
    """Test if .env file exists and has required variables."""
    print("\nTesting environment configuration...")
    
    if not os.path.exists('.env'):
        print("⚠️  .env file not found. Copy .env.example and add your bot token.")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ DISCORD_TOKEN not set in .env file")
        return False
    
    if token == 'your_bot_token_here':
        print("⚠️  DISCORD_TOKEN still has placeholder value")
        return False
    
    print("✅ Environment configuration looks good")
    return True

def test_database():
    """Test JSON data manager initialization."""
    print("\nTesting JSON data manager...")
    
    try:
        import asyncio
        from json_data_manager import JsonDataManager
        
        async def test_json_manager():
            db = JsonDataManager("test_data")
            await db.init_data_files()
            print("✅ JSON data manager initialization successful")
            
            # Clean up test data
            import shutil
            if os.path.exists("test_data"):
                shutil.rmtree("test_data")
            
            return True
        
        return asyncio.run(test_json_manager())
    
    except Exception as e:
        print(f"❌ JSON data manager test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🤖 Discord Hegemony Bot Setup Test")
    print("=" * 40)
    
    tests = [
        test_python_version,
        test_imports,
        test_bot_modules,
        test_env_file,
        test_database
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Your bot is ready to run.")
        print("Start the bot with: python main.py")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above before running the bot.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
